# MusicDownloadarr

Self-hosted music librarian. Paste a Spotify, Apple Music, YouTube Music, or SoundCloud playlist link — or a "Top 100" YouTube video — and the app extracts the tracklist (LLM-first, Whisper fallback), then downloads each track from sources you control: yt-dlp, Usenet (Newznab indexers + NNTP servers, **in-app**), or torrents (Torznab indexers + embedded libtorrent, **in-app**).

No Prowlarr, no SABnzbd, no qBittorrent. You enter your NZBGeek/Newshosting/Torznab credentials directly; the app does the searching and downloading itself.

Streaming services and YouTube are used **only to enumerate the tracklist** — the actual audio is always pulled from Usenet or torrents at FLAC / 320 kbps quality.

## Run on a Linux server (recommended)

Self-hosted on Linux via Docker is the primary deployment target. The image includes everything: `ffmpeg`, `par2`, `unrar`, `p7zip-full`, and `libtorrent` — no manual binary installs, no PATH wrangling.

```bash
git clone https://github.com/Nicolaslahri/downloadarr.git musicdl
cd musicdl
docker compose up -d --build
```

That's it.

- Web UI: http://your-server:3000
- API docs: http://your-server:8000/docs

Bind mounts (override via env / compose file):
- `./backend/.data` — SQLite, settings, auto-installed tools (persisted)
- `./library` (or `$LIBRARY_PATH`) — final tagged audio library
- `./downloads` — in-flight scratch space; safe to wipe

To upgrade: `git pull && docker compose up -d --build`.

## Run locally (one command, no Docker)

Backend defaults to a local SQLite file at `backend/.data/musicdl.db`, so the whole stack runs without Docker. Linux/macOS users get par2/unrar from their package manager (`apt install par2 unrar` / `brew install par2 unrar`); Windows users get them auto-installed at startup or via the upload escape hatch in Settings → Tools.

### One-time setup

```powershell
# Backend deps
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

# Frontend deps
cd ..\web
npm install
```

### Every time after that

From `web/`:

```powershell
npm run start
```

That's it. `concurrently` launches the FastAPI backend (`api`, port 8000) and Next.js dev server (`web`, port 3000) in the same terminal with prefixed output, and Ctrl+C kills both.

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

If you want them separately:

```powershell
npm run dev:api   # backend only
npm run dev:web   # frontend only
```

The top bar shows a green dot once it can reach the API. Visit `Settings` to wire up your indexers, news servers, AI key, and Spotify credentials.

## External binaries you'll want on PATH

Only matter for the Usenet path:

- **`par2`** — required for repairing PAR2-protected Usenet releases. ([par2cmdline-turbo](https://github.com/animetosho/par2cmdline-turbo/releases))
- **`unrar`** — required for extracting RAR'd Usenet releases. ([RARLab](https://www.rarlab.com/rar_add.htm))

If you skip these, Usenet downloads of plain audio files (no PAR2, no RAR) still work; archived/repaired releases will fail with a clear pointer.

## Faster Usenet decode (optional)

The default install ships a pure-Python yEnc decoder — it works, just slower per segment. If you want SAB-grade speed:

```powershell
pip install -e .[usenet-fast]
```

This pulls `sabyenc3`. On Windows + recent Python (3.13+) you may need MSVC Build Tools or a prebuilt wheel; if pip can't find one, just stay on the pure-Python path.

## Torrent engine install

`libtorrent` doesn't ship pip wheels for Windows + recent Python versions, so it's intentionally excluded from the required deps. Install it separately if you want torrent downloads:

- **Conda (recommended on Windows)**: `conda install -c conda-forge libtorrent` inside the same environment. If you're using a regular `venv`, switch to a conda env (or run `pip install miniforge` style flow) for this one dep.
- **Pre-built wheel**: search for a libtorrent wheel matching your Python version (cp312 etc.) and `pip install` it directly.
- **Skip torrents entirely**: leave it uninstalled — the rest of the app (yt-dlp, Usenet, AI extract, all UI) works fine. Torrent downloads will surface a clean error pointing here until you install.

## What works out of the box

**Tracklist resolution** (no audio is downloaded here — just artist/title pairs):

| Resolver                          | Needs                            |
| --------------------------------- | -------------------------------- |
| YouTube / YT Music playlist       | nothing                          |
| SoundCloud playlist               | nothing                          |
| Apple Music (best-effort scrape)  | nothing                          |
| Spotify                           | Spotify client id + secret       |
| AI extract from a YouTube video   | Anthropic API key                |

**Audio download** (HQ — FLAC, 320 kbps MP3, etc.):

| Source             | Needs                                                          |
| ------------------ | -------------------------------------------------------------- |
| Usenet             | one or more Newznab indexers + one or more NNTP news servers   |
| Torrents           | one or more Torznab indexers + `libtorrent` (see install note) |

You need at least one of Usenet or torrents configured before downloads will work. Without them, the app will resolve playlists and queue tracks, but each track will fail with `No Usenet or torrent indexers configured`.

## How it's wired

```
                   ┌────────────────────┐
   user paste url ─┤  /playlists/import  ├─► Resolver dispatch ─► tracks in DB
                   └────────────────────┘   (Spotify/Apple/YT/SC: read tracklist)
                                                            │
                                                            ▼
                                            asyncio task per track
                                                            │
                                                            ▼
                                       Indexer fan-out:
                                         • Newznab (your NZB indexers)
                                         • Torznab (your torrent indexers)
                                                            │
                                                            ▼
                                       Score & rank by quality profile
                                                            │
                                                            ▼
                              Downloader picks by source kind:
                                • nzb     → NNTP fetch + yEnc + par2/unrar
                                • torrent → embedded libtorrent
                                                            │
                                                            ▼
                                       mutagen tag → organize into library
```

Resolvers, Indexers, and Downloaders are all `Protocol`-based — adding a new playlist source or download backend means dropping one file in the right folder and registering it.

## Roadmap

- [x] Skeleton + Protocol-based extension points
- [x] Streaming-service resolvers (YT/YT Music, Spotify, Apple Music, SoundCloud)
- [x] AI tracklist extraction from YouTube videos
- [x] yt-dlp end-to-end download + tag + organize
- [x] In-app Usenet: Newznab search + NNTP download + par2/unrar
- [x] In-app torrents: Torznab search + libtorrent
- [x] Settings UI: list editors for indexers and servers
- [x] Live job stream over SSE
- [ ] Whisper fallback for videos without descriptions
- [ ] MusicBrainz cover-art lookup
- [ ] Multi-server NNTP failover
- [ ] Per-track source override in the UI
