"""SQLite storage + settings for Aura."""
import json
import os
import sqlite3
import sys
import threading
import unicodedata
from pathlib import Path

HOME = Path(os.environ.get("AURA_HOME") or (Path.home() / ".aura"))
HOME.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks(
  id TEXT PRIMARY KEY, path TEXT UNIQUE, title TEXT, artist TEXT, album TEXT, genre TEXT, year TEXT,
  track_no INTEGER, duration REAL, codec TEXT, bitrate INTEGER, sample_rate INTEGER, bit_depth INTEGER,
  lossless INTEGER, mtime REAL, added REAL, search TEXT);
CREATE INDEX IF NOT EXISTS ix_tracks_added ON tracks(added);
CREATE TABLE IF NOT EXISTS folders(path TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS playlists(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, created REAL);
CREATE TABLE IF NOT EXISTS playlist_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, playlist_id INTEGER, pos INTEGER, track TEXT);
CREATE INDEX IF NOT EXISTS ix_pi ON playlist_items(playlist_id, pos);
CREATE TABLE IF NOT EXISTS likes(key TEXT PRIMARY KEY, track TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, track TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS ix_hist ON history(ts);
CREATE TABLE IF NOT EXISTS search_history(query_key TEXT PRIMARY KEY, query TEXT NOT NULL, ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_search_history_ts ON search_history(ts);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
"""

_lock = threading.RLock()
_db = sqlite3.connect(str(HOME / "aura.db"), check_same_thread=False)
_db.row_factory = sqlite3.Row
_db.executescript(SCHEMA)
_db.commit()


def q(sql, args=(), one=False):
    with _lock:
        rows = _db.execute(sql, args).fetchall()
        _db.commit()
    if one:
        return rows[0] if rows else None
    return rows


def run(sql, args=()):
    with _lock:
        cur = _db.execute(sql, args)
        _db.commit()
        return cur.lastrowid


def many(sql, seq):
    with _lock:
        _db.executemany(sql, seq)
        _db.commit()


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


DEFAULTS = {
    "stream_quality": "high",          # low | normal | high | max
    "prefer_aac": sys.platform == "darwin",
    "autoplay_similar": True,
    "always_online": False,
    "download_format": "original",     # original | mp3_320 | mp3_192
    "download_dir": str(Path.home() / "Music" / "Aura"),
    "accent": "#ff681f",
    "skip_seconds": 10,
    "mini_color": "#ff5b1f",
    "mini_opacity": 72,
    "mini_width": 76,
    "mini_height": 78,
    "mini_player_mode": False,
    "floating_width": 520,
    "floating_height": 88,
    "card_size": "medium",
    "card_round": False,
    "shelf_gap": 16,
    "spotify_id": "",
    "spotify_secret": "",
    "jamendo_client_id": "",
    "audius_api_token": "",
    "cookies_browser": "",             # chrome | edge | firefox | brave | ""
    "cookies_file": "",
    "output_rate": 0,                  # 0 = device default
    "volume": 0.85,
    "eq": None,
    "eq_presets": {},
}


def get_settings():
    out = dict(DEFAULTS)
    for r in q("SELECT k, v FROM settings"):
        try:
            out[r["k"]] = json.loads(r["v"])
        except Exception:
            pass
    return out


def set_settings(d):
    for k, v in d.items():
        if k in DEFAULTS:
            run("INSERT OR REPLACE INTO settings(k, v) VALUES(?, ?)", (k, json.dumps(v)))
