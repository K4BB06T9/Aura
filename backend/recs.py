"""Home sections and playlist recommendations built from listening history + likes."""
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from . import db, library, providers

_mix_cache = {}
MIX_TTL = 6 * 3600


def _primary(artist):
    return re.split(r",|&| feat\.| x ", artist or "")[0].strip()


def home():
    hist = db.q("SELECT track, MAX(ts) ts FROM history GROUP BY key ORDER BY ts DESC LIMIT 12")
    recent = [json.loads(r["track"]) for r in hist]
    added = [library.row_track(r) for r in db.q("SELECT * FROM tracks ORDER BY added DESC LIMIT 14")]
    played = {r["key"] for r in db.q("SELECT DISTINCT key FROM history")}
    pool = db.q("SELECT * FROM tracks ORDER BY RANDOM() LIMIT 120")
    unheard = [library.row_track(r) for r in pool if "local:" + r["id"] not in played][:14]
    mixes = []
    total = db.q("SELECT COUNT(*) c FROM tracks", one=True)["c"]
    if total >= 10:
        mixes.append({"title": "Library shuffle", "subtitle": "A random pull from your collection",
                      "tracks": [library.row_track(r) for r in db.q("SELECT * FROM tracks ORDER BY RANDOM() LIMIT 30")]})
    for g in db.q("SELECT genre, COUNT(*) c FROM tracks WHERE genre != '' GROUP BY genre HAVING c >= 5 ORDER BY c DESC LIMIT 3"):
        rows = db.q("SELECT * FROM tracks WHERE genre=? ORDER BY RANDOM() LIMIT 30", (g["genre"],))
        mixes.append({"title": f"{g['genre']} mix", "subtitle": f"{g['c']} songs in your library",
                      "tracks": [library.row_track(r) for r in rows]})
    return {"recent": recent, "added": added, "unheard": unheard, "mixes": mixes,
            "counts": {"tracks": total, "likes": db.q("SELECT COUNT(*) c FROM likes", one=True)["c"],
                       "playlists": db.q("SELECT COUNT(*) c FROM playlists", one=True)["c"]}}


def _seeds(n=3):
    cutoff = time.time() - 60 * 86400
    score, rep = Counter(), {}
    for r in db.q("SELECT track FROM history WHERE ts > ? ORDER BY ts DESC LIMIT 500", (cutoff,)):
        t = json.loads(r["track"])
        a = _primary(t.get("artist"))
        if a and a != "Unknown Artist":
            score[a] += 1
            rep.setdefault(a, t)
    for r in db.q("SELECT track FROM likes ORDER BY ts DESC LIMIT 100"):
        t = json.loads(r["track"])
        a = _primary(t.get("artist"))
        if a and a != "Unknown Artist":
            score[a] += 3
            rep.setdefault(a, t)
    return [(a, rep[a]) for a, _ in score.most_common(n)]


def _mix_for(artist, track):
    hit = _mix_cache.get(artist)
    if hit and hit[0] > time.time():
        return hit[1]
    vid = providers.video_id_for(track)
    tracks = providers.radio(vid, 30)
    mix = {"title": f"Because you play {artist}", "subtitle": "Fresh picks from YouTube Music", "tracks": tracks}
    _mix_cache[artist] = (time.time() + MIX_TTL, mix)
    return mix


def mixes():
    seeds = _seeds(3)
    if not seeds:
        return {"mixes": [], "reason": "Play or like a few songs and personalised mixes will appear here."}
    out, errors = [], []

    def work(s):
        try:
            return _mix_for(*s)
        except Exception as e:
            errors.append(str(e)[:120])
            return None

    with ThreadPoolExecutor(3) as ex:
        res = [m for m in ex.map(work, seeds) if m and m["tracks"]]
    if len(res) >= 2:
        heard = {r["key"] for r in db.q("SELECT DISTINCT key FROM history")}
        seen, merged = set(), []
        for i in range(max(len(m["tracks"]) for m in res)):
            for m in res:
                if i < len(m["tracks"]):
                    t = m["tracks"][i]
                    if t["key"] not in seen and t["key"] not in heard:
                        seen.add(t["key"])
                        merged.append(t)
        out.append({"title": "Discover mix", "subtitle": "New songs blended from your favourite artists",
                    "tracks": merged[:40]})
    out.extend(res)
    return {"mixes": out, "errors": errors}
