"""Tiny threaded HTTP server: JSON API, local file serving (with ranges), and an ad-free stream proxy."""
import json
import mimetypes
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import db, downloader, library, providers, recs

UI = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "ui"
ROUTES = []
PORT = 0
_EDITORIAL_CACHE = {"until": 0, "value": None}


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def route(method, pattern):
    rx = re.compile("^" + pattern + "$")

    def deco(fn):
        ROUTES.append((method, rx, fn))
        return fn
    return deco


# ------------------------------------------------------------------ API
@route("GET", r"/api/caps")
def caps(h, m, q, b):
    def has(mod):
        try:
            __import__(mod)
            return True
        except Exception:
            return False
    settings = db.get_settings()
    return {"ffmpeg": downloader.have_ffmpeg(), "mutagen": has("mutagen"), "yt_dlp": has("yt_dlp"),
            "ytmusicapi": has("ytmusicapi"), "spotify": bool(settings.get("spotify_id")),
            "audius": True, "jamendo": bool(settings.get("jamendo_client_id"))}


@route("GET", r"/api/home")
def home(h, m, q, b):
    return recs.home()


@route("GET", r"/api/recs")
def recommendations(h, m, q, b):
    return recs.mixes()


@route("GET", r"/api/discover")
def discover(h, m, q, b):
    tab = q.get("tab", "hot")
    if tab in ("recommended", "for-you"):
        return recs.personalized()
    if tab == "continue":
        rows = db.q("SELECT track, MAX(ts) ts FROM history GROUP BY key ORDER BY ts DESC LIMIT 30")
        return {"tracks": [json.loads(r["track"]) for r in rows], "errors": [], "providers": ["history"]}
    return providers.discovery_tracks(tab=tab, genre=q.get("genre", "Pop"), country=q.get("country", "BD"), limit=40)


@route("GET", r"/api/editorial")
def editorial(h, m, q, b):
    # Cached, source-aware "today's hits for you" shelf. Discovery stays native to the
    # provider of the user's most recent/liked track where the provider supports it.
    if _EDITORIAL_CACHE["value"] is not None and _EDITORIAL_CACHE["until"] > time.time():
        return _EDITORIAL_CACHE["value"]
    out = {"hits": [], "hits_source": "YouTube Music", "errors": []}
    rows = db.q("SELECT track FROM likes ORDER BY ts DESC LIMIT 5")
    rows += db.q("SELECT track FROM history ORDER BY ts DESC LIMIT 8")
    seeds, artists = [], []
    for row in rows:
        try:
            track = json.loads(row["track"])
            seeds.append(track)
            artist = (track.get("artist") or "").split(",")[0].strip()
            if artist and artist != "Unknown Artist" and artist not in artists:
                artists.append(artist)
        except Exception:
            continue
    seed = seeds[0] if seeds else {}
    artist = artists[0] if artists else ""
    source = seed.get("source", "yt")
    try:
        if source == "audius":
            out["hits"] = providers.audius_related(seed, 18)
            out["hits_source"] = "Audius recommendations"
        elif source == "jamendo":
            genre = (seed.get("genre") or "").split(",")[0].strip()
            out["hits"] = providers.search_jamendo(genre or artist or seed.get("title", "indie"), 18, by_genre=bool(genre))
            out["hits_source"] = "Jamendo catalog"
        elif source == "sp":
            out["hits"] = providers.search_sp("artist:" + artist if artist else "popular", 18)
            out["hits_source"] = "Spotify catalog"
        elif source == "itunes":
            out["hits"] = providers.search_itunes(artist or "popular music", 18)
            out["hits_source"] = "Apple music catalog"
        else:
            out["hits"] = providers.search_yt((artist + " hits") if artist else "popular songs", 18, "songs")
            out["hits_source"] = "YouTube Music picks"
    except Exception as e:
        out["errors"].append(f"Personalized hits: {str(e)[:120]}")
        # Keep the feature useful if a preferred source is unavailable.
        try:
            out["hits"] = providers.search_yt((artist + " hits") if artist else "popular songs", 18, "songs")
            out["hits_source"] = "YouTube Music fallback"
        except Exception as fallback:
            out["errors"].append(f"YouTube Music: {str(fallback)[:120]}")
    _EDITORIAL_CACHE["value"] = out
    _EDITORIAL_CACHE["until"] = time.time() + 1800
    return out


