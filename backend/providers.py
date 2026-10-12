"""Music catalogs (YouTube Music, iTunes, MusicBrainz, optional Spotify) and stream resolution."""
import base64
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import db

_yt = None
_yt_lock = threading.Lock()
_stream_cache = {}
_match_cache = {}
_sp_tok = {"v": None, "exp": 0}
_mb_lock = threading.Lock()
_mb_last = 0.0
_mb_cache = {}
_audius_cache = {}
_jamendo_cache = {}
AUDIOUS_APP_NAME = "AuraDesktop"


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



def _as_bool(value):
    """Parse API permission flags without treating strings such as 'false' as truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value or "").strip().casefold() in {"true", "1", "yes", "allowed"}

def _count_views(value):
    text = str(value or "").strip().lower().replace(",", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmb])?", text)
    if not match:
        return 0
    scale = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(match.group(2), 1)
    try:
        return int(float(match.group(1)) * scale)
    except ValueError:
        return 0


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
        "release_date": r.get("releaseDate") or r.get("year") or "",
        "year": r.get("year") or "",
        "views": _count_views(r.get("views") or r.get("viewCount") or 0),
        "art": _big(th[-1]["url"]) if th else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
    }


def search_yt(text, limit=20, kind="songs"):
    res = ytm().search(text, filter=kind, limit=limit)
    out = [t for t in (_map_yt(r) for r in res) if t]
    if not out and kind == "songs":
        out = search_yt(text, limit, "videos")
    return out


def search_yt_collections(text, limit=20, kind="playlists"):
    """Search YouTube Music collections/artists. These are catalog links, not playable tracks."""
    filt = "artists" if kind in ("artists", "channels") else "playlists"
    res = ytm().search(text, filter=filt, limit=limit)
    out = []
    for item in res:
        thumbs = item.get("thumbnails") or item.get("thumbnail") or []
        art = _big(thumbs[-1].get("url")) if thumbs else None
        if filt == "playlists":
            pid = item.get("playlistId") or item.get("browseId")
            if not pid:
                continue
            out.append({"key": "ytpl:" + pid, "kind": "playlist", "title": item.get("title") or "Untitled playlist",
                        "artist": item.get("author") or "YouTube Music", "art": art,
                        "url": "https://music.youtube.com/playlist?list=" + urllib.parse.quote(pid)})
        else:
            bid = item.get("browseId")
            title = item.get("artist") or item.get("title") or item.get("name")
            if not bid or not title:
                continue
            out.append({"key": "ytartist:" + bid, "kind": "channel", "title": title,
                        "artist": "Artist / channel", "art": art,
                        "url": "https://music.youtube.com/channel/" + urllib.parse.quote(bid)})
    return out


def search_itunes(text, limit=20):
    """Search Apple's public iTunes catalog API. Preview availability varies by track and region."""
    params = urllib.parse.urlencode({"term": text, "media": "music", "entity": "song", "limit": min(max(int(limit), 1), 50)})
    req = urllib.request.Request("https://itunes.apple.com/search?" + params,
                                 headers={"User-Agent": "AuraMusicPlayer/1.0 (catalog search)"})
    with urllib.request.urlopen(req, timeout=8) as r:
        items = json.loads(r.read()).get("results", [])
    out = []
    for item in items:
        if not item.get("trackName"):
            continue
        art = item.get("artworkUrl100")
        if art:
            art = re.sub(r"/\d+x\d+bb\.(jpg|png)$", r"/600x600bb.\1", art)
        tid = str(item.get("trackId") or item.get("collectionId") or item.get("trackName"))
        out.append({"key": "itunes:" + tid, "source": "itunes", "kind": "track", "title": item.get("trackName", ""),
                    "artist": item.get("artistName", ""), "album": item.get("collectionName", ""),
                    "duration": (item.get("trackTimeMillis") or 0) / 1000, "art": art,
                    "preview_url": item.get("previewUrl"), "release_date": item.get("releaseDate", ""),
                    "genre": item.get("primaryGenreName", ""), "store_url": item.get("trackViewUrl", "")})
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
                    "popularity": i.get("popularity", 0), "release_date": i.get("album", {}).get("release_date", ""),
                    "art": imgs[0]["url"] if imgs else None})
    return out



