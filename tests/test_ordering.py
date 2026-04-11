from app.domain.models import Episode, Podcast
from app.domain.ordering import order_episodes_by_podcast_priority


def test_order_episodes_by_podcast_priority() -> None:
    podcasts = [
        Podcast(name="B", show_id="show-b", priority=2),
        Podcast(name="A", show_id="show-a", priority=1),
    ]
    episodes = [
        Episode(id="2", uri="u2", name="ep b", show_id="show-b", show_name="B", release_date="2026-04-10"),
        Episode(id="1", uri="u1", name="ep a", show_id="show-a", show_name="A", release_date="2026-04-10"),
    ]
    ordered = order_episodes_by_podcast_priority(episodes, podcasts)
    assert ordered[0].show_id == "show-a"
