import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

STATE_FILE = Path("state.json")
PODCASTS_FILE = Path("podcasts.json")
MAX_EPISODE_AGE_DAYS = 14
SHOW_EPISODE_FETCH_LIMIT = 20

SCOPES = [
    "playlist-read-private",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-playback-position",
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

        valid_shows.append({"name": name, "show_id": show_id})

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


def parse_release_date(value: str, precision: str = "day") -> Optional[date]:
    if not value:
        return None

    formats = {
        "day": "%Y-%m-%d",
        "month": "%Y-%m",
        "year": "%Y",
    }

    fmt = formats.get(precision)
    if not fmt:
        return None

    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def is_recent_episode(release_date: Optional[date], max_age_days: int = MAX_EPISODE_AGE_DAYS) -> bool:
    if release_date is None:
        return False
    return release_date >= (date.today() - timedelta(days=max_age_days))


def is_episode_fully_played(episode: Dict[str, Any]) -> bool:
    resume_point = episode.get("resume_point") or {}
    return bool(resume_point.get("fully_played", False))


def get_latest_episodes(sp: spotipy.Spotify, show_id: str, limit: int = SHOW_EPISODE_FETCH_LIMIT) -> List[Dict[str, Any]]:
    results = sp.show_episodes(show_id, limit=limit, market="BR")
    items = results.get("items", [])

    if not isinstance(items, list):
        print(f"Warning: Unexpected response for show_id={show_id}")
        return []

    valid_items: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            valid_items.append(item)
    return valid_items


def get_playlist_episode_items(sp: spotipy.Spotify, playlist_id: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    offset = 0
    limit = 100

    while True:
        response = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            market="BR",
            additional_types=("track", "episode"),
        )
        page_items = response.get("items", [])
        if not isinstance(page_items, list):
            break

        items.extend(page_items)

        if len(page_items) < limit:
            break
        offset += limit

    return items


def extract_playlist_episode_ids_and_finished_uris(
    playlist_items: List[Dict[str, Any]],
) -> Tuple[Set[str], List[str]]:
    playlist_episode_ids: Set[str] = set()
    finished_episode_uris: List[str] = []

    for item in playlist_items:
        track = item.get("track") if isinstance(item, dict) else None
        if not isinstance(track, dict):
            continue

        if track.get("type") != "episode":
            continue

        episode_id = track.get("id")
        episode_uri = track.get("uri")

        if episode_id:
            playlist_episode_ids.add(episode_id)

        if episode_uri and is_episode_fully_played(track):
            finished_episode_uris.append(episode_uri)

    return playlist_episode_ids, finished_episode_uris


def remove_episodes_from_playlist(sp: spotipy.Spotify, playlist_id: str, episode_uris: List[str]) -> None:
    if not episode_uris:
        return

    unique_uris = list(dict.fromkeys(episode_uris))
    chunk_size = 100
    for i in range(0, len(unique_uris), chunk_size):
        chunk = unique_uris[i:i + chunk_size]
        sp.playlist_remove_all_occurrences_of_items(playlist_id, chunk)


def add_episodes_to_playlist(sp: spotipy.Spotify, playlist_id: str, episode_uris: List[str]) -> None:
    if not episode_uris:
        return

    chunk_size = 100
    for i in range(0, len(episode_uris), chunk_size):
        chunk = episode_uris[i:i + chunk_size]
        sp.playlist_add_items(playlist_id, chunk)


def choose_episode_to_add(
    episodes: List[Dict[str, Any]],
    playlist_episode_ids: Set[str],
) -> Optional[Dict[str, Any]]:
    sorted_episodes = sorted(
        episodes,
        key=lambda ep: parse_release_date(
            ep.get("release_date", ""),
            ep.get("release_date_precision", "day"),
        ) or date.min,
        reverse=True,
    )

    for episode in sorted_episodes:
        episode_id = episode.get("id")
        episode_uri = episode.get("uri")
        episode_name = episode.get("name", "Unknown episode")
        release_date_raw = episode.get("release_date", "unknown")
        release_precision = episode.get("release_date_precision", "day")
        release_date = parse_release_date(release_date_raw, release_precision)

        if not episode_id or not episode_uri:
            print(f"  Skipping invalid episode: {episode_name}")
            continue

        if not is_recent_episode(release_date):
            print(f"  Ignoring old episode: {episode_name} ({release_date_raw})")
            continue

        if is_episode_fully_played(episode):
            print(f"  Already finished: {episode_name} ({release_date_raw})")
            continue

        if episode_id in playlist_episode_ids:
            print(f"  Already in playlist: {episode_name} ({release_date_raw})")
            continue

        return episode

    return None


def main() -> None:
    validate_env()

    sp = create_spotify_client()
    state = load_state()
    processed_ids: Set[str] = set(state.get("processed_episode_ids", []))
    shows = load_podcasts()

    print("\nReading current playlist...")
    playlist_items = get_playlist_episode_items(sp, PLAYLIST_ID)
    playlist_episode_ids, finished_episode_uris = extract_playlist_episode_ids_and_finished_uris(playlist_items)

    if finished_episode_uris:
        print(f"Removing {len(set(finished_episode_uris))} finished episode(s) from playlist...")
        remove_episodes_from_playlist(sp, PLAYLIST_ID, finished_episode_uris)

        removed_ids = {
            uri.split(":")[-1]
            for uri in finished_episode_uris
            if uri.startswith("spotify:episode:")
        }
        playlist_episode_ids -= removed_ids
    else:
        print("No finished episodes to remove.")

    new_episode_uris: List[str] = []
    newly_processed_ids: Set[str] = set()

    for show in shows:
        show_name = show["name"]
        show_id = show["show_id"]

        print(f"\nChecking show: {show_name}")
        episodes = get_latest_episodes(sp, show_id)

        if not episodes:
            print("  No episodes returned.")
            continue

        selected_episode = choose_episode_to_add(episodes, playlist_episode_ids)

        if not selected_episode:
            print("  No eligible episode found for this show.")
            continue

        episode_id = selected_episode["id"]
        episode_uri = selected_episode["uri"]
        episode_name = selected_episode.get("name", "Unknown episode")
        release_date = selected_episode.get("release_date", "unknown")

        print(f"  Adding most recent unfinished episode: {episode_name} ({release_date})")
        new_episode_uris.append(episode_uri)
        newly_processed_ids.add(episode_id)
        playlist_episode_ids.add(episode_id)

    if new_episode_uris:
        add_episodes_to_playlist(sp, PLAYLIST_ID, new_episode_uris)
        print(f"\nAdded {len(new_episode_uris)} episode(s) to playlist.")
    else:
        print("\nNo episodes needed to be added.")

    processed_ids.update(newly_processed_ids)
    save_state({"processed_episode_ids": sorted(processed_ids)})


if __name__ == "__main__":
    main()