def search_musicbrainz(text, limit=12):
    """Search the free MusicBrainz recording catalog. Audio playback is matched via YouTube Music."""
    global _mb_last
    key = (text or "").strip().lower()
    if not key:
        return []
    cached = _mb_cache.get(key)
    if cached and cached[0] > time.time():
        return cached[1]
    # MusicBrainz asks public clients to stay at or below one request per second.
    with _mb_lock:
        wait = 1.05 - (time.time() - _mb_last)
        if wait > 0:
            time.sleep(wait)
        query = urllib.parse.urlencode({"query": text, "fmt": "json", "limit": min(max(int(limit), 1), 25)})
        req = urllib.request.Request("https://musicbrainz.org/ws/2/recording/?" + query,
                                     headers={"User-Agent": "AuraMusicPlayer/1.0 (music metadata search)"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read())
        _mb_last = time.time()
    out = []
    for item in data.get("recordings", []):
        title = item.get("title")
        if not title:
            continue
        credits = item.get("artist-credit") or []
        artists = []
        for credit in credits:
            if isinstance(credit, dict):
                artist = credit.get("artist") or {}
                name = artist.get("name") or credit.get("name")
                if name and name not in ("&", ","):
                    artists.append(name)
        releases = item.get("releases") or []
        release = releases[0] if releases else {}
        release_id = release.get("id")
        art = f"https://coverartarchive.org/release/{release_id}/front-250" if release_id else None
        rid = str(item.get("id") or title)
        out.append({"key": "mb:" + rid, "source": "mb", "kind": "track", "title": title,
                    "artist": ", ".join(dict.fromkeys(artists)), "album": release.get("title", ""),
                    "duration": (item.get("length") or 0) / 1000, "art": art,
                    "release_date": release.get("date", ""), "year": (release.get("date", "") or "")[:4]})
    _mb_cache[key] = (time.time() + 3600, out)
    return out



# ---------- Audius (free/open streaming catalog) ----------
def _audius_request(path, params=None):
    params = dict(params or {})
    params.setdefault("app_name", AUDIOUS_APP_NAME)
    settings = db.get_settings()
    token = (settings.get("audius_api_token") or "").strip()
    url = "https://api.audius.co/v1/" + path.lstrip("/") + "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "AuraMusicPlayer/2.1 (+local desktop music player)"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=7) as response:
        data = json.loads(response.read())
    return data.get("data", data if isinstance(data, list) else [])


def _audius_art(track):
    art = track.get("artwork") or track.get("cover_art") or {}
    if isinstance(art, dict):
        return art.get("1000x1000") or art.get("480x480") or art.get("150x150") or next(iter(art.values()), None)
    return art or None


def _map_audius(item):
    if not isinstance(item, dict) or not item.get("id") or not item.get("title"):
        return None
    user = item.get("user") or {}
    return {
        "key": "aud:" + str(item["id"]), "source": "audius", "audius_id": str(item["id"]),
        "kind": "track", "title": item.get("title") or "", "artist": user.get("name") or item.get("artist") or "Audius artist",
        "album": item.get("album_title") or "", "duration": float(item.get("duration") or 0),
        "release_date": item.get("release_date") or item.get("date_created") or "", "genre": item.get("genre") or "",
        "views": int(item.get("play_count") or 0), "popularity": int(item.get("play_count") or 0),
        "art": _audius_art(item), "permalink": item.get("permalink") or "",
        "downloadable": _as_bool(item.get("is_downloadable")) or _as_bool(item.get("downloadable")),
        "license": item.get("license") or "See creator's Audius track page",
    }


def search_audius(text, limit=20, sort="relevant"):
    query = (text or "").strip()
    if not query:
        return []
    key = (query.casefold(), int(limit), sort)
    hit = _audius_cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    data = _audius_request("tracks/search", {"query": query, "limit": min(max(int(limit), 1), 50),
                                            "sort_method": sort if sort in ("relevant", "popular", "recent") else "relevant"})
    out = [t for t in (_map_audius(x) for x in (data or [])) if t]
    _audius_cache[key] = (time.time() + 120, out)
    return out


def trending_audius(limit=30, genre=None):
    params = {"limit": min(max(int(limit), 1), 50), "time": "week"}
    if genre:
        # Audius supports filtering tracks by genre on relevant track endpoints; a query is also
        # used so this continues to work if a discovery provider ignores the genre field.
        params["genre"] = genre
    data = _audius_request("tracks/trending", params)
    out = [t for t in (_map_audius(x) for x in (data or [])) if t]
    if genre:
        out = [t for t in out if genre.casefold() in str(t.get("genre", "")).casefold()] or search_audius(genre, limit)
    return out


def audius_related(track, limit=20):
    tid = str(track.get("audius_id") or "")
    if tid:
        try:
            data = _audius_request(f"tracks/{urllib.parse.quote(tid)}/recommended", {"limit": limit})
            out = [t for t in (_map_audius(x) for x in (data or [])) if t and t["key"] != track.get("key")]
            if out:
                return out
        except Exception:
            pass
    # Fallback to the same genre or artist query against the same source, not YT radio.
    q = (track.get("genre") or track.get("artist") or track.get("title") or "electronic").strip()
    return [t for t in search_audius(q, limit) if t.get("key") != track.get("key")]


# ---------- Jamendo (Creative Commons / licensed independent music) ----------
def search_jamendo(text, limit=20, by_genre=False):
    settings = db.get_settings()
    client_id = (settings.get("jamendo_client_id") or "").strip()
    if not client_id or not (text or "").strip():
        return []
    key = ((text or "").casefold(), int(limit), client_id, bool(by_genre))
    hit = _jamendo_cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    params_dict = {"client_id": client_id, "format": "json", "limit": min(max(int(limit), 1), 50),
                   "audioformat": "mp31", "imagesize": 600, "include": "musicinfo", "track_type": "single albumtrack"}
    params_dict["tags" if by_genre else "namesearch"] = text
    params = urllib.parse.urlencode(params_dict, doseq=True)
    req = urllib.request.Request("https://api.jamendo.com/v3.0/tracks/?" + params,
                                 headers={"User-Agent": "AuraMusicPlayer/2.1 (catalog search)"})
    with urllib.request.urlopen(req, timeout=7) as response:
        data = json.loads(response.read())
    out = []
    for item in data.get("results", []):
        tid = str(item.get("id") or "")
        if not tid:
            continue
        tags = item.get("musicinfo", {}).get("tags", {}) or {}
        genres = tags.get("genres") or tags.get("vartags") or []
        out.append({"key": "jam:" + tid, "source": "jamendo", "jamendo_id": tid, "kind": "track",
                    "title": item.get("name") or "", "artist": item.get("artist_name") or "Unknown artist",
                    "album": item.get("album_name") or "", "duration": float(item.get("duration") or 0),
                    "release_date": item.get("releasedate") or item.get("release_date") or "",
                    "genre": ", ".join(genres[:3]) if isinstance(genres, list) else str(genres),
                    "art": item.get("image") or item.get("album_image"), "license": item.get("license_ccurl") or "Jamendo license",
                    "downloadable": _as_bool(item.get("audiodownload_allowed")),
                    "popularity": int(item.get("popularity_week") or item.get("popularity_total") or 0),
                    "store_url": item.get("shareurl") or ""})
    _jamendo_cache[key] = (time.time() + 180, out)
    return out


def jamendo_file_url(track_id, action="stream"):
    client_id = (db.get_settings().get("jamendo_client_id") or "").strip()
    if not client_id:
        raise RuntimeError("Add a free Jamendo API client ID in Settings to play Jamendo tracks")
    params = urllib.parse.urlencode({"client_id": client_id, "id": str(track_id), "action": action, "audioformat": "mp31"})
    return "https://api.jamendo.com/v3.0/tracks/file/?" + params


def audius_file_url(track_id, action="stream"):
    settings = db.get_settings()
    params = {"app_name": AUDIOUS_APP_NAME}
    url = f"https://api.audius.co/v1/tracks/{urllib.parse.quote(str(track_id))}/{action}?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "AuraMusicPlayer/2.1"}
    token = (settings.get("audius_api_token") or "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    return url, headers


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


# ---------- source-aware discovery feeds ----------
_discovery_cache = {}
_discovery_lock = threading.Lock()

def _items_from_chart(section):
    """Tolerate ytmusicapi's changing chart response structure across regions."""
    if isinstance(section, list):
        return section
    if isinstance(section, dict):
        for k in ("items", "tracks", "results"):
            if isinstance(section.get(k), list):
                return section[k]
    return []

def youtube_trending(country="BD", limit=30):
    """Return YouTube Music chart tracks, falling back to its own native search."""
    cache_key = ("yttrend", country, limit)
    cached = _discovery_cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]
    out = []
    try:
        api = ytm()
        charts = api.get_charts(country=country or "ZZ")
        for section_name in ("songs", "trending", "videos"):
            for item in _items_from_chart(charts.get(section_name)):
                mapped = _map_yt(item)
                if mapped and mapped["key"] not in {t["key"] for t in out}:
                    out.append(mapped)
            if len(out) >= limit:
                break
        # Video chart sections may contain playlist cards rather than tracks.
        if len(out) < min(8, limit):
            videos = charts.get("videos")
            if isinstance(videos, list):
                for card in videos:
                    pid = card.get("playlistId") if isinstance(card, dict) else None
                    if not pid:
                        continue
                    try:
                        pl = api.get_playlist(pid, limit=limit)
                        for item in pl.get("tracks", []):
                            mapped = _map_yt(item)
                            if mapped and mapped["key"] not in {t["key"] for t in out}:
                                out.append(mapped)
                    except Exception:
                        pass
                    if len(out) >= limit:
                        break
    except Exception:
        pass
    if len(out) < 8:
        try:
            fallback = search_yt("trending songs", limit)
            seen = {t["key"] for t in out}
            out.extend(t for t in fallback if t["key"] not in seen)
        except Exception:
            pass
    out = out[:limit]
    _discovery_cache[cache_key] = (time.time() + 900, out)
    return out

def youtube_new_releases(limit=30, country="BD"):
    """Use YouTube Music's own Explore/new-release feed and native track IDs when available."""
    cache_key = ("ytnew", country, limit)
    cached = _discovery_cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]
    out = []
    try:
        api = ytm()
        explore = api.get_explore()
        albums = []
        for k in ("new_releases", "newReleases", "newAlbums", "new_albums", "albums"):
            val = explore.get(k) if isinstance(explore, dict) else None
            if isinstance(val, dict): val = val.get("items", [])
            if isinstance(val, list): albums.extend(val)
        seen = set()
        for album in albums:
            if len(out) >= limit: break
            if not isinstance(album, dict): continue
            aid = album.get("browseId") or album.get("albumId") or album.get("id")
            if not aid or aid in seen: continue
            seen.add(aid)
            try:
                detail = api.get_album(aid)
                for item in detail.get("tracks", []):
                    mapped = _map_yt(item)
                    if mapped and mapped["key"] not in {t["key"] for t in out}:
                        mapped["album"] = detail.get("title") or mapped.get("album")
                        mapped["release_date"] = detail.get("year") or album.get("year") or mapped.get("release_date", "")
                        out.append(mapped)
                        if len(out) >= limit: break
            except Exception:
                continue
    except Exception:
        pass
    if not out:
        try: out = search_yt("new music official", limit)
        except Exception: out = []
    _discovery_cache[cache_key] = (time.time() + 1800, out[:limit])
    return out[:limit]


