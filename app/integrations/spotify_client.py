from __future__ import annotations

from typing import Any, List

import spotipy

from app.config.constants import EPISODE_FETCH_LIMIT, SPOTIFY_MARKET


class SpotifyGateway:
    def __init__(self, client: spotipy.Spotify) -> None:
        self.client = client

    def get_show_episodes(
        self,
        show_id: str,
        limit: int = EPISODE_FETCH_LIMIT,
        offset: int = 0,
    ) -> List[dict[str, Any]]:
        response = self.client.show_episodes(
            show_id,
            limit=limit,
            offset=offset,
            market=SPOTIFY_MARKET,
        )
        items = response.get("items", [])
        return items if isinstance(items, list) else []

    def get_playlist_items(
        self,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict[str, Any]]:
        response = self.client.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            additional_types=("episode",),
        )
        items = response.get("items", [])
        return items if isinstance(items, list) else []

    def add_items_to_playlist(self, playlist_id: str, uris: list[str]) -> None:
        if not uris:
            return

        chunk_size = 100
        for start in range(0, len(uris), chunk_size):
            chunk = uris[start:start + chunk_size]
            self.client.playlist_add_items(playlist_id, chunk)

    def replace_playlist_items(self, playlist_id: str, uris: list[str]) -> None:
        if uris:
            first_chunk = uris[:100]
            self.client.playlist_replace_items(playlist_id, first_chunk)

            remaining = uris[100:]
            if remaining:
                self.add_items_to_playlist(playlist_id, remaining)
            return

        current_items = self.get_playlist_items(playlist_id)
        current_uris: list[str] = []

        for item in current_items:
            track = item.get("track", {})
            if not isinstance(track, dict):
                continue

            uri = track.get("uri")
            if isinstance(uri, str) and uri:
                current_uris.append(uri)

        if current_uris:
            self.remove_all_occurrences_from_playlist(playlist_id, current_uris)

    def remove_all_occurrences_from_playlist(self, playlist_id: str, uris: list[str]) -> None:
        if not uris:
            return

        chunk_size = 100
        for start in range(0, len(uris), chunk_size):
            chunk = uris[start:start + chunk_size]
            self.client.playlist_remove_all_occurrences_of_items(playlist_id, chunk)