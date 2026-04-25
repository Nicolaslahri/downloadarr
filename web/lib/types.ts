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

export interface AppSettings {
  library_path: string;
  quality_profile: "best" | "lossless_first" | "320_only";
  preferred_sources: string[];
  anthropic_api_key_set: boolean;
  spotify_configured: boolean;
  prowlarr_configured: boolean;
  nzbhydra_configured: boolean;
  qbt_configured: boolean;
  sab_configured: boolean;
}

export interface SettingsUpdate {
  library_path?: string;
  quality_profile?: "best" | "lossless_first" | "320_only";
  preferred_sources?: string[];
  anthropic_api_key?: string;
  spotify_client_id?: string;
  spotify_client_secret?: string;
  prowlarr_url?: string;
  prowlarr_api_key?: string;
  nzbhydra_url?: string;
  nzbhydra_api_key?: string;
  qbt_url?: string;
  qbt_user?: string;
  qbt_pass?: string;
  sab_url?: string;
  sab_api_key?: string;
}

export interface LibraryEntry {
  path: string;
  artist: string;
  album: string | null;
  title: string;
  size_bytes: number;
  format: string;
}
