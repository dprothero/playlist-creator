# Aftershock 2026 — YouTube Music Playlist Creator

Creates YouTube Music playlists for Aftershock 2026 using the YouTube Data API v3.

Two playlists are generated:
- **Priority Acts** — melodic metalcore, melodic death metal, and the heavier side of the lineup
- **Worth Checking Out** — broader picks across different flavors of heavy

See [aftershock-2026-playlists.md](aftershock-2026-playlists.md) for the full song list with descriptions.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for Python environment management
- [1Password CLI](https://developer.1password.com/docs/cli/) (optional, for credential management)
- A Google Cloud project with **YouTube Data API v3** enabled
- OAuth 2.0 credentials (TV and Limited Input devices type)

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure OAuth credentials

Store your Google OAuth client ID and secret. You can either:

**Option A: Use 1Password** (recommended)

Store credentials in 1Password and load them with:
```bash
eval "$(./env.sh)"
```

**Option B: Export manually**
```bash
export YTM_CLIENT_ID='your-client-id'
export YTM_CLIENT_SECRET='your-client-secret'
```

### 3. Authenticate with Google

```bash
./setup-auth.sh
```

This starts a device OAuth flow — follow the URL, log in with your Google account, and press Enter. Your token is saved to `oauth.json`.

## Usage

```bash
# Preview what would happen (no API writes)
uv run python create_playlists.py --dry-run

# Create the playlists
uv run python create_playlists.py

# Verbose output for debugging
uv run python create_playlists.py --verbose

# Clear all progress and cache, start fresh
uv run python create_playlists.py --reset
```

## Resuming after quota limits

The YouTube Data API v3 has a daily quota (search costs 100 units each). If you hit the limit, just re-run the script after the quota resets (midnight Pacific time). The script automatically:

- **Caches search results** in `search_cache.json` so found songs are never searched again
- **Tracks progress** in `progress.json` — knows which playlists were created and which songs were added
- **Skips completed playlists** entirely on subsequent runs

## Files

| File | Description |
|---|---|
| `create_playlists.py` | Main script |
| `setup-auth.sh` | One-time OAuth setup |
| `env.sh` | Loads credentials from 1Password |
| `oauth.json` | OAuth token (gitignored) |
| `search_cache.json` | Cached search results (gitignored) |
| `progress.json` | Playlist creation progress (gitignored) |
