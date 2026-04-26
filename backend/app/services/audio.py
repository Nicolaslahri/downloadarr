"""mutagen-based audio probe + quality-tier classification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LOSSLESS_EXTS = {".flac", ".alac", ".wav", ".ape", ".wv", ".tak", ".tta", ".dsf", ".dff"}

# Tier order from worst to best. The hard-floor check uses this index.
TIER_ORDER = ["any", "192", "256", "320", "lossless"]


@dataclass
class AudioInfo:
    format: str
    bitrate_kbps: int
    sample_rate: int
    channels: int
    lossless: bool

    @property
    def tier(self) -> str:
        if self.lossless:
            return "lossless"
        if self.bitrate_kbps >= 320:
            return "320"
        if self.bitrate_kbps >= 256:
            return "256"
        if self.bitrate_kbps >= 192:
            return "192"
        return "any"

    def label(self) -> str:
        if self.lossless:
            return f"{self.format.upper()} · lossless"
        return f"{self.format.upper()} · {self.bitrate_kbps} kbps"


def probe(path: Path) -> AudioInfo | None:
    try:
        from mutagen import File as MutaFile  # type: ignore

        audio = MutaFile(str(path))
    except Exception:
        return None
    if audio is None:
        return None
    info = getattr(audio, "info", None)
    if info is None:
        return None

    ext = path.suffix.lower()
    fmt = ext.lstrip(".") or "unknown"
    bitrate_bps = getattr(info, "bitrate", 0) or 0
    sample_rate = int(getattr(info, "sample_rate", 0) or 0)
    channels = int(getattr(info, "channels", 0) or 0)
    lossless_flag = ext in LOSSLESS_EXTS or bool(getattr(info, "codec_lossless", False))

    return AudioInfo(
        format=fmt,
        bitrate_kbps=int(bitrate_bps / 1000) if bitrate_bps else 0,
        sample_rate=sample_rate,
        channels=channels,
        lossless=lossless_flag,
    )


def meets_floor(info: AudioInfo, floor: str) -> bool:
    """Return True if `info` is at least as good as `floor`."""
    if floor not in TIER_ORDER:
        return True
    return TIER_ORDER.index(info.tier) >= TIER_ORDER.index(floor)
