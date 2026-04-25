"use client";

import { useState } from "react";
import { importPlaylist } from "@/lib/api";

type Result = { accepted: boolean; url: string; detail: string };

export default function Home() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await importPlaylist(url.trim());
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 py-16">
      <h1 className="mb-2 text-4xl font-bold tracking-tight">MusicDownloadarr</h1>
      <p className="mb-10 text-sm text-neutral-400">
        Paste a Spotify, Apple Music, YouTube Music, or SoundCloud playlist link —
        or a YouTube video with a tracklist.
      </p>

      <form onSubmit={onSubmit} className="flex w-full gap-2">
        <input
          type="url"
          required
          placeholder="https://open.spotify.com/playlist/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-sm outline-none focus:border-neutral-500"
          disabled={busy}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-white px-5 py-3 text-sm font-medium text-black transition disabled:opacity-50"
        >
          {busy ? "Importing…" : "Import"}
        </button>
      </form>

      {error && (
        <p className="mt-6 w-full rounded border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}
      {result && (
        <pre className="mt-6 w-full overflow-x-auto rounded border border-neutral-800 bg-neutral-950 px-4 py-3 text-xs text-neutral-300">
{JSON.stringify(result, null, 2)}
        </pre>
      )}
    </main>
  );
}
