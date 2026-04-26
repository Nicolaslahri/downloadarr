"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
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
      toast.success(`Resolved "${r.playlist.name}" — ${r.track_count} tracks. Review before starting.`);
      setUrl("");
      mutate("/playlists");
      router.push(`/playlists/${r.playlist.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      eyebrow="paste · resolve · review · download"
      title="Where streaming meets your hard drive."
      description="Paste any Spotify, Apple Music, YouTube Music, or SoundCloud playlist (or a YouTube video tracklist) — we resolve it to artist/title pairs so you can review the list before queuing HQ downloads from your Usenet and torrent indexers."
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
                <Loader2 className="h-4 w-4 animate-spin" /> Resolving
              </>
            ) : (
              <>
                Resolve <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </Card>

      <p className="mt-3 px-1 text-[11px] text-fg-subtle">
        Resolving builds a tracklist preview only — no downloads start until you press
        <span className="mx-1 rounded bg-bg-hover px-1 py-0.5 font-mono text-[10px]">Start</span>
        on the playlist page.
      </p>

      {recents && recents.length > 0 && (
        <Link
          href="/queue"
          className="mt-8 flex items-center justify-between rounded-xl border border-accent/30 bg-accent/5 px-5 py-4 transition-colors hover:bg-accent/10"
        >
          <div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-accent">
              Live activity
            </div>
            <div className="mt-0.5 text-sm text-fg">
              {recents.length} import{recents.length === 1 ? "" : "s"} in flight — open the Queue to watch downloads.
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-accent" />
        </Link>
      )}
    </PageShell>
  );
}
