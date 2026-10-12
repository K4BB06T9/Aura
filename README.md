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
2. If it finds fewer than 3 matches (or **Always search online too** is enabled), Aura searches YouTube Music, Audius, iTunes, and Jamendo (after you add its free client ID). Spotify catalog search is optional and needs developer credentials. **All music catalogs** also includes MusicBrainz recordings and YouTube video results.
3. Provider requests run in parallel to reduce search latency. Online results already present in your library are hidden. Use **Playlists** or **Artists / channels** to search YouTube Music collection results.

Catalog notes: Audius supports native streaming; Jamendo supports native streaming once configured. Some Jamendo downloads are disallowed by their creators and are disabled in Aura when the API reports that. iTunes, Apple charts, MusicBrainz, and Spotify results are catalog metadata, not unrestricted full-track streams; Aura resolves them to a playable source separately. Search coverage and API availability vary by provider and region.

## Features

- Library: MP3, FLAC, WAV, ALAC/AAC (m4a), OGG, OPUS, AIFF, WMA; tags + embedded artwork; rescans on launch
- Recommendations: provider-aware For you picks, today's hits based on listening history, Hot topics, Genres, New releases, Continue session, local genre mixes, and carousel controls on each shelf
- Playlists, liked songs, queue (play next / add / remove), shuffle, repeat, radio from any song
- Quality: stream Low / Normal / High / Max, Hi-Res badges for local lossless (24-bit / 88.2 kHz+), selectable 44.1–192 kHz audio engine rate
- Equalizer (press `E`): **Basic** (bass / mid / treble + presets) and **Advanced** (preamp, 10-band, bass enhancer, stereo width, compressor / limiter), auto headroom, save your own presets
- Downloads: original quality or MP3 320/192, tagged, added to your library automatically
- Now-playing view with live visualizer, media keys, configurable skip-back/skip-forward interval (5–60 seconds), next-track pre-resolution and best-effort media preloading, neon orange accents, customizable card size/shape/spacing, plus a configurable translucent mini-player with spectrum bars

Shortcuts: `Space` play/pause · `←/→` seek by your selected skip interval · `Shift+←/→` prev/next track · `↑/↓` volume · `/` search · `E` equalizer · `Q` queue · `L` like · `M` mute

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


## Multi-provider discovery, native streaming and mini-player

Aura supports source-specific online search and discovery for YouTube Music, Audius, Jamendo (after adding a free Jamendo client ID), iTunes/Apple catalog data, Spotify catalog metadata (optional credentials), and MusicBrainz recording metadata. Audius and Jamendo are handled as native stream providers; catalog APIs are clearly treated as metadata sources and may resolve playback through a separate provider. Audius read-only discovery is available without a token, though rate limits can apply.

### Music discovery

The Home page has tabs for **For you**, **Hot topics**, **Genres**, **New releases**, and **Continue session**. Hot-topic sections use provider-specific trending/chart data when available. Recommendations use source-native related-track paths where supported; Spotify and Apple catalog metadata should not be mistaken for full-track streaming APIs. Availability, freshness, permissions and ranking differ by provider and region.

### Downloads

Use the track context menu (⋯) and select Download. Audius/Jamendo direct downloads are offered only when the provider's result indicates the creator permits downloading. Other catalog entries use Aura's existing matching path and may not be exact.

### Neon mini-player

Click the mini-bar icon in the playback footer to toggle a translucent floating player with a live spectrum, current song, previous/next track labels, and previous/play-next controls. Its tint, opacity, width and height can be changed under **Personalization > Neon mini-player bar**.

### Jamendo configuration

Open **Settings > Open music catalogs**, then add a free Jamendo Client ID from https://devportal.jamendo.com/. Audius can be used with a blank token for public read-only search/streaming.


## Floating desktop mini-player (native app)

Run Aura with `python main.py` (not `python main.py --browser`) to use the desktop floating player. Click the small floating-window button in the playback bar, next to the in-app mini-player button. The main Aura interface collapses into a compact always-on-top window while keeping the same audio player running. Drag the bar background to move it; when released near a screen edge it snaps to that edge. Click the expand/return button to restore the full Aura window.

Set the floating bar width and height in **Personalization → Neon mini-player bar**. The app must use pywebview for native resizing, always-on-top, and edge docking; these functions are not available in browser mode.
