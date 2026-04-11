from __future__ import annotations

import logging
from typing import Any, List

import spotipy
from spotipy.exceptions import SpotifyException

from app.config.constants import EPISODE_FETCH_LIMIT, SPOTIFY_MARKET

logger = logging.getLogger(__name__)


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
        logger.info(
            "Fetching playlist items | playlist_id=%s offset=%s limit=%s",
            playlist_id,
            offset,
            limit,
        )

        response = self.client.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            additional_types=("episode",),
        )

        items = response.get("items", [])
        if not isinstance(items, list):
            logger.warning("Playlist items response is invalid | playlist_id=%s", playlist_id)
            return []

        logger.debug("Fetched %s playlist item(s) | playlist_id=%s", len(items), playlist_id)
        return items

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        try:
            response = self.client.episode(
                episode_id,
                market=SPOTIFY_MARKET,
            )
            return response if isinstance(response, dict) else None
        except SpotifyException as exc:
            if exc.http_status == 403:
                logger.warning("Episode forbidden (403), skipping | episode_id=%s", episode_id)
                return None

            logger.error("Failed to fetch episode | episode_id=%s", episode_id, exc_info=True)
            raise

    def get_episode_resume_points(self, episode_ids: list[str]) -> dict[str, bool]:
        result: dict[str, bool] = {}

        for episode_id in episode_ids:
            raw_episode = self.get_episode(episode_id)
            if not raw_episode:
                continue

            resume_point = raw_episode.get("resume_point", {})
            if not isinstance(resume_point, dict):
                resume_point = {}

            fully_played = bool(resume_point.get("fully_played", False))
            result[episode_id] = fully_played

            logger.debug(
                "Resume point fetched | episode_id=%s fully_played=%s",
                episode_id,
                fully_played,
            )

        return result

    def add_items_to_playlist(self, playlist_id: str, uris: list[str]) -> None:
        if not uris:
            return

        chunk_size = 100
        for start in range(0, len(uris), chunk_size):
            chunk = uris[start:start + chunk_size]
            self.client.playlist_add_items(playlist_id, chunk)

        logger.info("Added %s item(s) to playlist | playlist_id=%s", len(uris), playlist_id)

    def replace_playlist_items(self, playlist_id: str, uris: list[str]) -> None:
        if uris:
            first_chunk = uris[:100]
            self.client.playlist_replace_items(playlist_id, first_chunk)

            remaining = uris[100:]
            if remaining:
                self.add_items_to_playlist(playlist_id, remaining)

            logger.info(
                "Replaced playlist contents | playlist_id=%s final_count=%s",
                playlist_id,
                len(uris),
            )
            return

        current_items = self.get_playlist_items(playlist_id)
        current_uris: list[str] = []

        for item in current_items:
            track = item.get("track") or item.get("item")
            if not isinstance(track, dict):
                continue

            uri = track.get("uri")
            if isinstance(uri, str) and uri:
                current_uris.append(uri)

        if current_uris:
            self.remove_all_occurrences_from_playlist(playlist_id, current_uris)

        logger.info("Cleared playlist contents | playlist_id=%s", playlist_id)

    def remove_all_occurrences_from_playlist(self, playlist_id: str, uris: list[str]) -> None:
        if not uris:
            return

        chunk_size = 100
        for start in range(0, len(uris), chunk_size):
            chunk = uris[start:start + chunk_size]
            self.client.playlist_remove_all_occurrences_of_items(playlist_id, chunk)

        logger.info("Removed %s item(s) from playlist | playlist_id=%s", len(uris), playlist_id)