@route("GET", r"/api/search")
def search(h, m, q, b):
    text, scope = q.get("q", "").strip(), q.get("scope", "local")
    kind = q.get("kind", "songs")
    if not text:
        return {"local": [], "yt": [], "sp": [], "itunes": [], "musicbrainz": [], "audius": [], "jamendo": [], "collections": [], "errors": []}
    if scope == "local":
        return {"local": library.search(text, 40)}
    out = {"yt": [], "sp": [], "itunes": [], "musicbrainz": [], "audius": [], "jamendo": [], "collections": [], "errors": []}
    if kind in ("playlists", "channels"):
        try:
            out["collections"] = providers.search_yt_collections(text, 25, kind)
        except Exception as e:
            out["errors"].append(f"YouTube Music: {str(e)[:140]}")
        return out
    # Parallel provider calls keep UI latency close to the slowest provider, not the sum of all.
    jobs = {
        "yt": lambda: providers.search_yt(text, 25, "songs"),
        "itunes": lambda: providers.search_itunes(text, 20),
        "sp": lambda: providers.search_sp(text, 10),
        "audius": lambda: providers.search_audius(text, 25),
        "jamendo": lambda: providers.search_jamendo(text, 18),
    }
    if kind == "all":
        jobs["musicbrainz"] = lambda: providers.search_musicbrainz(text, 12)
        jobs["yt_videos"] = lambda: providers.search_yt(text, 12, "videos")
    labels = {"yt": "YouTube Music", "itunes": "iTunes", "sp": "Spotify", "audius": "Audius",
              "jamendo": "Jamendo", "musicbrainz": "MusicBrainz", "yt_videos": "YouTube Music videos"}
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futs = {name: ex.submit(fn) for name, fn in jobs.items()}
        for name, future in futs.items():
            try:
                found = future.result()
                if name == "yt_videos":
                    seen = {t.get("key") for t in out["yt"]}
                    out["yt"].extend(t for t in found if t.get("key") not in seen)
                else:
                    out[name] = found or []
            except Exception as e:
                out["errors"].append(f"{labels.get(name, name)}: {str(e)[:140]}")
    return out

@route("GET", r"/api/search-history")
def search_history(h, m, q, b):
    return {"queries": [dict(r) for r in db.q("SELECT query, ts FROM search_history ORDER BY ts DESC LIMIT 30")]}


@route("POST", r"/api/search-history")
def save_search_history(h, m, q, b):
    query = (b.get("query") or "").strip()[:180]
    if query:
        k = db.norm(query)
        db.run("INSERT OR REPLACE INTO search_history(query_key, query, ts) VALUES(?,?,?)", (k, query, time.time()))
    return {"ok": True}


@route("POST", r"/api/search-history/clear")
def clear_search_history(h, m, q, b):
    db.run("DELETE FROM search_history")
    return {"ok": True}


@route("GET", r"/api/library")
def lib(h, m, q, b):
    return {"tracks": library.all_tracks()}


@route("GET", r"/api/library/status")
def lib_status(h, m, q, b):
    return library.status


@route("POST", r"/api/library/scan")
def lib_scan(h, m, q, b):
    library.scan()
    return {"ok": True}


@route("GET", r"/api/folders")
def folders(h, m, q, b):
    return {"folders": [r["path"] for r in db.q("SELECT path FROM folders ORDER BY path")]}


@route("POST", r"/api/folders")
def add_folder(h, m, q, b):
    p = Path(b.get("path", "")).expanduser()
    if not p.is_dir():
        raise ApiError(400, "That folder doesn't exist")
    db.run("INSERT OR IGNORE INTO folders(path) VALUES(?)", (str(p),))
    library.scan()
    return {"ok": True}


@route("POST", r"/api/folders/remove")
def rm_folder(h, m, q, b):
    db.run("DELETE FROM folders WHERE path=?", (b.get("path"),))
    db.run("DELETE FROM tracks WHERE path LIKE ?", (str(b.get("path")) + "%",))
    return {"ok": True}


