import json
import os
from pathlib import Path
from typing import Dict, List, Set

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
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def load_state() -> Dict[str, List[str]]:
    if not STATE_FILE.exists():
        return {"processed_episode_ids": []}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: Dict[str, List[str]]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_podcasts() -> List[Dict[str, str]]:
    if not PODCASTS_FILE.exists():
        raise FileNotFoundError("podcasts.json not found")

    with open(PODCASTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    shows = data.get("shows", [])
    if not shows:
        raise ValueError("No shows found in podcasts.json")

    return shows


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


def get_latest_episodes(sp: spotipy.Spotify, show_id: str, limit: int = 10) -> List[Dict]:
    results = sp.show_episodes(show_id, limit=limit, market="BR")
    return results.get("items", [])


def add_episodes_to_playlist(sp: spotipy.Spotify, playlist_id: str, episode_uris: List[str]) -> None:
    if not episode_uris:
        return

    # Spotify accepts up to 100 items per request
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

        print(f"Checking show: {show_name}")

        episodes = get_latest_episodes(sp, show_id, limit=10)

        for episode in episodes:
            episode_id = episode["id"]
            episode_uri = episode["uri"]
            episode_name = episode["name"]
            release_date = episode.get("release_date", "unknown")

            if episode_id not in processed_ids:
                print(f"  New episode found: {episode_name} ({release_date})")
                new_episode_uris.append(episode_uri)
                newly_processed_ids.add(episode_id)

    if new_episode_uris:
        add_episodes_to_playlist(sp, PLAYLIST_ID, new_episode_uris)
        print(f"Added {len(new_episode_uris)} new episode(s) to playlist.")
    else:
        print("No new episodes found.")

    processed_ids.update(newly_processed_ids)
    save_state({"processed_episode_ids": sorted(processed_ids)})


if __name__ == "__main__":
    main()