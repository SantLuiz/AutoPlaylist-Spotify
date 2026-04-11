from __future__ import annotations

from typing import Iterable, List, Tuple

from app.domain.models import Episode, Podcast
from app.domain.ordering import order_episodes_by_podcast_priority
from app.integrations.spotify_client import SpotifyGateway


class PlaylistService:
    def __init__(self, spotify_gateway: SpotifyGateway) -> None:
        self.spotify_gateway = spotify_gateway

    def get_playlist_episodes(self, playlist_id: str) -> List[Episode]:
        episodes: List[Episode] = []
        offset = 0
        limit = 100

        while True:
            items = self.spotify_gateway.get_playlist_items(
                playlist_id=playlist_id,
                limit=limit,
                offset=offset,
            )

            if not items:
                break

            for item in items:
                episode = self._map_playlist_item_to_episode(item)
                if episode is not None:
                    episodes.append(episode)

            if len(items) < limit:
                break

            offset += limit

        return episodes

    def remove_finished_episodes(self, playlist_id: str) -> Tuple[List[Episode], int]:
        playlist_episodes = self.get_playlist_episodes(playlist_id)

        finished_episodes = [episode for episode in playlist_episodes if episode.is_finished]
        unfinished_episodes = [episode for episode in playlist_episodes if not episode.is_finished]

        if finished_episodes:
            self._remove_episodes_by_uri(
                playlist_id=playlist_id,
                uris=[episode.uri for episode in finished_episodes],
            )

        return unfinished_episodes, len(finished_episodes)

    def build_desired_order(
        self,
        existing_unfinished: List[Episode],
        new_episodes: List[Episode],
        podcasts: List[Podcast],
    ) -> List[Episode]:
        merged: List[Episode] = []
        seen_ids: set[str] = set()

        for episode in existing_unfinished + new_episodes:
            if episode.id in seen_ids:
                continue
            seen_ids.add(episode.id)
            merged.append(episode)

        priority_map = {podcast.show_id: podcast.priority for podcast in podcasts}

        ordered = order_episodes_by_podcast_priority(merged, podcasts)

        grouped: dict[str, List[Episode]] = {}
        for episode in ordered:
            grouped.setdefault(episode.show_id, []).append(episode)

        final_order: List[Episode] = []

        for podcast in sorted(podcasts, key=lambda p: p.priority):
            show_episodes = grouped.get(podcast.show_id, [])
            show_episodes_sorted = sorted(
                show_episodes,
                key=lambda episode: (episode.release_date, episode.name.lower()),
                reverse=True,
            )
            final_order.extend(show_episodes_sorted)

        remaining_show_ids = {
            episode.show_id
            for episode in merged
            if episode.show_id not in priority_map
        }

        for show_id in sorted(remaining_show_ids):
            extras = [episode for episode in merged if episode.show_id == show_id]
            extras_sorted = sorted(
                extras,
                key=lambda episode: (episode.release_date, episode.name.lower()),
                reverse=True,
            )
            final_order.extend(extras_sorted)

        return final_order

    def sync_playlist_to_order(
        self,
        playlist_id: str,
        desired_episodes: List[Episode],
    ) -> None:
        current_episodes = self.get_playlist_episodes(playlist_id)

        current_uris = [episode.uri for episode in current_episodes]
        desired_uris = [episode.uri for episode in desired_episodes]

        if current_uris == desired_uris:
            return

        self.spotify_gateway.replace_playlist_items(playlist_id, desired_uris)

    def extract_episode_ids(self, episodes: Iterable[Episode]) -> set[str]:
        return {episode.id for episode in episodes}

    def add_episodes(self, playlist_id: str, episodes: Iterable[Episode]) -> int:
        uris = [episode.uri for episode in episodes]
        if not uris:
            return 0

        self.spotify_gateway.add_items_to_playlist(playlist_id, uris)
        return len(uris)

    def _map_playlist_item_to_episode(self, item: dict) -> Episode | None:
        if not isinstance(item, dict):
            return None

        track = item.get("track")
        if not isinstance(track, dict):
            return None

        item_type = track.get("type")
        if item_type != "episode":
            return None

        episode_id = track.get("id")
        episode_uri = track.get("uri")
        episode_name = track.get("name")
        release_date = track.get("release_date")

        show = track.get("show", {})
        if not isinstance(show, dict):
            show = {}

        show_id = show.get("id")
        show_name = show.get("name", "Unknown podcast")

        resume_point = track.get("resume_point", {})
        if not isinstance(resume_point, dict):
            resume_point = {}

        is_finished = bool(resume_point.get("fully_played", False))

        if not episode_id or not episode_uri or not episode_name or not release_date or not show_id:
            return None

        return Episode(
            id=episode_id,
            uri=episode_uri,
            name=episode_name,
            show_id=show_id,
            show_name=show_name,
            release_date=release_date,
            is_finished=is_finished,
        )

    def _remove_episodes_by_uri(self, playlist_id: str, uris: List[str]) -> None:
        if not uris:
            return

        self.spotify_gateway.remove_all_occurrences_from_playlist(playlist_id, uris)