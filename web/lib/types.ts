export type TrackStatus =
  | "pending"
  | "resolving"
  | "downloading"
  | "tagging"
  | "done"
  | "failed"
  | "skipped";

export interface Track {
  id: number;
  playlist_id: number;
  artist: string;
  title: string;
  album: string | null;
  duration_s: number | null;
  isrc: string | null;
  status: TrackStatus;
  file_path: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Playlist {
  id: number;
  source: string;
  source_url: string;
  name: string;
  created_at: string;
  track_count?: number;
  done_count?: number;
}

export interface PlaylistDetail extends Playlist {
  tracks: Track[];
}

export interface JobEvent {
  ts: string;
  kind: "log" | "track_update" | "playlist_update";
  message?: string;
  playlist_id?: number;
  track_id?: number;
  status?: TrackStatus;
  level?: "info" | "warn" | "error";
}

export interface UsenetIndexer {
  name: string;
  url: string;
  api_key?: string;
  api_key_set?: boolean;
}

export interface UsenetServer {
  name: string;
  host: string;
  port: number;
  ssl: boolean;
  username: string;
  password?: string;
  password_set?: boolean;
  connections: number;
}

export interface TorrentIndexer {
  name: string;
  url: string;
  api_key?: string;
  api_key_set?: boolean;
}

export interface AppSettings {
  library_path: string;
  quality_profile: "best" | "lossless_first" | "320_only";
  preferred_sources: string[];
  anthropic_api_key_set: boolean;
  spotify_configured: boolean;
  usenet_indexers: UsenetIndexer[];
  usenet_servers: UsenetServer[];
  torrent_indexers: TorrentIndexer[];
}

export interface SettingsUpdate {
  library_path?: string;
  quality_profile?: "best" | "lossless_first" | "320_only";
  preferred_sources?: string[];
  anthropic_api_key?: string;
  spotify_client_id?: string;
  spotify_client_secret?: string;
  usenet_indexers?: UsenetIndexer[];
  usenet_servers?: UsenetServer[];
  torrent_indexers?: TorrentIndexer[];
}

export interface LibraryEntry {
  path: string;
  artist: string;
  album: string | null;
  title: string;
  size_bytes: number;
  format: string;
}
