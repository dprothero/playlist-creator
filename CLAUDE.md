# Project Context

YouTube Music playlist creator for Aftershock 2026. Uses the official YouTube Data API v3 with OAuth2 (device flow) via raw `requests` — not the `ytmusicapi` library (its internal API rejects OAuth tokens).

## Architecture

Single-file script (`create_playlists.py`) with no framework. Playlist definitions are hardcoded in `PLAYLISTS`. The script uses two JSON sidecar files for state:

- `search_cache.json` — maps `"artist — title"` to `videoId` (or null if not found). Avoids repeat API searches.
- `progress.json` — tracks created playlist IDs and which songs have been added. Enables resume after quota exhaustion.

Both files are saved incrementally after each API call.

## Key decisions

- **Raw `requests` over `ytmusicapi`**: The `ytmusicapi` library uses YouTube Music's unofficial internal API (`youtubei/v1`), which returns HTTP 400 when OAuth Bearer tokens are sent. The official YouTube Data API v3 works correctly with OAuth.
- **Separate search and write auth**: Search doesn't strictly require auth but we use it anyway since we're on the official API now.
- **Quota-aware design**: YouTube Data API v3 has a 10,000 unit/day quota. Searches cost 100 units each. The script exits gracefully on 403 and saves progress.

## Running

```bash
eval "$(./env.sh)"        # load credentials from 1Password
./setup-auth.sh           # one-time OAuth device flow -> oauth.json
uv run python create_playlists.py --dry-run   # preview
uv run python create_playlists.py             # create playlists
uv run python create_playlists.py --reset     # clear cache + progress
```

## Environment

- Python managed with `uv`
- OAuth credentials via 1Password CLI or `YTM_CLIENT_ID` / `YTM_CLIENT_SECRET` env vars
- Google Cloud project needs YouTube Data API v3 enabled
- OAuth client type: TVs and Limited Input devices
