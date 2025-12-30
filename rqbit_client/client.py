from typing import Any, Literal
import base64
import os

import httpx

from .exceptions import (
    RQBitError,
    RQBitHTTPError,
)
from .models import (
    AddTorrent,
    TorrentDetail,
    TorrentDetailFile,
)


class RQBitClient:
    def __init__(self, base_url: str, auth_userpass: str | None = None):
        self.base_url = base_url
        self.auth_userpass = auth_userpass

        headers: dict[str, str] = {}
        env_auth_userpass = os.environ.get("RQBIT_HTTP_BASIC_AUTH_USERPASS")
        if self.auth_userpass is None and env_auth_userpass:
            self.auth_userpass = env_auth_userpass

        if self.auth_userpass:
            credentials = base64.b64encode(self.auth_userpass.encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        self.client = httpx.Client(base_url=self.base_url, headers=headers)

    def __enter__(self) -> "RQBitClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.client.close()

    def _request(
        self,
        method: str,
        path: str,
        data: str | bytes | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        function = getattr(self.client, method)
        kwargs: dict[str, Any] = {}
        if data:
            kwargs["data"] = data
        if json_data:
            kwargs["json"] = json_data

        try:
            response = function(path, params=params, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise RQBitHTTPError(exc.response) from exc
        except httpx.HTTPError as exc:
            raise RQBitError from exc

    def get_server_info(self) -> dict:
        response = self._request("get", "/")
        return response.json()

    def get_dht_stats(self) -> dict:
        response = self._request("get", "/dht/stats")
        return response.json()

    def get_dht_table(self) -> dict:
        response = self._request("get", "/dht/table")
        return response.json()

    def get_metrics(self) -> str:
        response = self._request("get", "/metrics")
        return response.text

    def get_stats(self) -> dict:
        response = self._request("get", "/stats")
        return response.json()

    def stream_logs(self) -> None:
        raise NotImplementedError("This method requires the async client.")

    def get_torrents(self) -> list[TorrentDetail]:
        response = self._request("get", "/torrents")
        return [
            TorrentDetail(
                id=data["id"],
                info_hash=data["info_hash"],
                name=data["name"],
                output_folder=data["output_folder"],
                files=[],
            )
            for data in response.json()["torrents"]
        ]

    def get_torrents_playlist(self) -> str:
        response = self._request("get", "/torrents/playlist")
        return response.text

    def get_torrent(self, id_or_infohash: int | str) -> TorrentDetail:
        response = self._request("get", f"/torrents/{id_or_infohash}")
        data = response.json()
        return TorrentDetail(
            id=data["id"],
            info_hash=data["info_hash"],
            name=data["name"],
            output_folder=data["output_folder"],
            files=[
                TorrentDetailFile(
                    idx=idx,
                    **file_data,
                )
                for idx, file_data in enumerate(data["files"])
            ],
        )

    def get_torrent_haves(self, id_or_infohash: int | str) -> bytes:
        response = self._request("get", f"/torrents/{id_or_infohash}/haves")
        return response.content

    def get_torrent_metadata(self, id_or_infohash: int | str) -> bytes:
        response = self._request("get", f"/torrents/{id_or_infohash}/metadata")
        return response.content

    def get_torrent_peer_stats(
        self, id_or_infohash: int | str, state: Literal["All", "Live"]
    ) -> dict:
        response = self._request(
            "get", f"/torrents/{id_or_infohash}/peer_stats", params={"state": state}
        )
        return response.json()

    def get_torrent_peer_stats_prometheus(self, id_or_infohash: int | str) -> str:
        response = self._request(
            "get", f"/torrents/{id_or_infohash}/peer_stats/prometheus"
        )
        return response.text

    def get_torrent_playlist(self, id_or_infohash: int | str) -> str:
        response = self._request("get", f"/torrents/{id_or_infohash}/playlist")
        return response.text

    def stream_torrent_file(self, id_or_infohash: int | str, file_idx: int) -> None:
        raise NotImplementedError("This method requires the async client.")

    def set_rust_log(self, new_value: str) -> dict:
        response = self._request("post", "/rust_log", data=new_value)
        return response.json()

    def add_torrent(
        self,
        torrent: str | bytes,
        *,
        overwrite: bool | None = None,
        only_files_regex: str | None = None,
        output_folder: str | None = None,
        list_only: bool | None = None,
    ) -> AddTorrent:
        params = {}
        if overwrite is not None:
            params["overwrite"] = str(overwrite).lower()
        if only_files_regex:
            params["only_files_regex"] = only_files_regex
        if output_folder:
            params["output_folder"] = output_folder
        if list_only is not None:
            params["list_only"] = str(list_only).lower()

        response = self._request("post", "/torrents", data=torrent, params=params)
        data = response.json()
        details = data["details"]
        return AddTorrent(
            id=data["id"],
            seen_peers=data["seen_peers"],
            output_folder=data["output_folder"],
            details=TorrentDetail(
                id=details.get("id"),
                info_hash=details["info_hash"],
                name=details["name"],
                output_folder=details["output_folder"],
                files=[
                    TorrentDetailFile(
                        idx=idx,
                        **file_data,
                    )
                    for idx, file_data in enumerate(details["files"])
                ],
            ),
        )

    def create_torrent(self, directory: str) -> dict:
        response = self._request("post", "/torrents/create", data=directory)
        return response.json()

    def resolve_magnet(self, magnet: str) -> bytes:
        response = self._request("post", "/torrents/resolve_magnet", data=magnet)
        return response.content

    def add_peers(self, id_or_infohash: int | str, peers: str) -> dict:
        response = self._request(
            "post", f"/torrents/{id_or_infohash}/add_peers", data=peers
        )
        return response.json()

    def delete_torrent(self, id_or_infohash: int | str) -> dict:
        response = self._request("post", f"/torrents/{id_or_infohash}/delete")
        return response.json()

    def forget_torrent(self, id_or_infohash: int | str) -> dict:
        response = self._request("post", f"/torrents/{id_or_infohash}/forget")
        return response.json()

    def pause_torrent(self, id_or_infohash: int | str) -> dict:
        response = self._request("post", f"/torrents/{id_or_infohash}/pause")
        return response.json()

    def start_torrent(self, id_or_infohash: int | str) -> dict:
        response = self._request("post", f"/torrents/{id_or_infohash}/start")
        return response.json()

    def update_only_files(
        self, id_or_infohash: int | str, only_files: list[int]
    ) -> dict:
        response = self._request(
            "post",
            f"/torrents/{id_or_infohash}/update_only_files",
            json_data={"only_files": only_files},
        )
        return response.json()
