"""Connection-pooled NNTP client with yEnc decoding.

Designed for music workloads: short connection life, parallel article fetches
across N connections to a single news server. Uses sabyenc3 for decode.
"""
from __future__ import annotations

import asyncio
import logging
import re
import socket
import ssl as _ssl
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class NntpConfig:
    host: str
    port: int = 563
    ssl: bool = True
    username: str = ""
    password: str = ""
    connections: int = 10


_LINE_END = b"\r\n"
_END_BODY = b"\r\n.\r\n"


class NntpError(RuntimeError):
    pass


class _Conn:
    """Bare-minimum NNTP wire client. Auth + BODY <message-id>."""

    def __init__(self, cfg: NntpConfig):
        self.cfg = cfg
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        ctx = _ssl.create_default_context() if self.cfg.ssl else None
        self.reader, self.writer = await asyncio.open_connection(
            self.cfg.host, self.cfg.port, ssl=ctx
        )
        # Banner: 200 = posting allowed, 201 = read-only access
        await self._read_status(200, 201)
        if self.cfg.username:
            await self._cmd(f"AUTHINFO USER {self.cfg.username}", expect={281, 381})
            if self.cfg.password:
                await self._cmd(f"AUTHINFO PASS {self.cfg.password}", expect={281})

    async def close(self) -> None:
        if self.writer is None:
            return
        try:
            self.writer.write(b"QUIT\r\n")
            await self.writer.drain()
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
        self.writer = None
        self.reader = None

    async def _cmd(self, line: str, expect: set[int]) -> str:
        assert self.writer and self.reader
        self.writer.write(line.encode("ascii", "ignore") + _LINE_END)
        await self.writer.drain()
        try:
            return await self._read_status(*expect)
        except NntpError as e:
            # Surface which command was rejected — without echoing secrets.
            verb = line.split(" ", 1)[0]
            arg = line.split(" ", 2)[1] if " " in line else ""
            label = f"{verb} {arg}".strip() if verb in ("AUTHINFO",) and not arg.startswith("PASS") else verb
            if verb == "AUTHINFO" and arg == "PASS":
                label = "AUTHINFO PASS"
            raise NntpError(f"after {label}: {e}") from e

    async def _read_status(self, *expect: int) -> str:
        assert self.reader
        line = await self.reader.readuntil(_LINE_END)
        text = line.decode("latin-1").strip()
        try:
            code = int(text.split(" ", 1)[0])
        except Exception as e:
            raise NntpError(f"bad NNTP response: {text!r}") from e
        if expect and code not in expect:
            raise NntpError(f"unexpected NNTP {code}: {text}")
        return text

    async def fetch_body(self, message_id: str) -> bytes:
        """Fetch one article body (message-id includes <>) and return raw yEnc bytes."""
        assert self.writer and self.reader
        mid = message_id if message_id.startswith("<") else f"<{message_id}>"
        self.writer.write(f"BODY {mid}\r\n".encode("ascii", "ignore"))
        await self.writer.drain()
        status = await self.reader.readuntil(_LINE_END)
        s = status.decode("latin-1").strip()
        if not s.startswith("222"):
            raise NntpError(f"BODY {mid} → {s}")
        # Read multi-line body until "\r\n.\r\n"
        chunks: list[bytes] = []
        while True:
            line = await self.reader.readuntil(_LINE_END)
            if line == b".\r\n":
                break
            # Per RFC 3977, lines beginning with "." are dot-stuffed.
            if line.startswith(b".."):
                line = line[1:]
            chunks.append(line)
        return b"".join(chunks)


class NntpPool:
    def __init__(self, cfg: NntpConfig):
        self.cfg = cfg
        self._sem = asyncio.Semaphore(max(1, cfg.connections))
        self._idle: asyncio.Queue[_Conn] = asyncio.Queue()

    @asynccontextmanager
    async def acquire(self):
        await self._sem.acquire()
        try:
            try:
                conn = self._idle.get_nowait()
            except asyncio.QueueEmpty:
                conn = _Conn(self.cfg)
                await conn.connect()
            try:
                yield conn
                await self._idle.put(conn)
            except Exception:
                await conn.close()
                raise
        finally:
            self._sem.release()

    async def shutdown(self) -> None:
        while not self._idle.empty():
            try:
                conn = self._idle.get_nowait()
            except asyncio.QueueEmpty:
                break
            await conn.close()


