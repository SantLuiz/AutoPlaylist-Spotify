from __future__ import annotations

from typing import Iterable, List

from app.domain.models import Episode, Podcast


def order_episodes_by_podcast_priority(
    episodes: Iterable[Episode],
    podcasts: list[Podcast],
) -> List[Episode]:
    priority_map = {podcast.show_id: podcast.priority for podcast in podcasts}

    return sorted(
        episodes,
        key=lambda episode: priority_map.get(episode.show_id, 9999),
    )