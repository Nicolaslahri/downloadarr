"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SourceDetector } from "@/components/source-detector";
import { detectSource } from "@/lib/source-detect";
import { api } from "@/lib/api";
import type { Playlist } from "@/lib/types";
import { PageShell } from "@/components/page-shell";

export default function Home() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const detected = detectSource(url);

  const { data: recents } = useSWR<Playlist[]>("/playlists", { refreshInterval: 4000 });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true);
    try {
      const r = await api.importPlaylist(url.trim());
      toast.success(`Imported "${r.playlist.name}" — ${r.queued} tracks queued`);
      setUrl("");
      mutate("/playlists");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      eyebrow="paste · resolve · download"
      title="Where streaming meets your hard drive."
      description="Paste any Spotify, Apple Music, YouTube Music, or SoundCloud playlist (or a YouTube video tracklist) — we resolve it to artist/title pairs, then search your configured Usenet and torrent indexers for HQ audio (FLAC / 320). YouTube is for tracklisting, never for the actual download."
    >
      <Card className="relative overflow-hidden p-1.5">
        <div className="pointer-events-none absolute inset-0 bg-grid-fade opacity-60" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" />
        <form onSubmit={onSubmit} className="relative flex items-center gap-2 p-2">
          <div className="flex flex-1 items-center gap-3 px-3">
            <Sparkles className="h-4 w-4 shrink-0 text-accent" />
            <Input
              type="url"
              inputMode="url"
              required
              autoFocus
              placeholder="https://open.spotify.com/playlist/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={busy}
              className="border-0 bg-transparent px-0 text-base focus-visible:ring-0"
            />
          </div>
          <SourceDetector source={detected} />
          <Button type="submit" disabled={busy || !url.trim()} size="lg" className="ml-2">
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Importing
              </>
            ) : (
              <>
                Import <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </Card>

      <div className="mt-3 flex flex-wrap items-center gap-2 px-1 text-[11px] text-fg-subtle">
        <span className="font-mono uppercase tracking-widest">Try</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.url}
            onClick={() => setUrl(ex.url)}
            className="rounded-full border border-border bg-bg-subtle/50 px-2.5 py-1 font-mono text-[10px] text-fg-muted transition-colors hover:border-accent/60 hover:text-fg"
          >
            {ex.label}
          </button>
        ))}
      </div>

      <section className="mt-12">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-fg-muted">
            Recent imports
          </h2>
          <Link href="/playlists" className="text-xs text-fg-muted transition-colors hover:text-fg">
            View all →
          </Link>
        </div>

        <div className="grid gap-3">
          <AnimatePresence initial={false}>
            {(recents ?? []).slice(0, 6).map((p, i) => (
              <motion.div
                key={p.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0, transition: { delay: i * 0.04 } }}
                exit={{ opacity: 0, y: -8 }}
              >
                <Link
                  href={`/playlists/${p.id}`}
                  className="group flex items-center gap-4 rounded-xl border border-border bg-bg-subtle/40 px-4 py-3 transition-all hover:border-accent/40 hover:bg-bg-hover"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-accent/30 to-success/20 ring-1 ring-white/5">
                    <Sparkles className="h-4 w-4 text-accent-glow" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-fg">{p.name}</div>
                    <div className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                      {p.source}
                      {p.track_count != null && ` · ${p.done_count ?? 0}/${p.track_count} done`}
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-fg-subtle transition-all group-hover:translate-x-0.5 group-hover:text-fg" />
                </Link>
              </motion.div>
            ))}
            {recents && recents.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-xl border border-dashed border-border bg-bg-subtle/30 p-8 text-center"
              >
                <p className="text-sm text-fg-muted">
                  Nothing imported yet. Paste a link above to get started.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>
    </PageShell>
  );
}

const EXAMPLES = [
  { label: "Spotify playlist", url: "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" },
  { label: "YT Music", url: "https://music.youtube.com/playlist?list=PL4fGSI1pDJn5kI81J1fYWK5eZRl1zJ5kM" },
  { label: "YouTube video", url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
];
