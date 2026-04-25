# MusicDownloadarr

Self-hosted music librarian. Paste a Spotify, Apple Music, YouTube Music, or SoundCloud playlist link — or a "Top 100" YouTube video — and the app extracts the tracklist (LLM-first, Whisper fallback), then downloads each track from sources you control: yt-dlp, Usenet (Newznab indexers + NNTP servers, **in-app**), or torrents (Torznab indexers + embedded libtorrent, **in-app**).

No Prowlarr, no SABnzbd, no qBittorrent. You enter your NZBGeek/Newshosting/Torznab credentials directly; the app does the searching and downloading itself.

## Run locally (zero-infra dev)

The backend defaults to a local SQLite file at `backend/.data/musicdl.db`, so you can run both halves without Docker.

### Backend (FastAPI on :8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend (Next.js on :3000)

```powershell
cd web
npm install
npm run dev
```

Open http://localhost:3000.

The top bar shows a green dot once it can reach the API. Visit `Settings` to wire up your indexers, news servers, AI key, and Spotify credentials.

## External binaries you'll want on PATH

- **`ffmpeg`** — required by `yt-dlp` for audio extraction. ([download](https://www.gyan.dev/ffmpeg/builds/))
- **`par2`** — required for repairing PAR2-protected Usenet releases. ([par2cmdline-turbo](https://github.com/animetosho/par2cmdline-turbo/releases))
- **`unrar`** — required for extracting RAR'd Usenet releases. ([RARLab](https://www.rarlab.com/rar_add.htm))

You only need par2/unrar if you plan to download from Usenet. yt-dlp and torrent paths don't use them.

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

| Feature                                       | Needs                            |
| --------------------------------------------- | -------------------------------- |
| YouTube / YouTube Music playlist import       | nothing                          |
| SoundCloud playlist import                    | nothing                          |
| yt-dlp track download (m4a)                   | `ffmpeg` on PATH                 |
| Apple Music playlist (best-effort scrape)     | nothing                          |
| Spotify playlist import                       | Spotify client id + secret       |
| AI tracklist from a YouTube video             | Anthropic API key                |
| Torrent search & download                     | Torznab indexer + libtorrent     |
| Usenet search & download                      | Newznab indexer + NNTP server + par2/unrar |

## How it's wired

```
                   ┌────────────────────┐
   user paste url ─┤  /playlists/import  ├─► Resolver dispatch ─► tracks in DB
                   └────────────────────┘                   │
                                                            ▼
                                            asyncio task per track
                                                            │
                                                            ▼
                                       Indexer fan-out — yt-dlp,
                                       Newznab (your NZB indexers),
                                       Torznab (your trackers)
                                                            │
                                                            ▼
                                       Score & rank by quality profile
                                                            │
                                                            ▼
                              Downloader picks itself by source kind:
                               • yt-dlp  → direct
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