@route("GET", r"/api/playlists")
def playlists(h, m, q, b):
    out = []
    for p in db.q("SELECT * FROM playlists ORDER BY created"):
        items = db.q("SELECT track FROM playlist_items WHERE playlist_id=? ORDER BY pos", (p["id"],))
        tr = [json.loads(i["track"]) for i in items]
        out.append({"id": p["id"], "name": p["name"], "count": len(tr), "arts": [t.get("art") for t in tr if t.get("art")][:4]})
    return {"playlists": out}


@route("POST", r"/api/playlists")
def new_playlist(h, m, q, b):
    name = (b.get("name") or "").strip() or "New playlist"
    pid = db.run("INSERT INTO playlists(name, created) VALUES(?, ?)", (name, time.time()))
    for t in b.get("tracks", []):
        _add_item(pid, t)
    return {"id": pid, "name": name}


def _add_item(pid, t):
    pos = (db.q("SELECT MAX(pos) p FROM playlist_items WHERE playlist_id=?", (pid,), one=True)["p"] or 0) + 1
    db.run("INSERT INTO playlist_items(playlist_id, pos, track) VALUES(?,?,?)", (pid, pos, json.dumps(t)))


@route("GET", r"/api/playlists/(\d+)")
def playlist(h, m, q, b):
    p = db.q("SELECT * FROM playlists WHERE id=?", (m.group(1),), one=True)
    if not p:
        raise ApiError(404, "Playlist not found")
    items = db.q("SELECT id, track FROM playlist_items WHERE playlist_id=? ORDER BY pos", (p["id"],))
    tracks = []
    for i in items:
        t = json.loads(i["track"])
        t["item_id"] = i["id"]
        tracks.append(t)
    return {"id": p["id"], "name": p["name"], "tracks": tracks}


@route("POST", r"/api/playlists/(\d+)/rename")
def rename_pl(h, m, q, b):
    db.run("UPDATE playlists SET name=? WHERE id=?", (b.get("name", "Playlist"), m.group(1)))
    return {"ok": True}


@route("POST", r"/api/playlists/(\d+)/delete")
def delete_pl(h, m, q, b):
    db.run("DELETE FROM playlist_items WHERE playlist_id=?", (m.group(1),))
    db.run("DELETE FROM playlists WHERE id=?", (m.group(1),))
    return {"ok": True}


@route("POST", r"/api/playlists/(\d+)/add")
def add_to_pl(h, m, q, b):
    for t in b.get("tracks", []):
        _add_item(int(m.group(1)), t)
    return {"ok": True}


@route("POST", r"/api/playlists/(\d+)/remove")
def rm_from_pl(h, m, q, b):
    db.run("DELETE FROM playlist_items WHERE id=? AND playlist_id=?", (b.get("item_id"), m.group(1)))
    return {"ok": True}


@route("GET", r"/api/likes")
def likes(h, m, q, b):
    return {"tracks": [json.loads(r["track"]) for r in db.q("SELECT track FROM likes ORDER BY ts DESC")]}


@route("POST", r"/api/like")
def like(h, m, q, b):
    t = b["track"]
    if db.q("SELECT 1 FROM likes WHERE key=?", (t["key"],), one=True):
        db.run("DELETE FROM likes WHERE key=?", (t["key"],))
        return {"liked": False}
    db.run("INSERT INTO likes(key, track, ts) VALUES(?,?,?)", (t["key"], json.dumps(t), time.time()))
    return {"liked": True}


@route("POST", r"/api/played")
def played(h, m, q, b):
    t = b["track"]
    db.run("INSERT INTO history(key, track, ts) VALUES(?,?,?)", (t["key"], json.dumps(t), time.time()))
    return {"ok": True}


@route("POST", r"/api/radio")
def radio(h, m, q, b):
    try:
        vid = providers.video_id_for(b["track"])
        return {"tracks": providers.radio(vid, 30)}
    except Exception as e:
        raise ApiError(502, f"Couldn't build a radio: {str(e)[:140]}")


