# MusicDownloadarr

Self-hosted music librarian. Paste a playlist link from Spotify / Apple Music / YouTube Music / SoundCloud, or a "Top 100" YouTube video, and the app builds your offline tagged library by pulling from yt-dlp, Usenet (NZBHydra/SABnzbd), torrents (Prowlarr/qBittorrent), or spotdl/zotify — whichever your quality profile prefers.

## Quick start (skeleton)

```bash
cp .env.example .env
docker compose up -d --build
```

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

The current skeleton wires up FastAPI + Arq worker + Postgres + Redis + Next.js paste bar. The `/playlists/import` endpoint accepts a URL but resolver dispatch is the next milestone.

## Status

Built incrementally per [the plan](https://). See the approved plan at `~/.claude/plans/so-i-have-a-binary-swing.md`.
