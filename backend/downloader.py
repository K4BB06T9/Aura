"""Background downloads (yt-dlp) that land in the local library."""
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import db, library, providers

_jobs = {}
_pool = ThreadPoolExecutor(2)


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def jobs():
    return sorted(_jobs.values(), key=lambda j: -j["ts"])


def start(track, fmt=None):
    jid = uuid.uuid4().hex[:8]
    job = {"id": jid, "title": track.get("title", ""), "artist": track.get("artist", ""), "art": track.get("art"),
           "status": "queued", "progress": 0, "error": None, "note": None, "path": None, "ts": time.time()}
    _jobs[jid] = job
    _pool.submit(_run, job, track, fmt)
    return job


def _clean(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s).strip(" .") or "track"


def _run(job, track, fmt):
    try:
        s = db.get_settings()
        fmt = fmt or s["download_format"]
        out_dir = Path(s["download_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        job["status"] = "resolving"
        vid = providers.video_id_for(track)
        base = _clean(f"{track.get('artist', '')} - {track.get('title', '')}")
        post, embed = [], False
        if fmt.startswith("mp3") and have_ffmpeg():
            post.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                         "preferredquality": fmt.split("_")[1] if "_" in fmt else "320"})
            embed = True
        elif fmt.startswith("mp3"):
            job["note"] = "ffmpeg not found - saved in the original format instead"
        if have_ffmpeg():
            post.append({"key": "FFmpegMetadata", "add_metadata": True})
            if embed or s["prefer_aac"]:
                post.append({"key": "EmbedThumbnail"})

        def hook(d):
            if d["status"] == "downloading":
                tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if tot:
                    job["progress"] = min(90, int(d.get("downloaded_bytes", 0) / tot * 90))
                job["status"] = "downloading"
            elif d["status"] == "finished":
                job["progress"], job["status"] = 92, "processing"

        opts = {"outtmpl": str(out_dir / (base + ".%(ext)s")), "progress_hooks": [hook],
                "postprocessors": post, "writethumbnail": any(p["key"] == "EmbedThumbnail" for p in post)}
        info = providers.extract(vid, providers.format_for("max", s["prefer_aac"]), download=True, extra=opts)
        path = None
        for rd in info.get("requested_downloads") or []:
            path = rd.get("filepath") or path
        if not path or not Path(path).exists():
            found = sorted(out_dir.glob(base + ".*"), key=lambda p: p.stat().st_mtime, reverse=True)
            found = [p for p in found if p.suffix.lower() in library.EXTS]
            path = str(found[0]) if found else None
        if not path:
            raise RuntimeError("Download finished but the file could not be found")
        library.index_file(path, {"title": track.get("title"), "artist": track.get("artist"),
                                  "album": track.get("album"), "duration": track.get("duration")})
        db.run("INSERT OR IGNORE INTO folders(path) VALUES(?)", (str(out_dir),))
        job.update(status="done", progress=100, path=path)
    except Exception as e:
        job.update(status="error", error=str(e)[:200])