_YENC_NAME_RE = re.compile(rb"^=ybegin .*name=(.+?)\s*$", re.MULTILINE)


def _decode_yenc(raw: bytes) -> tuple[str, bytes]:
    """Decode yEnc article. Returns (filename, decoded_bytes).

    Uses sabyenc3 if available; falls back to a pure-Python decoder.
    """
    try:
        import sabyenc3  # type: ignore

        # sabyenc3.decode_usenet_chunks expects a list of bytes (one per chunk)
        # but sabyenc3.simple_decoder also exists in newer versions. We use
        # the simple shim that handles a single concatenated body.
        result = sabyenc3.decode_usenet_chunks([raw], len(raw))
        # result tuple: (output, filename, ...) — exact shape varies between
        # sabyenc3 versions; tolerate both 5- and 6-tuple signatures.
        if isinstance(result, tuple) and len(result) >= 2:
            out = result[0]
            name = result[1]
            if isinstance(name, bytes):
                name = name.decode("latin-1", "replace")
            return name or "", out or b""
    except Exception as e:
        log.debug("sabyenc3 unavailable, falling back: %s", e)

    # Pure-Python fallback
    name_match = _YENC_NAME_RE.search(raw)
    name = (name_match.group(1).decode("latin-1") if name_match else "").strip()
    # Strip header/trailer lines
    lines = raw.splitlines()
    body_lines = [
        l for l in lines if not l.startswith((b"=ybegin", b"=ypart", b"=yend"))
    ]
    data = b"".join(body_lines)
    out = bytearray()
    escape = False
    for byte in data:
        if escape:
            out.append((byte - 64 - 42) & 0xFF)
            escape = False
        elif byte == 0x3D:  # '='
            escape = True
        elif byte in (0x0D, 0x0A):
            continue
        else:
            out.append((byte - 42) & 0xFF)
    return name, bytes(out)


async def download_segment(pool: NntpPool, message_id: str) -> tuple[str, bytes]:
    async with pool.acquire() as conn:
        raw = await conn.fetch_body(message_id)
    return _decode_yenc(raw)


async def download_files(
    pool: NntpPool,
    files: list,  # list[NzbFile]
    dest_dir: Path,
    progress: callable | None = None,
    bytes_progress: callable | None = None,
) -> list[Path]:
    """Download every file in the NZB into dest_dir.

    `progress(done_segments, total_segments)` (sync) — kept for log lines.
    `bytes_progress(done_bytes, total_bytes)` (async) — for the UI.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    total_segments = sum(len(f.segments) for f in files)
    total_bytes = sum(s.bytes for f in files for s in f.segments)
    done_segments = 0
    done_bytes = 0

    for f in files:
        # Index segments so we can look up byte count when each completes.
        seg_bytes = {s.number: s.bytes for s in f.segments}

        async def fetch_seg(seg):
            return seg.number, await download_segment(pool, seg.message_id)

        tasks = [asyncio.create_task(fetch_seg(s)) for s in f.segments]
        chunks: list[tuple[int, str, bytes]] = []
        try:
            for fut in asyncio.as_completed(tasks):
                num, (name, data) = await fut
                chunks.append((num, name, data))
                done_segments += 1
                done_bytes += seg_bytes.get(num) or len(data)
                if progress:
                    progress(done_segments, total_segments)
                if bytes_progress:
                    await bytes_progress(done_bytes, total_bytes)
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

        chunks.sort(key=lambda x: x[0])
        if not chunks:
            continue
        filename = next((n for _, n, _ in chunks if n), None) or f.subject or "file.bin"
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename).strip() or "file.bin"
        out = dest_dir / filename
        with open(out, "wb") as fh:
            for _, _, data in chunks:
                fh.write(data)
        out_paths.append(out)

    return out_paths
