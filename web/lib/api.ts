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

  startPlaylist: (id: number, limit?: number) =>
    jfetch<{ queued: number; message?: string }>(`/playlists/${id}/start`, {
      method: "POST",
      body: JSON.stringify(limit ? { limit } : {}),
    }),

  stopPlaylist: (id: number) =>
    jfetch<{ cancelled: number }>(`/playlists/${id}/stop`, { method: "POST" }),

  deletePlaylist: (id: number) =>
    jfetch<{ ok: boolean }>(`/playlists/${id}`, { method: "DELETE" }),

  listPlaylists: () => jfetch<Playlist[]>("/playlists"),

  getPlaylist: (id: number) => jfetch<PlaylistDetail>(`/playlists/${id}`),

  retryTrack: (id: number) =>
    jfetch<Track>(`/tracks/${id}/retry`, { method: "POST" }),

  listLibrary: () => jfetch<LibraryEntry[]>("/library"),

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
};

export interface TestResult {
  ok: boolean;
  message: string;
  detail?: Record<string, unknown> | null;
}

export function jobsEventSource(): EventSource | null {
  if (typeof window === "undefined") return null;
  return new EventSource(`${API_URL}/jobs/stream`);
}
