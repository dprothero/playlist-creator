"""
YouTube Music Playlist Creator — Aftershock 2026

Uses the official YouTube Data API v3 with OAuth2 credentials.

SETUP (one-time):
    ./setup-auth.sh

USAGE:
    python create_playlists.py              # create both playlists
    python create_playlists.py --dry-run    # preview without creating anything
    python create_playlists.py --verbose    # show debug-level logging
    python create_playlists.py --oauth-file path/to/oauth.json

State is saved to progress.json after each step so the script can resume
where it left off if interrupted (e.g. by quota limits). Search results are
cached in search_cache.json to avoid burning quota on repeated runs.
"""

import argparse
import json
import logging
import os
import sys
import time

import requests

API_BASE = "https://www.googleapis.com/youtube/v3"
SEARCH_CACHE_FILE = "search_cache.json"
PROGRESS_FILE = "progress.json"

# ---------------------------------------------------------------------------
# Playlist data
# ---------------------------------------------------------------------------

PLAYLISTS = [
    {
        "name": "Aftershock 2026 — Priority Acts",
        "description": (
            "Priority acts from Aftershock 2026: melodic metalcore, melodic death metal, "
            "and the heavier side of the lineup."
        ),
        "songs": [
            # Killswitch Engage
            {"artist": "Killswitch Engage", "title": "The End of Heartache"},
            {"artist": "Killswitch Engage", "title": "My Curse"},
            {"artist": "Killswitch Engage", "title": "Rose of Sharyn"},
            {"artist": "Killswitch Engage", "title": "In Due Time"},
            # The Black Dahlia Murder
            {"artist": "The Black Dahlia Murder", "title": "Funeral Thirst"},
            {"artist": "The Black Dahlia Murder", "title": "What a Horrible Night to Have a Curse"},
            {"artist": "The Black Dahlia Murder", "title": "Nightbringers"},
            {"artist": "The Black Dahlia Murder", "title": "Verminous"},
            # Blue Medusa / Alissa White-Gluz / Arch Enemy — per-song artist
            {"artist": "Blue Medusa", "title": "Checkmate"},
            {"artist": "Alissa White-Gluz", "title": "The Room Where She Died"},
            {"artist": "Arch Enemy", "title": "War Eternal"},
            {"artist": "Arch Enemy", "title": "The Eagle Flies Alone"},
            # After The Burial
            {"artist": "After The Burial", "title": "A Wolf Amongst Ravens"},
            {"artist": "After The Burial", "title": "Behold the Crown"},
            {"artist": "After The Burial", "title": "Lost in the Static"},
            {"artist": "After The Burial", "title": "Collapse"},
            # The Devil Wears Prada
            {"artist": "The Devil Wears Prada", "title": "Danger: Wildman"},
            {"artist": "The Devil Wears Prada", "title": "Chemical"},
            {"artist": "The Devil Wears Prada", "title": "Sacrifice"},
            {"artist": "The Devil Wears Prada", "title": "Watchtower"},
            # Wage War
            {"artist": "Wage War", "title": "Stitch"},
            {"artist": "Wage War", "title": "Low"},
            {"artist": "Wage War", "title": "Manic"},
            {"artist": "Wage War", "title": "Grave"},
            # The Ghost Inside
            {"artist": "The Ghost Inside", "title": "Aftermath"},
            {"artist": "The Ghost Inside", "title": "Engine 45"},
            {"artist": "The Ghost Inside", "title": "Avalanche"},
            {"artist": "The Ghost Inside", "title": "Move Me"},
            # Counterparts
            {"artist": "Counterparts", "title": "The Disconnect"},
            {"artist": "Counterparts", "title": "Paradise and Plague"},
            {"artist": "Counterparts", "title": "Wings of Nightmares"},
            {"artist": "Counterparts", "title": "Bound to the Burn"},
        ],
    },
    {
        "name": "Aftershock 2026 — Worth Checking Out",
        "description": (
            "Broader picks from Aftershock 2026 — different flavors of heavy "
            "that could land depending on mood."
        ),
        "songs": [
            # Cavalera (performing Sepultura's Roots)
            {"artist": "Cavalera", "title": "Roots Bloody Roots"},
            {"artist": "Cavalera", "title": "Attitude"},
            {"artist": "Cavalera", "title": "Ratamahatta"},
            {"artist": "Cavalera", "title": "Cut-Throat"},
            # Tool
            {"artist": "Tool", "title": "Schism"},
            {"artist": "Tool", "title": "Forty Six & 2"},
            {"artist": "Tool", "title": "Lateralus"},
            {"artist": "Tool", "title": "Fear Inoculum"},
            # Slaughter To Prevail
            {"artist": "Slaughter To Prevail", "title": "Bonebreaker"},
            {"artist": "Slaughter To Prevail", "title": "Demolisher"},
            {"artist": "Slaughter To Prevail", "title": "Viking"},
            {"artist": "Slaughter To Prevail", "title": "Agony"},
            # Rivers of Nihil
            {"artist": "Rivers of Nihil", "title": "Where Owls Know My Name"},
            {"artist": "Rivers of Nihil", "title": "The Silent Life"},
            {"artist": "Rivers of Nihil", "title": "Clean"},
            {"artist": "Rivers of Nihil", "title": "Focus"},
            # Alexisonfire
            {"artist": "Alexisonfire", "title": "This Could Be Anywhere in the World"},
            {"artist": "Alexisonfire", "title": "Pulmonary Archery"},
            {"artist": "Alexisonfire", "title": "Young Cardinals"},
            {"artist": "Alexisonfire", "title": "Boiled Frogs"},
            # Underoath
            {"artist": "Underoath", "title": "Writing on the Walls"},
            {"artist": "Underoath", "title": "It's Dangerous Business Walking Out Your Front Door"},
            {"artist": "Underoath", "title": "A Boy Brushed Red Living in Black and White"},
            {"artist": "Underoath", "title": "Reinventing Your Exit"},
            # Atreyu
            {"artist": "Atreyu", "title": "Lip Gloss and Black"},
            {"artist": "Atreyu", "title": "The Crimson"},
            {"artist": "Atreyu", "title": "Ex's and Oh's"},
            {"artist": "Atreyu", "title": "Right Side of the Bed"},
            # Cradle of Filth
            {"artist": "Cradle of Filth", "title": "Her Ghost in the Fog"},
            {"artist": "Cradle of Filth", "title": "Nymphetamine Fix"},
            {"artist": "Cradle of Filth", "title": "From the Cradle to Enslave"},
            {"artist": "Cradle of Filth", "title": "Heartbreak and Seance"},
            # DOWN
            {"artist": "DOWN", "title": "Stone the Crow"},
            {"artist": "DOWN", "title": "Lifer"},
            {"artist": "DOWN", "title": "Bury Me in Smoke"},
            {"artist": "DOWN", "title": "Ghosts Along the Mississippi"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Search cache
# ---------------------------------------------------------------------------

def load_search_cache() -> dict[str, str | None]:
    if os.path.exists(SEARCH_CACHE_FILE):
        with open(SEARCH_CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_search_cache(cache: dict[str, str | None]) -> None:
    with open(SEARCH_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def cache_key(artist: str, title: str) -> str:
    return f"{artist} — {title}"

# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def load_progress() -> dict:
    """Load progress state.

    Structure:
    {
        "playlists": {
            "<playlist_name>": {
                "playlist_id": "...",
                "added_songs": ["artist — title", ...]
            }
        }
    }
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"playlists": {}}


def save_progress(progress: dict) -> None:
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

# ---------------------------------------------------------------------------
# OAuth token management
# ---------------------------------------------------------------------------

def load_token(oauth_file: str, client_id: str, client_secret: str) -> str:
    """Load access token from oauth.json, refreshing if expired."""
    if not os.path.exists(oauth_file):
        sys.exit(
            f"ERROR: OAuth credentials not found at '{oauth_file}'.\n"
            "Run ./setup-auth.sh first."
        )

    with open(oauth_file) as f:
        token_data = json.load(f)

    # Refresh if expired or expiring within 60s
    if token_data.get("expires_at", 0) - time.time() < 60:
        logging.info("Access token expired, refreshing...")
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        fresh = resp.json()
        token_data["access_token"] = fresh["access_token"]
        token_data["expires_at"] = int(time.time()) + fresh["expires_in"]
        token_data["expires_in"] = fresh["expires_in"]
        with open(oauth_file, "w") as f:
            json.dump(token_data, f, indent=True)
        logging.info("Token refreshed successfully.")

    return token_data["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

# ---------------------------------------------------------------------------
# YouTube Data API v3 operations
# ---------------------------------------------------------------------------

def search_song(access_token: str, artist: str, title: str, search_cache: dict) -> str | None:
    key = cache_key(artist, title)
    if key in search_cache:
        video_id = search_cache[key]
        if video_id:
            logging.debug("Cache hit: %s -> %s", key, video_id)
        else:
            logging.debug("Cache hit (not found): %s", key)
        return video_id

    query = f"{artist} {title}"
    logging.debug("Searching: %s", query)
    resp = requests.get(f"{API_BASE}/search", params={
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",  # Music
        "maxResults": 5,
    }, headers=auth_headers(access_token))

    if resp.status_code == 403:
        logging.error("Quota exceeded during search for '%s'. Re-run later to resume.", query)
        save_search_cache(search_cache)
        sys.exit(2)

    if resp.status_code != 200:
        logging.warning("Search error for '%s': %s %s", query, resp.status_code, resp.text[:200])
        return None

    items = resp.json().get("items", [])
    if not items:
        logging.warning("Not found: %s — %s", artist, title)
        search_cache[key] = None
        save_search_cache(search_cache)
        return None

    video_id = items[0]["id"]["videoId"]
    logging.debug("Found: %s (videoId=%s)", items[0]["snippet"]["title"], video_id)
    search_cache[key] = video_id
    save_search_cache(search_cache)
    return video_id


def create_playlist(access_token: str, name: str, description: str, dry_run: bool = False) -> str | None:
    if dry_run:
        logging.info("[DRY RUN] Would create playlist: %s", name)
        return "DRY_RUN_PLAYLIST_ID"

    resp = requests.post(f"{API_BASE}/playlists", params={"part": "snippet,status"}, json={
        "snippet": {"title": name, "description": description},
        "status": {"privacyStatus": "private"},
    }, headers=auth_headers(access_token))

    if resp.status_code == 403:
        logging.error("Quota exceeded creating playlist '%s'. Re-run later to resume.", name)
        sys.exit(2)

    if resp.status_code != 200:
        logging.error("Failed to create playlist '%s': %s %s", name, resp.status_code, resp.text[:300])
        return None

    playlist_id = resp.json()["id"]
    logging.info("Created playlist '%s' (id=%s)", name, playlist_id)
    return playlist_id


def add_song_to_playlist(access_token: str, playlist_id: str, video_id: str) -> bool:
    resp = requests.post(f"{API_BASE}/playlistItems", params={"part": "snippet"}, json={
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        },
    }, headers=auth_headers(access_token))

    if resp.status_code == 403:
        logging.error("Quota exceeded adding video %s. Re-run later to resume.", video_id)
        return False

    if resp.status_code != 200:
        logging.warning("Failed to add video %s to playlist %s: %s", video_id, playlist_id, resp.text[:200])
        return False
    return True

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_playlist(
    access_token: str,
    playlist_def: dict,
    search_cache: dict,
    progress: dict,
    dry_run: bool = False,
) -> dict:
    name = playlist_def["name"]
    description = playlist_def["description"]
    songs = playlist_def["songs"]
    pl_progress = progress["playlists"].get(name, {})

    # Skip fully completed playlists
    if pl_progress.get("complete"):
        logging.info("--- Skipping completed playlist: %s ---", name)
        return {
            "name": name,
            "playlist_id": pl_progress.get("playlist_id"),
            "added": len(pl_progress.get("added_songs", [])),
            "skipped": [],
            "status": "already complete",
        }

    logging.info("--- Building playlist: %s (%d songs) ---", name, len(songs))

    # Resume: reuse existing playlist_id if we already created it
    playlist_id = pl_progress.get("playlist_id")
    if playlist_id:
        logging.info("Resuming playlist '%s' (id=%s)", name, playlist_id)
    else:
        playlist_id = create_playlist(access_token, name, description, dry_run)
        if playlist_id is None:
            return {"name": name, "playlist_id": None, "added": 0, "skipped": songs}
        pl_progress["playlist_id"] = playlist_id
        pl_progress.setdefault("added_songs", [])
        progress["playlists"][name] = pl_progress
        save_progress(progress)

    added_songs = set(pl_progress.get("added_songs", []))
    added_count = len(added_songs)
    skipped = []
    quota_hit = False

    for song in songs:
        artist = song["artist"]
        title = song["title"]
        song_key = cache_key(artist, title)

        # Skip songs already added to this playlist
        if song_key in added_songs:
            logging.debug("Already added: %s", song_key)
            continue

        video_id = search_song(access_token, artist, title, search_cache)
        if video_id:
            if dry_run:
                added_count += 1
            else:
                if add_song_to_playlist(access_token, playlist_id, video_id):
                    added_count += 1
                    pl_progress.setdefault("added_songs", []).append(song_key)
                    save_progress(progress)
                else:
                    # Likely quota exceeded — stop and save
                    logging.warning("Stopping playlist '%s' — will resume on next run.", name)
                    quota_hit = True
                    break
        else:
            skipped.append(song)
        time.sleep(0.2)  # gentle rate limiting

    if not quota_hit and not dry_run:
        pl_progress["complete"] = True
        save_progress(progress)

    if dry_run:
        logging.info("[DRY RUN] Would add %d songs to playlist %s", added_count, playlist_id)

    return {
        "name": name,
        "playlist_id": playlist_id,
        "added": added_count,
        "skipped": skipped,
    }


def print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 50)
    print("Playlist Creation Summary")
    print("=" * 50)
    for r in results:
        print(f"\n{r['name']}")
        if r.get("status"):
            print(f"  STATUS  : {r['status']}")
        if r["playlist_id"] is None:
            print("  STATUS  : FAILED (playlist not created)")
        else:
            print(f"  ID      : {r['playlist_id']}")
        total = r["added"] + len(r["skipped"])
        print(f"  Added   : {r['added']} / {total}")
        if r["skipped"]:
            print(f"  Skipped : {len(r['skipped'])}")
            for s in r["skipped"]:
                print(f"    - {s['artist']}: {s['title']}")
        else:
            print("  Skipped : 0")
    print()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Aftershock 2026 playlists on YouTube Music."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without creating any playlists.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--oauth-file",
        default="oauth.json",
        metavar="FILE",
        help="Path to OAuth credentials file (default: oauth.json).",
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("YTM_CLIENT_ID"),
        help="OAuth client ID (or set YTM_CLIENT_ID env var).",
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("YTM_CLIENT_SECRET"),
        help="OAuth client secret (or set YTM_CLIENT_SECRET env var).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear progress and search cache, start fresh.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.reset:
        for f in [PROGRESS_FILE, SEARCH_CACHE_FILE]:
            if os.path.exists(f):
                os.remove(f)
                logging.info("Removed %s", f)

    if not args.client_id or not args.client_secret:
        sys.exit(
            "ERROR: client_id and client_secret are required.\n"
            "Set YTM_CLIENT_ID and YTM_CLIENT_SECRET env vars, or pass --client-id and --client-secret."
        )

    access_token = load_token(args.oauth_file, args.client_id, args.client_secret)
    search_cache = load_search_cache()
    progress = load_progress()

    results = []
    for playlist_def in PLAYLISTS:
        result = build_playlist(access_token, playlist_def, search_cache, progress, dry_run=args.dry_run)
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
