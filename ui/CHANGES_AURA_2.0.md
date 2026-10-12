# Aura update notes

## Playback
- Added configurable seek/skip interval (5, 10, 15, 20, 30, 45 or 60 seconds) in Settings > Playback.
- The player now shows skip-back/skip-forward controls, and Left/Right use the selected interval. Shift+Left/Right remain previous/next track.
- Added best-effort pre-resolution and media preloading for the next queued item so the next track does less work after the button is pressed.

## Search and catalog
- Added persistent search history with a Clear history control.
- Added local genre-tag syntax: `tag:rock` or `genre:jazz`.
- Added result sort controls for best match, most recent (when the provider returns release metadata), and most popular (when the provider exposes popularity/view data).
- Added search by YouTube Music playlists and artist/channel results. Those catalog objects open in YouTube Music.
- Added the public iTunes Search API to song search.
- Added MusicBrainz recording search under **All music catalogs**. Its results are metadata records and are matched to YouTube Music for playback; matches can vary.
- **All music catalogs** also broadens YouTube Music results with video results to help find tracks that are missed by song-only search.

## Home and appearance
- Added carousel previous/next buttons to music shelves.
- Added Continue session, Recommended by genre, Today's hits for your taste, and New releases shelves where data is available.
- Changed Aura's logo accent to neon orange with a subtle cyber glow.
- Added a Personalization page for card size, rounded artwork and shelf spacing.

## Provider limitations
- Free catalog APIs have their own availability, rate limits, and regional/catalog gaps. The iTunes and MusicBrainz APIs supply catalog metadata, not unrestricted full-length audio. Aura attempts to match these results through YouTube Music for playback.
- Popularity sorting works only where a provider supplies a popularity/view metric. Most recent sorting works only where release-date metadata exists.
- Preloading is best-effort: network conditions, YouTube access checks and provider response times can still affect transitions.


## Multi-provider discovery and streaming
- Search now queries YouTube Music, Audius, iTunes, and Spotify metadata in parallel; Jamendo is enabled by a free client ID in Settings. MusicBrainz and YouTube video fallback remain available under All music catalogs.
- Added source-native Audius and Jamendo streaming. Spotify/iTunes/MusicBrainz results remain metadata/catalog results and resolve separately for playback; no catalog-only API is mislabeled as a full-track stream.
- Added provider-based Home tabs: For you, Hot topics, Genres, New releases, and Continue session. YouTube Music recommendations use YouTube Music radio/charts where available; Audius recommendations/trending use Audius's own API; Spotify recommendations remain Spotify catalog-derived.
- Added native downloads for Audius/Jamendo tracks only when the API reports downloads are permitted by the creator. Permission flags are parsed conservatively, and the existing download menu remains for other online results.
- Proxied Audius/Jamendo streams through Aura’s local origin so browser audio analysis and seeking are less dependent on upstream CORS headers.
- Added the asynchronous “Today’s hits for your taste” shelf, selecting discovery from the seed track’s provider where supported (YouTube Music, Audius, Jamendo, Spotify catalog, or Apple catalog).

## Mini-player and personalization
- Added a toggleable floating mini-player with a translucent glass effect, live audio spectrum, current song, previous/next track names, and previous/pause/play/next controls.
- Added mini-player tint, opacity, width and height controls under Personalization.


### Floating desktop player refinement
- Added a dedicated button to collapse the full Aura interface into a separate-size native floating window while retaining the same WebView/audio context.
- Floating window stays above other windows, can be dragged by the bar background, snaps to the nearest display edge on release, and restores the previous app-window size/position using the expand button.
- Added separate floating width/height preferences and moved the spectrum visualizer to a narrow strip along the top of the player.
- Native floating mode requires `python main.py`; browser mode retains the in-page mini-player only.