@route("GET", r"/api/resolve")
def resolve(h, m, q, b):
    try:
        src = q.get("src", "yt")
        tid = q.get("id", "")
        track = {"source": src, "key": ("aud:" if src == "audius" else "jam:" if src == "jamendo" else "yt:" if src == "yt" else "" ) + tid,
                 "video_id": tid if src == "yt" else None,
                 "audius_id": tid if src == "audius" else None,
                 "jamendo_id": tid if src == "jamendo" else None,
                 "preview_url": q.get("preview", "") or None,
                 "title": q.get("t", ""), "artist": q.get("a", ""), "duration": float(q.get("d") or 0)}
        info = providers.resolve_source(track)
    except Exception as e:
        raise ApiError(502, f"Couldn't load this track: {str(e)[:160]}")
    return info


@route("POST", r"/api/download")
def download(h, m, q, b):
    return downloader.start(b["track"], b.get("format"))


@route("POST", r"/api/download/many")
def download_many(h, m, q, b):
    return {"jobs": [downloader.start(t, b.get("format")) for t in b.get("tracks", [])]}


@route("GET", r"/api/downloads")
def downloads(h, m, q, b):
    return {"jobs": downloader.jobs()}


@route("GET", r"/api/settings")
def get_settings(h, m, q, b):
    return db.get_settings()


@route("POST", r"/api/settings")
def set_settings(h, m, q, b):
    db.set_settings(b)
    return db.get_settings()


# ------------------------------------------------------------------ streaming
def _send_headers(h, code, headers):
    h.send_response(code)
    for k, v in headers.items():
        h.send_header(k, v)
    h.end_headers()


def _pipe(h, src, length=None):
    try:
        while True:
            chunk = src.read(65536)
            if not chunk:
                break
            h.wfile.write(chunk)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        h.close_connection = True


def serve_file(h, path):
    p = Path(path)
    if not p.is_file():
        raise ApiError(404, "File missing")
    size = p.stat().st_size
    ctype = library.MIME.get(p.suffix.lower()) or mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    start, end, code = 0, size - 1, 200
    rng = h.headers.get("Range")
    if rng:
        mm = re.match(r"bytes=(\d*)-(\d*)", rng)
        if mm:
            if mm.group(1):
                start = int(mm.group(1))
                end = int(mm.group(2)) if mm.group(2) else size - 1
            elif mm.group(2):
                start = max(0, size - int(mm.group(2)))
            end = min(end, size - 1)
            code = 206
    if start > end:
        _send_headers(h, 416, {"Content-Range": f"bytes */{size}", "Content-Length": "0"})
        return
    hdrs = {"Content-Type": ctype, "Accept-Ranges": "bytes", "Content-Length": str(end - start + 1),
            "Cache-Control": "no-cache"}
    if code == 206:
        hdrs["Content-Range"] = f"bytes {start}-{end}/{size}"
    _send_headers(h, code, hdrs)
    with open(p, "rb") as f:
        f.seek(start)
        left = end - start + 1
        try:
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                h.wfile.write(chunk)
                left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            h.close_connection = True


def proxy_stream(h, vid, retry=True):
    info = providers.resolve(vid)
    client_range = h.headers.get("Range")
    hdrs = dict(info["headers"])
    hdrs["Range"] = client_range or "bytes=0-"
    try:
        resp = urllib.request.urlopen(urllib.request.Request(info["url"], headers=hdrs), timeout=25)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404, 410) and retry:
            providers.invalidate(vid)
            return proxy_stream(h, vid, False)
        raise ApiError(502, f"Upstream returned {e.code}")
    code = resp.status
    out = {"Accept-Ranges": "bytes", "Content-Type": resp.headers.get("Content-Type", "audio/webm"),
           "Cache-Control": "private, max-age=120"}
    if resp.headers.get("Content-Length"):
        out["Content-Length"] = resp.headers["Content-Length"]
    else:
        h.close_connection = True
    if resp.headers.get("Content-Range") and client_range:
        out["Content-Range"] = resp.headers["Content-Range"]
    if not client_range and code == 206:
        code = 200
    _send_headers(h, code, out)
    _pipe(h, resp)
    resp.close()


@route("GET", r"/stream/yt/([\w-]+)")
def stream_yt(h, m, q, b):
    proxy_stream(h, m.group(1))


