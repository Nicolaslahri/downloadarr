import type {
  AppSettings,
  LibraryEntry,
  Playlist,
  PlaylistDetail,
  SettingsUpdate,
  Track,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function jfetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const fetcher = (path: string) => jfetch(path);

export const api = {
  health: () => jfetch<{ status: string }>("/health"),

  importPlaylist: (url: string) =>
    jfetch<{ playlist: Playlist; track_count: number }>("/playlists/import", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  startPlaylist: (id: number, opts?: { limit?: number; trackIds?: number[] }) =>
    jfetch<{ queued: number; message?: string }>(`/playlists/${id}/start`, {
      method: "POST",
      body: JSON.stringify({
        ...(opts?.limit ? { limit: opts.limit } : {}),
        ...(opts?.trackIds ? { track_ids: opts.trackIds } : {}),
      }),
    }),

  retryFailed: (id: number) =>
    jfetch<{ queued: number; message?: string }>(`/playlists/${id}/retry-failed`, {
      method: "POST",
    }),

  stopPlaylist: (id: number) =>
    jfetch<{ cancelled: number }>(`/playlists/${id}/stop`, { method: "POST" }),

  deletePlaylist: (id: number) =>
    jfetch<{ ok: boolean }>(`/playlists/${id}`, { method: "DELETE" }),

  deleteTrack: (id: number) =>
    jfetch<{ ok: boolean }>(`/tracks/${id}`, { method: "DELETE" }),

  listPlaylists: () => jfetch<Playlist[]>("/playlists"),

  getPlaylist: (id: number) => jfetch<PlaylistDetail>(`/playlists/${id}`),

  retryTrack: (id: number) =>
    jfetch<Track>(`/tracks/${id}/retry`, { method: "POST" }),

  getCandidates: (id: number) =>
    jfetch<TrackCandidate[]>(`/tracks/${id}/candidates`),

  useCandidate: (id: number, body: TrackCandidate) =>
    jfetch<{ ok: boolean }>(`/tracks/${id}/use-candidate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  manualSearch: (id: number, query: string) =>
    jfetch<TrackCandidate[]>(`/tracks/${id}/manual-search`, {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  listLibrary: () => jfetch<LibraryEntry[]>("/library"),

  libraryInfo: () =>
    jfetch<{
      library_path: string;
      library_exists: boolean;
      library_writable: boolean;
      library_track_count: number;
      library_size_bytes: number;
      downloads_path: string;
      downloads_exists: boolean;
      downloads_size_bytes: number;
      free_bytes: number;
    }>("/library/info"),

  cleanupWorkspace: () =>
    jfetch<{ removed_dirs: number; removed_files: number; freed_bytes: number }>(
      "/library/cleanup",
      { method: "POST" }
    ),

  getQueue: () => jfetch<import("./types").TrackInQueue[]>("/queue"),

  getHistory: (limit = 200) =>
    jfetch<import("./types").TrackInQueue[]>(`/history?limit=${limit}`),

  getSettings: () => jfetch<AppSettings>("/settings"),

  updateSettings: (patch: SettingsUpdate) =>
    jfetch<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  testUsenetIndexer: (body: { name?: string; url: string; api_key?: string }) =>
    jfetch<TestResult>("/settings/test/usenet-indexer", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testUsenetServer: (body: {
    name?: string;
    host: string;
    port: number;
    ssl: boolean;
    username?: string;
    password?: string;
  }) =>
    jfetch<TestResult>("/settings/test/usenet-server", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testTorrentIndexer: (body: { name?: string; url: string; api_key?: string }) =>
    jfetch<TestResult>("/settings/test/torrent-indexer", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testAnthropic: (body: { api_key?: string }) =>
    jfetch<TestResult>("/settings/test/anthropic", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testSpotify: (body: { client_id?: string; client_secret?: string }) =>
    jfetch<TestResult>("/settings/test/spotify", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getTools: () => jfetch<ToolsStatus>("/settings/tools"),

  installTools: (force = false) =>
    jfetch<ToolsStatus>(`/settings/tools/install${force ? "?force=true" : ""}`, {
      method: "POST",
    }),

  uploadTool: async (file: File): Promise<{ ok: boolean; name: string; path: string; size: number }> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_URL}/settings/tools/upload`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
    }
    return res.json();
  },
};

export interface TestResult {
  ok: boolean;
  message: string;
  detail?: Record<string, unknown> | null;
}

export interface ToolStatus {
  name: string;
  available: boolean;
  path: string | null;
  auto_managed: boolean;
  error?: string;
}

export type ToolsStatus = Record<"par2" | "unrar", ToolStatus>;

export interface TrackCandidate {
  source: "nzb" | "torrent" | "ytdlp" | "spotdl" | "zotify" | string;
  url: string;
  title: string;
  score: number;
  size?: number;
  indexer?: string;
  seeders?: number;
  format?: string;
  bitrate_kbps?: number;
  accepted?: boolean;
  reject_reasons?: { spec: string; reason: string }[];
}

export function jobsEventSource(): EventSource | null {
  if (typeof window === "undefined") return null;
  return new EventSource(`${API_URL}/jobs/stream`);
}
