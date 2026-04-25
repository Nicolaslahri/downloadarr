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
    jfetch<{ playlist: Playlist; queued: number }>("/playlists/import", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

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
};

export function jobsEventSource(): EventSource | null {
  if (typeof window === "undefined") return null;
  return new EventSource(`${API_URL}/jobs/stream`);
}
