from dataclasses import dataclass


@dataclass
class TorrentDetailFile:
    idx: int
    name: str
    components: list[str]
    length: int
    included: bool
    attributes: dict[str, bool]


@dataclass
class TorrentDetail:
    id: int | None
    info_hash: str
    name: str
    output_folder: str
    files: list[TorrentDetailFile]


@dataclass
class AddTorrent:
    # in case of list_only=true there is no id
    id: int | None
    details: TorrentDetail
    output_folder: str
    seen_peers: list | None
