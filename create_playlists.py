"""
YouTube Music Playlist Creator — Aftershock 2026

SETUP (one-time):
    pip install -r requirements.txt
    python -c "from ytmusicapi import setup_oauth; setup_oauth(filepath='oauth.json')"

    This opens a browser URL. Log in with your Google account and the token is
    saved to oauth.json. Do NOT commit oauth.json to version control.

USAGE:
    python create_playlists.py              # create both playlists
    python create_playlists.py --dry-run    # preview without creating anything
    python create_playlists.py --verbose    # show debug-level logging
    python create_playlists.py --oauth-file path/to/oauth.json
"""

import argparse
import logging
import os
import sys
import time

from ytmusicapi import YTMusic

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
# Authentication
# ---------------------------------------------------------------------------

def get_authenticated_client(oauth_file: str = "oauth.json") -> YTMusic:
    if not os.path.exists(oauth_file):
        sys.exit(
            f"ERROR: OAuth credentials not found at '{oauth_file}'.\n\n"
            "Run the one-time setup:\n"
            "  python -c \"from ytmusicapi import setup_oauth; "
            "setup_oauth(filepath='oauth.json')\"\n\n"
            "Then re-run this script."
        )
    return YTMusic(oauth_file)

# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def search_song(ytm: YTMusic, artist: str, title: str) -> str | None:
    query = f"{artist} {title}"
    logging.debug("Searching: %s", query)
    try:
        results = ytm.search(query, filter="songs", limit=5)
    except Exception as exc:
        logging.warning("Search error for '%s': %s", query, exc)
        return None

    if not results:
        logging.warning("Not found: %s — %s", artist, title)
        return None

    video_id = results[0].get("videoId")
    if not video_id:
        logging.warning("No videoId in result for: %s — %s", artist, title)
        return None

    logging.debug("Found: %s (videoId=%s)", results[0].get("title", "?"), video_id)
    return video_id


def create_playlist(ytm: YTMusic, name: str, description: str, dry_run: bool = False) -> str | None:
    if dry_run:
        logging.info("[DRY RUN] Would create playlist: %s", name)
        return "DRY_RUN_PLAYLIST_ID"
    try:
        playlist_id = ytm.create_playlist(name, description)
        logging.info("Created playlist '%s' (id=%s)", name, playlist_id)
        return playlist_id
    except Exception as exc:
        logging.error("Failed to create playlist '%s': %s", name, exc)
        return None


def add_songs_to_playlist(
    ytm: YTMusic, playlist_id: str, video_ids: list[str], dry_run: bool = False
) -> bool:
    if not video_ids:
        return True
    if dry_run:
        logging.info("[DRY RUN] Would add %d songs to playlist %s", len(video_ids), playlist_id)
        return True
    try:
        ytm.add_playlist_items(playlist_id, video_ids)
        logging.info("Added %d songs to playlist %s", len(video_ids), playlist_id)
        return True
    except Exception as exc:
        logging.error("Failed to add songs to playlist %s: %s", playlist_id, exc)
        return False

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_playlist(
    ytm: YTMusic, playlist_def: dict, dry_run: bool = False
) -> dict:
    name = playlist_def["name"]
    description = playlist_def["description"]
    songs = playlist_def["songs"]

    logging.info("--- Building playlist: %s (%d songs) ---", name, len(songs))

    playlist_id = create_playlist(ytm, name, description, dry_run)
    if playlist_id is None:
        return {"name": name, "playlist_id": None, "added": 0, "skipped": songs}

    video_ids = []
    skipped = []

    for song in songs:
        artist = song["artist"]
        title = song["title"]
        video_id = search_song(ytm, artist, title)
        if video_id:
            video_ids.append(video_id)
        else:
            skipped.append(song)
        time.sleep(0.2)  # gentle rate limiting

    add_songs_to_playlist(ytm, playlist_id, video_ids, dry_run)

    return {
        "name": name,
        "playlist_id": playlist_id,
        "added": len(video_ids),
        "skipped": skipped,
    }


def print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 50)
    print("Playlist Creation Summary")
    print("=" * 50)
    for r in results:
        print(f"\n{r['name']}")
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
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    ytm = get_authenticated_client(args.oauth_file)

    results = []
    for playlist_def in PLAYLISTS:
        result = build_playlist(ytm, playlist_def, dry_run=args.dry_run)
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