def proxy_external(h, url, headers=None):
    """Proxy provider-native audio through Aura's origin so the Web Audio analyser works without CORS gaps."""
    out_headers = {"User-Agent": "AuraMusicPlayer/2.1", "Accept": "*/*"}
    out_headers.update(headers or {})
    client_range = h.headers.get("Range")
    if client_range:
        out_headers["Range"] = client_range
    try:
        req = urllib.request.Request(url, headers=out_headers)
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        code = e.code if e.code in (403, 404, 416, 429) else 502
        detail = "Upstream rejected the stream" if code == 502 else f"Provider returned HTTP {code}"
        raise ApiError(code, detail)
    except Exception as e:
        raise ApiError(502, f"Could not open provider stream: {str(e)[:120]}")
    try:
        code = getattr(resp, "status", 200) or 200
        out = {
            "Content-Type": resp.headers.get("Content-Type", "audio/mpeg"),
            "Accept-Ranges": resp.headers.get("Accept-Ranges", "bytes"),
            "Cache-Control": "private, max-age=60",
        }
        for k in ("Content-Length", "Content-Range"):
            value = resp.headers.get(k)
            if value and (k != "Content-Range" or client_range):
                out[k] = value
        if not out.get("Content-Length"):
            # Streaming responses can be chunked/unknown-length; close after this response.
            h.close_connection = True
        if not client_range and code == 206:
            code = 200
            out.pop("Content-Range", None)
        _send_headers(h, code, out)
        _pipe(h, resp)
    finally:
        resp.close()


@route("GET", r"/stream/audius/([\w-]+)")
def stream_audius(h, m, q, b):
    url, headers = providers.audius_file_url(m.group(1), "stream")
    proxy_external(h, url, headers)


@route("GET", r"/stream/jamendo/([\w-]+)")
def stream_jamendo(h, m, q, b):
    url = providers.jamendo_file_url(m.group(1), "stream")
    proxy_external(h, url)


@route("GET", r"/local/(\w+)")
def local_file(h, m, q, b):
    path = library.get_path(m.group(1))
    if not path:
        raise ApiError(404, "Track not in library")
    serve_file(h, path)


@route("GET", r"/art/(\w+)")
def art(h, m, q, b):
    path = library.get_path(m.group(1))
    res = library.get_art(path) if path else None
    if not res:
        raise ApiError(404, "No artwork")
    data, mime = res
    _send_headers(h, 200, {"Content-Type": mime, "Content-Length": str(len(data)), "Cache-Control": "max-age=86400"})
    h.wfile.write(data)


# ------------------------------------------------------------------ handler
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _allowed(self):
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
            return False
        origin = self.headers.get("Origin")
        return not origin or origin.lower() in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        _send_headers(self, code, {"Content-Type": "application/json", "Content-Length": str(len(data)),
                                   "Cache-Control": "no-store"})
        self.wfile.write(data)

    def _static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        f = (UI / rel).resolve()
        if UI.resolve() not in f.parents and f != UI.resolve() or not f.is_file():
            return self._json({"error": "Not found"}, 404)
        data = f.read_bytes()
        _send_headers(self, 200, {"Content-Type": mimetypes.guess_type(str(f))[0] or "application/octet-stream",
                                  "Content-Length": str(len(data)), "Cache-Control": "no-cache"})
        self.wfile.write(data)

    def _handle(self, method):
        if not self._allowed():
            return self._json({"error": "Forbidden"}, 403)
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        body = {}
        if method == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                try:
                    body = json.loads(self.rfile.read(n))
                except ValueError:
                    return self._json({"error": "Bad JSON"}, 400)
        for meth, rx, fn in ROUTES:
            if meth == method:
                mm = rx.match(u.path)
                if mm:
                    try:
                        res = fn(self, mm, q, body)
                    except ApiError as e:
                        return self._json({"error": e.msg}, e.code)
                    except Exception as e:  # keep the app alive on provider errors
                        return self._json({"error": f"{type(e).__name__}: {str(e)[:160]}"}, 500)
                    if res is not None:
                        self._json(res)
                    return
        if method == "GET" and not u.path.startswith(("/api/", "/stream/", "/local/", "/art/")):
            return self._static(u.path)
        self._json({"error": "Not found"}, 404)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def start(port=0):
    global PORT
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    PORT = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, PORT
