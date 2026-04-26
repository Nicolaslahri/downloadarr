"""Free public torrent indexers — no API key required.

Each module exports a Protocol-conforming Indexer that searches a
specific public source. They're toggled on/off via settings (default:
all on, since none cost anything to query).
"""
from app.indexers.free.nyaa import NyaaIndexer
from app.indexers.free.torrents_csv import TorrentsCsvIndexer
from app.indexers.free.x1337 import X1337Indexer

__all__ = ["NyaaIndexer", "TorrentsCsvIndexer", "X1337Indexer"]
