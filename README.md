# Aura

A lightweight desktop music player: local library first, ad-free streaming when you need it, built-in equalizer, downloads.

Python backend + your OS's own web view (pywebview), so there's no bundled Chromium (~30 MB installed vs. 150 MB+ for Electron).

## Run

```bash
pip install -r requirements.txt
python main.py            # native window
python main.py --browser  # or open in your browser
```

Optional: install **ffmpeg** (for MP3 conversion and embedded cover art on downloads).
Linux also needs a pywebview backend (`sudo apt install python3-gi gir1.2-webkit2-4.1` or `pip install pywebview[qt]`).

Package as an app: `pip install pyinstaller && python build.py`

## How search works

1. Your **local library** is searched first (instant, SQLite).
2. If it finds fewer than 3 matches (or "Always search online too" is on), Aura goes online: **YouTube Music**, plus **Spotify** if you add free developer credentials in Settings.
3. Online results already in your library are hidden; everything else plays instantly. Streams are direct audio from yt-dlp, so there are no ads.

Spotify note: Spotify's own audio is DRM-protected, so Aura uses Spotify only for catalog search and matches each track to YouTube Music for playback.

## Features

- Library: MP3, FLAC, WAV, ALAC/AAC (m4a), OGG, OPUS, AIFF, WMA; tags + embedded artwork; rescans on launch
- Recommendations: "Made from your library" mixes, rediscover, plus online mixes built from your history and likes (Discover mix, "Because you play …"), autoplay of similar songs when the queue ends
- Playlists, liked songs, queue (play next / add / remove), shuffle, repeat, radio from any song
- Quality: stream Low / Normal / High / Max, Hi-Res badges for local lossless (24-bit / 88.2 kHz+), selectable 44.1–192 kHz audio engine rate
- Equalizer (press `E`): **Basic** (bass / mid / treble + presets) and **Advanced** (preamp, 10-band, bass enhancer, stereo width, compressor / limiter), auto headroom, save your own presets
- Downloads: original quality or MP3 320/192, tagged, added to your library automatically
- Now-playing view with live visualizer, media keys, accent colours

Shortcuts: `Space` play/pause · `←/→` seek · `Shift+←/→` prev/next · `↑/↓` volume · `/` search · `E` equalizer · `Q` queue · `L` like · `M` mute

## Things to know

- Data lives in `~/.aura` (set `AURA_HOME` to change). Downloads go to `~/Music/Aura` by default.
- The equalizer runs in the web audio engine. The OS still decides the final output rate and there's no exclusive/bit-perfect mode in a web view.
- Downloading from YouTube may breach its Terms of Service in your country; use it for content you're entitled to.


## Make an executable

- **Windows:** double-click `build_windows.bat` → `dist\Aura.exe`
- **macOS / Linux:** run `./build_mac_linux.sh` → `dist/`

PyInstaller builds only for the OS it runs on. Put `ffmpeg` on your PATH if you want MP3 conversion in the built app.

## "Sign in to confirm you're not a bot"

YouTube sometimes blocks anonymous streams. Aura retries with other player types automatically. If it still fails: Settings > YouTube access > pick the browser you're signed in to YouTube with (close that browser first). Also run `pip install -U yt-dlp`.
