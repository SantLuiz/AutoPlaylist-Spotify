from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, List

from app.domain.models import Episode, Podcast
from app.integrations.spotify_client import SpotifyGateway


class EpisodeService:
    def __init__(self, spotify_gateway: SpotifyGateway) -> None:
        self.spotify_gateway = spotify_gateway

    def get_recent_unfinished_episodes(
        self,
        podcast: Podcast,
        interval_days: int,
        fetch_limit: int = 50,
    ) -> List[Episode]:
        raw_episodes = self.spotify_gateway.get_show_episodes(
            show_id=podcast.show_id,
            limit=fetch_limit,
        )

        if not raw_episodes:
            return []

        cutoff_date = date.today() - timedelta(days=interval_days)
        valid_episodes: List[Episode] = []

        for raw_episode in raw_episodes:
            episode = self._map_show_episode_to_episode(raw_episode, podcast)

            if episode is None:
                continue

            if not self._is_recent_enough(episode.release_date, cutoff_date):
                continue

            if episode.is_finished:
                continue

            valid_episodes.append(episode)

        valid_episodes.sort(
            key=lambda episode: (episode.release_date, episode.name.lower()),
            reverse=True,
        )

        return valid_episodes

    def _map_show_episode_to_episode(
        self,
        raw_episode: dict[str, Any],
        podcast: Podcast,
    ) -> Episode | None:
        if not isinstance(raw_episode, dict):
            return None

        episode_id = raw_episode.get("id")
        episode_uri = raw_episode.get("uri")
        episode_name = raw_episode.get("name")
        release_date = raw_episode.get("release_date")

        if not episode_id or not episode_uri or not episode_name or not release_date:
            return None

        resume_point = raw_episode.get("resume_point", {})
        if not isinstance(resume_point, dict):
            resume_point = {}

        is_finished = bool(resume_point.get("fully_played", False))

        show = raw_episode.get("show", {})
        if not isinstance(show, dict):
            show = {}

        show_id = show.get("id") or podcast.show_id
        show_name = show.get("name") or podcast.name

        return Episode(
            id=episode_id,
            uri=episode_uri,
            name=episode_name,
            show_id=show_id,
            show_name=show_name,
            release_date=release_date,
            is_finished=is_finished,
        )

    def _is_recent_enough(self, release_date_str: str, cutoff_date: date) -> bool:
        parsed_release_date = self._parse_release_date(release_date_str)
        if parsed_release_date is None:
            return False

        return parsed_release_date >= cutoff_date

    def _parse_release_date(self, value: str) -> date | None:
        if not value:
            return None

        formats = ("%Y-%m-%d", "%Y-%m", "%Y")

        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.date()
            except ValueError:
                continue

        return None