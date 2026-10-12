"""Local library: scanning, tags, search, cover art."""
import hashlib
import os
import threading
import time
from pathlib import Path

from . import db

try:
    import mutagen
except Exception:  # mutagen is optional; falls back to filenames
    mutagen = None

EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".aif", ".alac", ".ape"}
LOSSLESS = {".flac", ".wav", ".aiff", ".aif", ".alac", ".ape"}
MIME = {".mp3": "audio/mpeg", ".flac": "audio/flac", ".wav": "audio/wav", ".m4a": "audio/mp4",
        ".aac": "audio/aac", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".aiff": "audio/aiff",
        ".aif": "audio/aiff", ".wma": "audio/x-ms-wma", ".webm": "audio/webm"}

status = {"running": False, "scanned": 0, "total": 0, "added": 0, "done": 0}


def track_id(path):
    return hashlib.sha1(str(path).encode("utf-8", "ignore")).hexdigest()[:16]


def read_tags(p: Path):
    d = dict(title=p.stem, artist="Unknown Artist", album="Unknown Album", genre="", year="", track_no=0,
             duration=0.0, codec=p.suffix[1:].upper(), bitrate=0, sample_rate=0, bit_depth=0,
             lossless=1 if p.suffix.lower() in LOSSLESS else 0)
    if " - " in p.stem:
        a, t = p.stem.split(" - ", 1)
        d["artist"], d["title"] = a.strip() or d["artist"], t.strip() or d["title"]
    if not mutagen:
        return d
    try:
        f = mutagen.File(str(p), easy=True)
        if f is None:
            return d

        def tag(k):
            try:
                v = f.tags.get(k) if f.tags else None
                return str(v[0]).strip() if v else ""
            except Exception:
                return ""

        d["title"] = tag("title") or d["title"]
        d["artist"] = tag("artist") or tag("albumartist") or d["artist"]
        d["album"] = tag("album") or d["album"]
        d["genre"] = tag("genre")
        d["year"] = tag("date")[:4]
        try:
            d["track_no"] = int(tag("tracknumber").split("/")[0] or 0)
        except ValueError:
            pass
        info = f.info
        d["duration"] = float(getattr(info, "length", 0) or 0)
        d["bitrate"] = int((getattr(info, "bitrate", 0) or 0) / 1000)
        d["sample_rate"] = int(getattr(info, "sample_rate", 0) or 0)
        d["bit_depth"] = int(getattr(info, "bits_per_sample", 0) or 0)
        codec = str(getattr(info, "codec", "") or "")
        if codec.lower() == "alac":
            d["codec"], d["lossless"] = "ALAC", 1
        elif p.suffix.lower() == ".m4a":
            d["codec"] = "AAC"
    except Exception:
        pass
    return d


def _insert(p: Path, mtime, overrides=None):
    d = read_tags(p)
    if overrides:
        for k in ("title", "artist", "album"):
            if overrides.get(k):
                d[k] = overrides[k]
        if not d["duration"] and overrides.get("duration"):
            d["duration"] = overrides["duration"]
    tid = track_id(p)
    search = db.norm(f"{d['title']} {d['artist']} {d['album']}")
    old = db.q("SELECT added FROM tracks WHERE id=?", (tid,), one=True)
    db.run("""INSERT OR REPLACE INTO tracks(id,path,title,artist,album,genre,year,track_no,duration,codec,bitrate,
              sample_rate,bit_depth,lossless,mtime,added,search) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
           (tid, str(p), d["title"], d["artist"], d["album"], d["genre"], d["year"], d["track_no"], d["duration"],
            d["codec"], d["bitrate"], d["sample_rate"], d["bit_depth"], d["lossless"], mtime,
            old["added"] if old else time.time(), search))
    return tid


def index_file(path, overrides=None):
    p = Path(path)
    return _insert(p, p.stat().st_mtime, overrides)


def scan(folders=None):
    if status["running"]:
        return
    folders = folders or [r["path"] for r in db.q("SELECT path FROM folders")]
    status.update(running=True, scanned=0, total=0, added=0, done=0)

    def work():
        files = []
        for root in folders:
            for dirpath, _, names in os.walk(root):
                for n in names:
                    if Path(n).suffix.lower() in EXTS:
                        files.append(Path(dirpath) / n)
        status["total"] = len(files)
        known = {r["path"]: r["mtime"] for r in db.q("SELECT path, mtime FROM tracks")}
        seen = set()
        for p in files:
            seen.add(str(p))
            try:
                m = p.stat().st_mtime
                if known.get(str(p)) != m:
                    _insert(p, m)
                    status["added"] += 1
            except Exception:
                pass
            status["scanned"] += 1
        roots = tuple(str(Path(f)) for f in folders)
        for path in list(known):
            if path.startswith(roots) and path not in seen:
                db.run("DELETE FROM tracks WHERE path=?", (path,))
        status.update(running=False, done=1)

    threading.Thread(target=work, daemon=True).start()


def row_track(r):
    return {
        "key": "local:" + r["id"], "source": "local", "local_id": r["id"], "title": r["title"],
        "artist": r["artist"], "album": r["album"], "genre": r["genre"], "year": r["year"],
        "duration": r["duration"], "art": "/art/" + r["id"], "no": r["track_no"],
        "q": {"codec": r["codec"], "bitrate": r["bitrate"], "sample_rate": r["sample_rate"],
              "bit_depth": r["bit_depth"], "lossless": bool(r["lossless"])},
    }


def all_tracks():
    return [row_track(r) for r in db.q("SELECT * FROM tracks ORDER BY artist COLLATE NOCASE, album COLLATE NOCASE, track_no, title COLLATE NOCASE")]


def search(text, limit=40):
    toks = db.norm(text).split()
    if not toks:
        return []
    where = " AND ".join(["search LIKE ?"] * len(toks))
    rows = db.q(f"SELECT * FROM tracks WHERE {where} LIMIT 300", tuple(f"%{t}%" for t in toks))
    full = " ".join(toks)

    def score(r):
        t = db.norm(r["title"])
        if t == full:
            return 0
        if t.startswith(full):
            return 1
        if full in t:
            return 2
        return 3

    rows = sorted(rows, key=lambda r: (score(r), db.norm(r["title"])))
    return [row_track(r) for r in rows[:limit]]


def get_path(tid):
    r = db.q("SELECT path FROM tracks WHERE id=?", (tid,), one=True)
    return r["path"] if r else None


def get_art(path):
    p = Path(path)
    data = None
    if mutagen:
        try:
            f = mutagen.File(str(p))
            if f is not None:
                if getattr(f, "pictures", None):
                    data = f.pictures[0].data
                elif f.tags:
                    for k in f.tags.keys():
                        if str(k).startswith("APIC"):
                            data = f.tags[k].data
                            break
                    if data is None and "covr" in f.tags:
                        data = bytes(f.tags["covr"][0])
        except Exception:
            data = None
    if data is None:
        for name in ("cover", "folder", "front", "album", "Cover", "Folder"):
            for ext in (".jpg", ".jpeg", ".png"):
                c = p.parent / (name + ext)
                if c.exists():
                    data = c.read_bytes()
                    break
            if data:
                break
    if not data:
        return None
    return data, ("image/png" if data[:4] == b"\x89PNG" else "image/jpeg")
