"""Background downloads (yt-dlp) that land in the local library."""
import re
import shutil
import subprocess
import mimetypes
import urllib.error
import urllib.request
from urllib.parse import urlparse
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


def _unique_path(path):
    if not path.exists():
        return path
    for n in range(2, 10000):
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Too many files with the same name")


def _native_download(job, track, fmt, out_dir, base):
    """Download only when the provider explicitly allows the track to be downloaded."""
    source = track.get("source")
    if source == "audius":
        if not track.get("downloadable"):
            raise RuntimeError("This Audius track is not marked downloadable by its creator")
        url, headers = providers.audius_file_url(track.get("audius_id") or str(track.get("key", "")).removeprefix("aud:"), "download")
    elif source == "jamendo":
        if not track.get("downloadable"):
            raise RuntimeError("The artist has not enabled downloads for this Jamendo track")
        url = providers.jamendo_file_url(track.get("jamendo_id") or str(track.get("key", "")).removeprefix("jam:"), "download")
        headers = {"User-Agent": "AuraMusicPlayer/2.1 (user-requested licensed track download)"}
    else:
        return None
    req = urllib.request.Request(url, headers=headers)
    job["status"] = "downloading"
    with urllib.request.urlopen(req, timeout=25) as response:
        total = int(response.headers.get("Content-Length") or 0)
        final_url = response.geturl()
        path_ext = Path(urlparse(final_url).path).suffix.lower()
        ctype = (response.headers.get("Content-Type") or "").split(";")[0].lower()
        ext_map = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/ogg": ".ogg", "audio/flac": ".flac",
                   "audio/mp4": ".m4a", "audio/aac": ".aac", "audio/webm": ".webm", "audio/wav": ".wav", "audio/x-wav": ".wav"}
        ext = path_ext if path_ext in {".mp3", ".ogg", ".flac", ".m4a", ".aac", ".webm", ".wav", ".opus"} else ext_map.get(ctype, ".mp3")
        path = _unique_path(out_dir / (base + ext))
        done = 0
        with open(path, "wb") as dest:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                dest.write(chunk); done += len(chunk)
                if total:
                    job["progress"] = min(88, int(done / total * 88))
        job["status"], job["progress"] = "processing", 90
    if fmt.startswith("mp3") and path.suffix.lower() != ".mp3" and have_ffmpeg():
        quality = fmt.split("_")[1] if "_" in fmt else "320"
        converted = _unique_path(path.with_suffix(".mp3"))
        subprocess.run(["ffmpeg", "-y", "-i", str(path), "-vn", "-codec:a", "libmp3lame", "-b:a", f"{quality}k", str(converted)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=180)
        path.unlink(missing_ok=True); path = converted
    elif fmt.startswith("mp3") and not have_ffmpeg() and path.suffix.lower() != ".mp3":
        job["note"] = "ffmpeg not installed; kept provider's original format"
    return path


def _run(job, track, fmt):
    try:
        s = db.get_settings()
        fmt = fmt or s["download_format"]
        out_dir = Path(s["download_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        job["status"] = "resolving"
        base = _clean(f"{track.get('artist', '')} - {track.get('title', '')}")
        if track.get("source") in ("audius", "jamendo"):
            path = _native_download(job, track, fmt, out_dir, base)
            if path:
                library.index_file(str(path), {"title": track.get("title"), "artist": track.get("artist"),
                                               "album": track.get("album"), "duration": track.get("duration")})
                db.run("INSERT OR IGNORE INTO folders(path) VALUES(?)", (str(out_dir),))
                job.update(status="done", progress=100, path=str(path))
                return
        vid = providers.video_id_for(track)
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
