export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function importPlaylist(url: string) {
  const res = await fetch(`${API_URL}/playlists/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`Import failed: ${res.status}`);
  return res.json() as Promise<{ accepted: boolean; url: string; detail: string }>;
}
