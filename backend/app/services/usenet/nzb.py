"""Tiny NZB (XML) parser. Yields one NzbFile per <file>, ordered segments inside."""
from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET


@dataclass
class NzbSegment:
    number: int
    bytes: int
    message_id: str


@dataclass
class NzbFile:
    poster: str
    subject: str
    groups: list[str]
    segments: list[NzbSegment] = field(default_factory=list)


@dataclass
class Nzb:
    files: list[NzbFile]

    @property
    def total_bytes(self) -> int:
        return sum(s.bytes for f in self.files for s in f.segments)


_NS = "{http://www.newzbin.com/DTD/2003/nzb}"


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse(xml_bytes: bytes) -> Nzb:
    root = ET.fromstring(xml_bytes)
    files: list[NzbFile] = []
    for f in root.iter():
        if _strip_ns(f.tag) != "file":
            continue
        poster = f.get("poster") or ""
        subject = f.get("subject") or ""
        groups: list[str] = []
        segments: list[NzbSegment] = []
        for child in f:
            t = _strip_ns(child.tag)
            if t == "groups":
                for g in child:
                    if _strip_ns(g.tag) == "group" and g.text:
                        groups.append(g.text.strip())
            elif t == "segments":
                for s in child:
                    if _strip_ns(s.tag) != "segment":
                        continue
                    try:
                        num = int(s.get("number") or 0)
                        size = int(s.get("bytes") or 0)
                    except ValueError:
                        continue
                    mid = (s.text or "").strip()
                    if mid:
                        segments.append(NzbSegment(number=num, bytes=size, message_id=mid))
        segments.sort(key=lambda x: x.number)
        files.append(NzbFile(poster=poster, subject=subject, groups=groups, segments=segments))
    return Nzb(files=files)
