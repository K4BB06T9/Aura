"""Online catalogs (YouTube Music, Spotify) and ad-free stream resolution via yt-dlp."""
import base64
import json
import re
import threading
import time
import urllib.parse
import urllib.request

from . import db

_yt = None
_yt_lock = threading.Lock()
_stream_cache = {}
_match_cache = {}
_sp_tok = {"v": None, "exp": 0}


# ---------- YouTube Music ----------
def ytm():
    global _yt
    with _yt_lock:
        if _yt is None:
            from ytmusicapi import YTMusic
            _yt = YTMusic()
        return _yt


def _dur(v):
    if isinstance(v, (int, float)):
        return float(v)
    if not v:
        return 0.0
    try:
        parts = [int(x) for x in str(v).split(":")]
        s = 0
        for p in parts:
            s = s * 60 + p
        return float(s)
    except ValueError:
        return 0.0


def _big(url):
    if not url:
        return None
    return re.sub(r"=w\d+-h\d+[^&]*$", "=w544-h544-l90-rj", url)


def _map_yt(r):
    vid = r.get("videoId")
    if not vid:
        return None
    artists = r.get("artists") or []
    artist = ", ".join(a.get("name", "") for a in artists if a.get("name")) or r.get("author") or ""
    th = r.get("thumbnails") or r.get("thumbnail") or []
    alb = r.get("album")
    return {
        "key": "yt:" + vid, "source": "yt", "video_id": vid, "title": r.get("title") or "",
        "artist": artist, "album": alb.get("name", "") if isinstance(alb, dict) else "",
        "duration": r.get("duration_seconds") or _dur(r.get("duration") or r.get("length")),
        "art": _big(th[-1]["url"]) if th else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
    }


def search_yt(text, limit=20, kind="songs"):
    res = ytm().search(text, filter=kind, limit=limit)
    out = [t for t in (_map_yt(r) for r in res) if t]
    if not out and kind == "songs":
        out = search_yt(text, limit, "videos")
    return out


def radio(video_id, limit=30):
    res = ytm().get_watch_playlist(video_id, limit=limit, radio=True)
    out = [t for t in (_map_yt(r) for r in res.get("tracks", [])) if t]
    return [t for t in out if t["video_id"] != video_id]


def video_id_for(track):
    """Return a YouTube video id for any track (yt direct, spotify/local matched by search)."""
    if track.get("video_id"):
        return track["video_id"]
    return match(track.get("title", ""), track.get("artist", ""), track.get("duration", 0))


def match(title, artist, duration=0):
    key = (title.lower(), artist.lower())
    if key in _match_cache:
        return _match_cache[key]
    results = search_yt(f"{title} {artist}".strip(), limit=6)
    if not results:
        raise RuntimeError("No online match found for this track")
    best = results[0]
    if duration:
        best = min(results, key=lambda r: abs((r["duration"] or 0) - duration) if r["duration"] else 9999)
    _match_cache[key] = best["video_id"]
    return best["video_id"]


# ---------- Spotify (catalog metadata only; audio is matched on YouTube Music) ----------
def sp_token():
    s = db.get_settings()
    cid, sec = s.get("spotify_id"), s.get("spotify_secret")
    if not cid or not sec:
        return None
    if _sp_tok["v"] and time.time() < _sp_tok["exp"]:
        return _sp_tok["v"]
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=b"grant_type=client_credentials",
                                 headers={"Authorization": "Basic " + auth,
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=12) as r:
        d = json.loads(r.read())
    _sp_tok.update(v=d["access_token"], exp=time.time() + d.get("expires_in", 3600) - 60)
    return _sp_tok["v"]


def search_sp(text, limit=10):
    tok = sp_token()
    if not tok:
        return []
    url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode({"q": text, "type": "track", "limit": limit})
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=12) as r:
        items = json.loads(r.read()).get("tracks", {}).get("items", [])
    out = []
    for i in items:
        imgs = i.get("album", {}).get("images") or []
        out.append({"key": "sp:" + i["id"], "source": "sp", "sp_id": i["id"], "title": i["name"],
                    "artist": ", ".join(a["name"] for a in i.get("artists", [])),
                    "album": i.get("album", {}).get("name", ""), "duration": (i.get("duration_ms") or 0) / 1000,
                    "art": imgs[0]["url"] if imgs else None})
    return out


# ---------- Stream resolution ----------
def format_for(quality, prefer_aac=False):
    cap = {"low": 64, "normal": 128, "high": 192, "max": None}.get(quality, 192)
    ext = "[ext=m4a]" if prefer_aac else ""
    if cap:
        return f"bestaudio{ext}[abr<={cap}]/bestaudio[abr<={cap}]/bestaudio{ext}/bestaudio/best"
    return f"bestaudio{ext}/bestaudio/best"


_ANSI = re.compile(r"\x1b\[[0-9;]*m|\[[0-9;]*m")


def friendly(e):
    msg = _ANSI.sub("", str(e)).replace("ERROR:", "").strip()
    if "Sign in" in msg or "not a bot" in msg:
        return "YouTube wants a sign-in check. Open Settings > YouTube access and pick the browser you're signed in to YouTube with."
    if "cookies" in msg.lower() and "database" in msg.lower():
        return "Couldn't read browser cookies. Close that browser completely and try again, or pick another browser in Settings."
    return msg[:150]


def ydl_opts(fmt, variant=0):
    s = db.get_settings()
    o = {"quiet": True, "no_warnings": True, "noplaylist": True, "format": fmt}
    if s.get("cookies_file"):
        o["cookiefile"] = s["cookies_file"]
    elif s.get("cookies_browser"):
        o["cookiesfrombrowser"] = (s["cookies_browser"],)
    if variant == 1:
        o["extractor_args"] = {"youtube": {"player_client": ["tv", "android_vr"]}}
    elif variant == 2:
        o["extractor_args"] = {"youtube": {"player_client": ["mweb", "web_safari"]}}
    return o


def extract(vid, fmt, download=False, extra=None):
    """Run yt-dlp, retrying with other player clients if YouTube shows its bot check."""
    import yt_dlp
    last = None
    for variant in (0, 1, 2):
        o = ydl_opts(fmt, variant)
        o.update(extra or {})
        try:
            with yt_dlp.YoutubeDL(o) as ydl:
                return ydl.extract_info("https://music.youtube.com/watch?v=" + vid, download=download)
        except Exception as e:
            last = e
            if "Sign in" not in str(e) and "bot" not in str(e).lower():
                break
    raise RuntimeError(friendly(last))


def resolve(vid, quality=None):
    s = db.get_settings()
    fmt = format_for(quality or s["stream_quality"], s["prefer_aac"])
    key = (vid, fmt)
    hit = _stream_cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    info = extract(vid, fmt)
    out = {"url": info["url"], "headers": info.get("http_headers", {}), "ext": info.get("ext"),
           "codec": (info.get("acodec") or "").split(".")[0], "abr": int(info.get("abr") or 0),
           "asr": info.get("asr")}
    _stream_cache[key] = (time.time() + 2 * 3600, out)
    return out


def invalidate(vid):
    for k in [k for k in _stream_cache if k[0] == vid]:
        _stream_cache.pop(k, None)
