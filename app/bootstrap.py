from app.config.settings import AppConfig
from app.integrations.spotify_auth import build_spotify_client
from app.integrations.spotify_client import SpotifyGateway
from app.repositories.podcasts_repository import PodcastsRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.state_repository import StateRepository
from app.services.episode_service import EpisodeService
from app.services.playlist_service import PlaylistService
from app.services.scheduler_service import SchedulerService
from app.services.sync_service import SyncService
from app.ui.main_window import MainWindow


class Application:
    def __init__(self, config: AppConfig, window: MainWindow, scheduler: SchedulerService) -> None:
        self.config = config
        self.window = window
        self.scheduler = scheduler

    def run(self) -> None:
        self.scheduler.start()
        self.window.show()
        self.window.exec_app()


def build_application() -> Application:
    config = AppConfig.load()

    raw_spotify_client = build_spotify_client(config)
    spotify_gateway = SpotifyGateway(raw_spotify_client)

    podcasts_repository = PodcastsRepository(config.podcasts_file)
    state_repository = StateRepository(config.state_file)
    settings_repository = SettingsRepository(config.settings_file)

    episode_service = EpisodeService(spotify_gateway)
    playlist_service = PlaylistService(spotify_gateway)

    sync_service = SyncService(
        playlist_id=config.playlist_id,
        podcasts_repository=podcasts_repository,
        settings_repository=settings_repository,
        state_repository=state_repository,
        episode_service=episode_service,
        playlist_service=playlist_service,
    )

    scheduler = SchedulerService(
        sync_service=sync_service,
        settings_repository=settings_repository,
    )

    window = MainWindow(
        sync_service=sync_service,
        settings_repository=settings_repository,
        scheduler_service=scheduler,
    )

    return Application(
        config=config,
        window=window,
        scheduler=scheduler,
    )