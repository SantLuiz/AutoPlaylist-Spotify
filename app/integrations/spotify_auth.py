from __future__ import annotations

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config.settings import AppConfig

SCOPES = [
    "playlist-modify-private",
    "playlist-modify-public",
    "playlist-read-private",
    "user-library-read",
    "user-read-playback-position",
]


def build_spotify_client(config: AppConfig) -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        scope=" ".join(SCOPES),
        open_browser=True,
        cache_path=".spotify_cache",
        show_dialog=False,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