def apple_chart_tracks(kind="most-played", country="us", limit=30):
    """Fetch Apple's public RSS charts. Chart data is metadata; playback follows Aura's resolver."""
    kind = "new-releases" if kind == "new-releases" else "most-played"
    cache_key = ("apple", kind, country, limit)
    cached = _discovery_cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]
    url = f"https://rss.applemarketingtools.com/api/v2/{urllib.parse.quote(country)}/music/{kind}/{min(max(int(limit), 1), 50)}/songs.json"
    req = urllib.request.Request(url, headers={"User-Agent": "AuraMusicPlayer/2.1 (music discovery)"})
    with urllib.request.urlopen(req, timeout=7) as r:
        data = json.loads(r.read())
    feed = data.get("feed", {})
    out = []
    for x in feed.get("results", []):
        title = x.get("name") or ""
        if not title:
            continue
        genres = x.get("genres") or []
        out.append({"key": "apple:" + str(x.get("id") or title), "source": "itunes", "kind": "track",
                    "title": title, "artist": x.get("artistName") or "Unknown artist",
                    "album": x.get("name") or "", "duration": 0, "release_date": x.get("releaseDate") or "",
                    "genre": ", ".join(g.get("name", "") for g in genres if isinstance(g, dict)),
                    "art": x.get("artworkUrl100"), "store_url": x.get("url") or "",
                    "discovery_source": "Apple Music charts"})
    _discovery_cache[cache_key] = (time.time() + 1800, out)
    return out

