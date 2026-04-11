from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from app.domain.models import Episode
from app.repositories.podcasts_repository import PodcastsRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.state_repository import StateRepository
from app.services.episode_service import EpisodeService
from app.services.playlist_service import PlaylistService

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(
        self,
        playlist_id: str,
        podcasts_repository: PodcastsRepository,
        settings_repository: SettingsRepository,
        state_repository: StateRepository,
        episode_service: EpisodeService,
        playlist_service: PlaylistService,
    ) -> None:
        self.playlist_id = playlist_id
        self.podcasts_repository = podcasts_repository
        self.settings_repository = settings_repository
        self.state_repository = state_repository
        self.episode_service = episode_service
        self.playlist_service = playlist_service

    def run_sync(self) -> Dict[str, Any]:
        logger.info("Starting synchronization")

        settings = self.settings_repository.load()
        state = self.state_repository.load()
        podcasts = self.podcasts_repository.load()

        processed_episode_ids: Set[str] = set(state.get("processed_episode_ids", []))
        interval_days = getattr(settings, "interval_days", 14)

        logger.info(
            "Synchronization context loaded | interval_days=%s podcasts=%s processed_ids=%s",
            interval_days,
            len(podcasts),
            len(processed_episode_ids),
        )

        existing_unfinished, removed_count = self.playlist_service.remove_finished_episodes(
            self.playlist_id
        )
        active_playlist_ids = self.playlist_service.extract_episode_ids(existing_unfinished)

        logger.info(
            "Playlist cleanup finished | removed_finished=%s remaining_unfinished=%s",
            removed_count,
            len(existing_unfinished),
        )

        new_candidate_episodes = self._collect_new_candidate_episodes(
            podcasts=podcasts,
            interval_days=interval_days,
            processed_episode_ids=processed_episode_ids,
            active_playlist_ids=active_playlist_ids,
        )

        desired_episodes = self.playlist_service.build_desired_order(
            existing_unfinished=existing_unfinished,
            new_episodes=new_candidate_episodes,
            podcasts=podcasts,
        )

        self.playlist_service.sync_playlist_to_order(
            playlist_id=self.playlist_id,
            desired_episodes=desired_episodes,
        )

        processed_episode_ids.update(episode.id for episode in desired_episodes)

        self._save_state(
            processed_episode_ids=processed_episode_ids,
            removed_count=removed_count,
            playlist_size=len(desired_episodes),
        )

        logger.info(
            "Synchronization finished successfully | new_found=%s removed_finished=%s final_total=%s",
            len(new_candidate_episodes),
            removed_count,
            len(desired_episodes),
        )

        return {
            "success": True,
            "removed_finished": removed_count,
            "existing_unfinished": len(existing_unfinished),
            "new_found": len(new_candidate_episodes),
            "final_total": len(desired_episodes),
            "interval_days": interval_days,
        }

    def _collect_new_candidate_episodes(
        self,
        podcasts,
        interval_days: int,
        processed_episode_ids: Set[str],
        active_playlist_ids: Set[str],
    ) -> List[Episode]:
        new_candidate_episodes: List[Episode] = []
        new_candidate_ids: Set[str] = set()

        for podcast in podcasts:
            episodes = self.episode_service.get_recent_unfinished_episodes(
                podcast=podcast,
                interval_days=interval_days,
            )

            logger.info(
                "Podcast checked | name=%s recent_unfinished=%s",
                podcast.name,
                len(episodes),
            )

            for episode in episodes:
                if episode.id in active_playlist_ids:
                    logger.debug(
                        "Episode skipped: already active in playlist | episode_id=%s name=%s",
                        episode.id,
                        episode.name,
                    )
                    continue

                if episode.id in new_candidate_ids:
                    logger.debug(
                        "Episode skipped: duplicate candidate | episode_id=%s name=%s",
                        episode.id,
                        episode.name,
                    )
                    continue

                if episode.id in processed_episode_ids:
                    logger.debug(
                        "Episode skipped: already processed | episode_id=%s name=%s",
                        episode.id,
                        episode.name,
                    )
                    continue

                new_candidate_episodes.append(episode)
                new_candidate_ids.add(episode.id)

                logger.debug(
                    "Episode accepted as new candidate | episode_id=%s name=%s",
                    episode.id,
                    episode.name,
                )

        logger.info("New candidate collection finished | total_new_candidates=%s", len(new_candidate_episodes))
        return new_candidate_episodes

    def _save_state(
        self,
        processed_episode_ids: Set[str],
        removed_count: int,
        playlist_size: int,
    ) -> None:
        new_state = {
            "processed_episode_ids": sorted(processed_episode_ids),
            "last_sync_at": datetime.now().isoformat(timespec="seconds"),
            "last_removed_count": removed_count,
            "last_playlist_size": playlist_size,
        }
        self.state_repository.save(new_state)

        logger.info(
            "Synchronization state saved | processed_ids=%s removed_count=%s playlist_size=%s",
            len(processed_episode_ids),
            removed_count,
            playlist_size,
        )