import os
import sys
import json
from typing import Optional, Dict, Any, List

import requests


API_BASE = "https://api.spotify.com/v1"
ACCOUNTS_BASE = "https://accounts.spotify.com"


class SpotifyDebugger:
    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.access_token = access_token or os.getenv("SPOTIFY_ACCESS_TOKEN", "")
        self.refresh_token = refresh_token or os.getenv("SPOTIFY_REFRESH_TOKEN", "")
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("SPOTIFY_ACCESS_TOKEN is not set.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _print_response(self, response: requests.Response) -> None:
        print(f"\nStatus: {response.status_code}")
        print("Headers:")
        for key, value in response.headers.items():
            if key.lower() in {"content-type", "retry-after"}:
                print(f"  {key}: {value}")

        try:
            data = response.json()
            print("\nJSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except ValueError:
            print("\nText:")
            print(response.text)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        url = f"{API_BASE}{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self._headers(),
            params=params,
            json=json_body,
            timeout=self.timeout,
        )
        return response

    def get_me(self) -> None:
        print("== GET /me ==")
        response = self._request("GET", "/me")
        self._print_response(response)

    def get_playlists(self, limit: int = 20) -> None:
        print("== GET /me/playlists ==")
        response = self._request("GET", "/me/playlists", params={"limit": limit})
        self._print_response(response)

    def search_show(self, query: str, limit: int = 10) -> None:
        print("== GET /search (type=show) ==")
        response = self._request(
            "GET",
            "/search",
            params={
                "q": query,
                "type": "show",
                "limit": limit,
            },
        )
        self._print_response(response)

    def get_show(self, show_id: str) -> None:
        print(f"== GET /shows/{show_id} ==")
        response = self._request("GET", f"/shows/{show_id}")
        self._print_response(response)

    def get_show_episodes(self, show_id: str, limit: int = 20) -> None:
        print(f"== GET /shows/{show_id}/episodes ==")
        response = self._request(
            "GET",
            f"/shows/{show_id}/episodes",
            params={"limit": limit},
        )
        self._print_response(response)

    def get_playlist_items(self, playlist_id: str, limit: int = 20) -> None:
        print(f"== GET /playlists/{playlist_id}/items ==")
        response = self._request(
            "GET",
            f"/playlists/{playlist_id}/items",
            params={"limit": limit},
        )
        self._print_response(response)

    def create_playlist(
        self,
        name: str,
        public: bool = False,
        description: str = "Created by spotify_debug.py",
    ) -> None:
        print("== GET /me (fetch user id) ==")
        me_response = self._request("GET", "/me")
        try:
            me_data = me_response.json()
        except ValueError:
            self._print_response(me_response)
            return

        user_id = me_data.get("id")
        if not user_id:
            print("Could not get user id from /me response.")
            self._print_response(me_response)
            return

        print(f"== POST /users/{user_id}/playlists ==")
        response = self._request(
            "POST",
            f"/users/{user_id}/playlists",
            json_body={
                "name": name,
                "public": public,
                "description": description,
            },
        )
        self._print_response(response)

    def add_items_to_playlist(self, playlist_id: str, uris: List[str]) -> None:
        print(f"== POST /playlists/{playlist_id}/tracks ==")
        response = self._request(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            json_body={"uris": uris},
        )
        self._print_response(response)

    def refresh_access_token(self) -> None:
        if not self.refresh_token:
            print("SPOTIFY_REFRESH_TOKEN is not set.")
            return
        if not self.client_id:
            print("SPOTIFY_CLIENT_ID is not set.")
            return

        print("== POST /api/token (refresh token) ==")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(
            f"{ACCOUNTS_BASE}/api/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        self._print_response(response)


def print_usage() -> None:
    print(
        """
Usage:
  python spotify_debug.py me
  python spotify_debug.py playlists [limit]
  python spotify_debug.py search-show "podcast name" [limit]
  python spotify_debug.py show SHOW_ID
  python spotify_debug.py show-episodes SHOW_ID [limit]
  python spotify_debug.py playlist-items PLAYLIST_ID [limit]
  python spotify_debug.py create-playlist "Playlist Name" [public|private]
  python spotify_debug.py add-items PLAYLIST_ID spotify:episode:ID1 [spotify:episode:ID2 ...]
  python spotify_debug.py refresh

Environment variables:
  SPOTIFY_ACCESS_TOKEN
  SPOTIFY_REFRESH_TOKEN
  SPOTIFY_CLIENT_ID
  SPOTIFY_CLIENT_SECRET
"""
    )


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        return

    cmd = sys.argv[1].lower()
    debugger = SpotifyDebugger()

    try:
        if cmd == "me":
            debugger.get_me()

        elif cmd == "playlists":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            debugger.get_playlists(limit=limit)

        elif cmd == "search-show":
            if len(sys.argv) < 3:
                print('Missing search text. Example: python spotify_debug.py search-show "NerdCast"')
                return
            query = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            debugger.search_show(query=query, limit=limit)

        elif cmd == "show":
            if len(sys.argv) < 3:
                print("Missing SHOW_ID.")
                return
            debugger.get_show(show_id=sys.argv[2])

        elif cmd == "show-episodes":
            if len(sys.argv) < 3:
                print("Missing SHOW_ID.")
                return
            show_id = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            debugger.get_show_episodes(show_id=show_id, limit=limit)

        elif cmd == "playlist-items":
            if len(sys.argv) < 3:
                print("Missing PLAYLIST_ID.")
                return
            playlist_id = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            debugger.get_playlist_items(playlist_id=playlist_id, limit=limit)

        elif cmd == "create-playlist":
            if len(sys.argv) < 3:
                print('Missing playlist name. Example: python spotify_debug.py create-playlist "My Playlist" private')
                return
            name = sys.argv[2]
            visibility = sys.argv[3].lower() if len(sys.argv) > 3 else "private"
            debugger.create_playlist(name=name, public=(visibility == "public"))

        elif cmd == "add-items":
            if len(sys.argv) < 4:
                print("Usage: python spotify_debug.py add-items PLAYLIST_ID spotify:episode:ID1 [spotify:episode:ID2 ...]")
                return
            playlist_id = sys.argv[2]
            uris = sys.argv[3:]
            debugger.add_items_to_playlist(playlist_id=playlist_id, uris=uris)

        elif cmd == "refresh":
            debugger.refresh_access_token()

        else:
            print_usage()

    except requests.RequestException as exc:
        print(f"Network error: {exc}")
    except ValueError as exc:
        print(f"Configuration error: {exc}")


if __name__ == "__main__":
    main()