def discovery_tracks(tab="hot", genre="", country="BD", limit=30):
    """Gather source-native discovery results without pretending metadata APIs stream full audio."""
    tab = (tab or "hot").lower()
    tasks = []
    if tab == "hot":
        tasks = [("ytmusic", lambda: youtube_trending(country, limit)),
                 ("audius", lambda: trending_audius(limit)),
                 ("apple", lambda: apple_chart_tracks("most-played", "us", limit))]
    elif tab == "genres":
        g = (genre or "Pop").strip()
        tasks = [("ytmusic", lambda: search_yt(g + " songs", limit)),
                 ("audius", lambda: trending_audius(limit, g)),
                 ("jamendo", lambda: search_jamendo(g, limit, by_genre=True))]
    elif tab == "releases":
        tasks = [("itunes", lambda: search_itunes("new music", limit)),
                 ("yt", lambda: youtube_new_releases(limit, country))]
    out, errors = [], []
    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as ex:
        futs = [(name, ex.submit(fn)) for name, fn in tasks]
        for name, fut in futs:
            try:
                found = fut.result()
                out.extend(found or [])
            except Exception as e:
                errors.append(f"{name}: {str(e)[:120]}")
    # De-dupe by normalized title/artist while retaining native stream sources when possible.
    seen, merged = set(), []
    for t in out:
        key = (re.sub(r"\W+", " ", (t.get("title") or "").lower()).strip(),
               re.sub(r"\W+", " ", (t.get("artist") or "").lower()).strip())
        if not key[0] or key in seen:
            continue
        seen.add(key); merged.append(t)
    if tab == "releases":
        merged.sort(key=lambda t: str(t.get("release_date") or ""), reverse=True)
    elif tab == "hot":
        merged.sort(key=lambda t: int(t.get("popularity") or t.get("views") or 0), reverse=True)
    selected = merged[:limit]
    grouped = {}
    for t in selected:
        grouped.setdefault(t.get("source", "unknown"), []).append(t)
    return {"tracks": selected, "groups": grouped, "errors": errors,
            "providers": sorted({t.get("source", "") for t in selected})}


