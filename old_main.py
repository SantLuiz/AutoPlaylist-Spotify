import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

STATE_FILE = Path("state.json")
PODCASTS_FILE = Path("podcasts.json")

SCOPES = [
    "playlist-modify-private",
    "playlist-modify-public",
]

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
PLAYLIST_ID = os.getenv("PLAYLIST_ID")


def validate_env() -> None:
    missing = []

    for key, value in {
        "SPOTIPY_CLIENT_ID": CLIENT_ID,
        "SPOTIPY_CLIENT_SECRET": CLIENT_SECRET,
        "SPOTIPY_REDIRECT_URI": REDIRECT_URI,
        "PLAYLIST_ID": PLAYLIST_ID,
    }.items():
        if not value:
            missing.append(key)

    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}"
        )


def load_state() -> Dict[str, List[str]]:
    if not STATE_FILE.exists():
        return {"processed_episode_ids": []}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print("Warning: state.json is not a valid object. Resetting state.")
            return {"processed_episode_ids": []}

        processed_ids = data.get("processed_episode_ids", [])

        if not isinstance(processed_ids, list):
            print("Warning: processed_episode_ids is invalid. Resetting state.")
            return {"processed_episode_ids": []}

        return {"processed_episode_ids": processed_ids}

    except json.JSONDecodeError:
        print("Warning: state.json is corrupted. Resetting state.")
        return {"processed_episode_ids": []}


def save_state(state: Dict[str, List[str]]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_podcasts() -> List[Dict[str, str]]:
    if not PODCASTS_FILE.exists():
        raise FileNotFoundError("podcasts.json not found")

    with open(PODCASTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    shows = data.get("shows", [])
    if not isinstance(shows, list) or not shows:
        raise ValueError("No valid shows found in podcasts.json")

    valid_shows = []
    for show in shows:
        if not isinstance(show, dict):
            print(f"Skipping invalid show entry: {show}")
            continue

        name = show.get("name")
        show_id = show.get("show_id")

        if not name or not show_id:
            print(f"Skipping show with missing fields: {show}")
            continue

        valid_shows.append({
            "name": name,
            "show_id": show_id
        })

    if not valid_shows:
        raise ValueError("No usable shows found in podcasts.json")

    return valid_shows


def create_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        open_browser=True,
        cache_path=".spotify_cache",
        show_dialog=True,
    )

    return spotipy.Spotify(auth_manager=auth_manager)


def get_latest_episodes(
    sp: spotipy.Spotify,
    show_id: str,
    limit: int = 10
) -> List[Any]:
    results = sp.show_episodes(show_id, limit=limit, market="BR")
    items = results.get("items", [])

    if not isinstance(items, list):
        print(f"Warning: Unexpected response for show_id={show_id}")
        return []

    return items


def add_episodes_to_playlist(
    sp: spotipy.Spotify,
    playlist_id: str,
    episode_uris: List[str]
) -> None:
    if not episode_uris:
        return

    chunk_size = 100
    for i in range(0, len(episode_uris), chunk_size):
        chunk = episode_uris[i:i + chunk_size]
        sp.playlist_add_items(playlist_id, chunk)


def main() -> None:
    validate_env()

    sp = create_spotify_client()
    state = load_state()
    processed_ids: Set[str] = set(state.get("processed_episode_ids", []))
    shows = load_podcasts()

    new_episode_uris: List[str] = []
    newly_processed_ids: Set[str] = set()

    for show in shows:
        show_name = show["name"]
        show_id = show["show_id"]

        print(f"\nChecking show: {show_name}")

        episodes = get_latest_episodes(sp, show_id, limit=10)

        if not episodes:
            print("  No episodes returned.")
            continue

        for index, episode in enumerate(episodes):
            if not episode:
                print(f"  Skipping empty episode entry at index {index}.")
                continue

            if not isinstance(episode, dict):
                print(f"  Skipping non-dict episode at index {index}: {episode}")
                continue

            episode_id = episode.get("id")
            episode_uri = episode.get("uri")
            episode_name = episode.get("name", "Unknown episode")
            release_date = episode.get("release_date", "unknown")

            if not episode_id or not episode_uri:
                print(f"  Skipping invalid episode at index {index}: {episode}")
                continue

            if episode_id not in processed_ids:
                print(f"  New episode found: {episode_name} ({release_date})")
                new_episode_uris.append(episode_uri)
                newly_processed_ids.add(episode_id)
            else:
                print(f"  Already processed: {episode_name} ({release_date})")

    if new_episode_uris:
        add_episodes_to_playlist(sp, PLAYLIST_ID, new_episode_uris)
        print(f"\nAdded {len(new_episode_uris)} new episode(s) to playlist.")
    else:
        print("\nNo new episodes found.")

    processed_ids.update(newly_processed_ids)
    save_state({"processed_episode_ids": sorted(processed_ids)})


if __name__ == "__main__":
    main()