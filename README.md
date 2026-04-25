# MusicDownloadarr

Self-hosted music librarian. Paste any Spotify, Apple Music, YouTube Music, or SoundCloud playlist link — or a "Top 100" YouTube video — and the app extracts the tracklist (LLM-first, Whisper fallback), then downloads each track from a pluggable mix of sources (yt-dlp, Usenet, torrents, spotdl) into a tagged offline library.

## Run locally (zero-infra dev)

The backend defaults to a local SQLite file at `backend/.data/musicdl.db`, so you can run both halves without Docker.

### Backend (FastAPI on :8000)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend (Next.js on :3000)

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000.

The top bar shows a green dot once it can reach the API. Visit `Settings` to wire up your indexers, download clients, Anthropic key (for AI tracklist extraction), and Spotify credentials.

## What works out of the box

| Feature                                       | Needs                            |
| --------------------------------------------- | -------------------------------- |
| YouTube / YouTube Music playlist import       | nothing                          |
| SoundCloud playlist import                    | nothing                          |
| yt-dlp track download (m4a)                   | `ffmpeg` on PATH                 |
| Apple Music playlist (best-effort scrape)     | nothing                          |
| Spotify playlist import                       | Spotify client id + secret       |
| AI tracklist from a YouTube video             | Anthropic API key                |
| Torrent search & download (Prowlarr → qBit)   | Prowlarr + qBittorrent           |
| Usenet search & download (NZBHydra → SAB)     | NZBHydra2 + SABnzbd              |

## How it's wired

```
                   ┌────────────────────┐
   user paste url ─┤  /playlists/import  ├─► Resolver dispatch ─► tracks in DB
                   └────────────────────┘                   │
                                                            ▼
                                            asyncio task per track
                                                            │
                                                            ▼
                                       Indexer fan-out (yt-dlp,
                                       Prowlarr, NZBHydra, spotdl)
                                                            │
                                                            ▼
                                       Score & rank by quality profile
                                                            │
                                                            ▼
                              Downloader (yt-dlp / qBit / SAB)
                                                            │
                                                            ▼
                                       mutagen tag → organize into library
```

Resolvers, Indexers, and Downloaders are all `Protocol`-based — adding a new playlist source or download backend means dropping one file in the right folder and registering it.

## Roadmap

The first commit's plan is at `docs/plan.md` (see also `~/.claude/plans/`). Live work tracked in commit history.

- [x] Skeleton + Protocol-based extension points
- [x] YouTube / YT Music / SoundCloud resolvers
- [x] Spotify resolver (with creds)
- [x] Apple Music resolver (best-effort scrape)
- [x] AI tracklist extraction from YouTube videos
- [x] yt-dlp end-to-end download + tag + organize
- [x] Settings UI (indexers, clients, AI, quality profile)
- [x] Live job stream over SSE
- [ ] qBittorrent / SABnzbd downloader implementations
- [ ] Whisper fallback for videos without descriptions
- [ ] MusicBrainz cover art lookup
- [ ] Quality-profile per-source override
