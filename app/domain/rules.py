from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List

from app.domain.models import Episode


def is_recent_episode(release_date: str, interval_days: int) -> bool:
    try:
        released_at = datetime.strptime(release_date[:10], "%Y-%m-%d").date()
    except ValueError:
        return False

    cutoff = date.today() - timedelta(days=interval_days)
    return released_at >= cutoff


def filter_recent_unfinished_episodes(episodes: Iterable[Episode], interval_days: int) -> List[Episode]:
    return [
        episode
        for episode in episodes
        if (not episode.is_finished and is_recent_episode(episode.release_date, interval_days))
    ]