def resolve_source(track, quality=None):
    """Resolve a track using its native playable provider when available."""
    src = track.get("source") or "yt"
    if src == "yt":
        vid = track.get("video_id") or track.get("id")
        info = resolve(vid, quality)
        return {"stream": f"/stream/yt/{vid}", "video_id": vid, "codec": info["codec"], "abr": info["abr"],
                "asr": info["asr"], "ext": info["ext"]}
    if src == "audius":
        tid = track.get("audius_id") or str(track.get("key", "")).removeprefix("aud:")
        if not tid:
            raise RuntimeError("Missing Audius track ID")
        return {"stream": f"/stream/audius/{urllib.parse.quote(str(tid), safe='')}", "video_id": None,
                "codec": "audio", "abr": 0, "asr": None, "ext": "stream"}
    if src == "jamendo":
        tid = track.get("jamendo_id") or str(track.get("key", "")).removeprefix("jam:")
        if not tid:
            raise RuntimeError("Missing Jamendo track ID")
        if not (db.get_settings().get("jamendo_client_id") or "").strip():
            raise RuntimeError("Add a free Jamendo API client ID in Settings to play Jamendo tracks")
        return {"stream": f"/stream/jamendo/{urllib.parse.quote(str(tid), safe='')}", "video_id": None,
                "codec": "mp3", "abr": 0, "asr": None, "ext": "mp3"}
    # Spotify, Apple/iTunes, MusicBrainz and chart RSS are discovery/catalog sources rather than
    # unrestricted full-track streams. For these items Aura attempts a title/artist match on YT Music.
    # Apple's preview_url is a short preview only; it is intentionally not substituted for a full track.
    vid = match(track.get("title", ""), track.get("artist", ""), track.get("duration", 0))
    info = resolve(vid, quality)
    return {"stream": f"/stream/yt/{vid}", "video_id": vid, "codec": info["codec"], "abr": info["abr"],
            "asr": info["asr"], "ext": info["ext"]}
