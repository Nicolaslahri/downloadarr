"use client";

import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw, Search, X } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { TrackInQueue } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { StatusPill } from "@/components/status-pill";
import { ManualSearchDialog } from "@/components/manual-search";

function fmtDuration(s: number | null | undefined): string {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function fmtBytes(n: number): string {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function fmtSpeed(kbps: number): string {
  if (!kbps) return "—";
  if (kbps < 1024) return `${kbps} KB/s`;
  return `${(kbps / 1024).toFixed(1)} MB/s`;
}

function fmtEta(bytesLeft: number, kbps: number): string {
  if (!kbps || !bytesLeft) return "—";
  const seconds = Math.round(bytesLeft / 1024 / kbps);
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600)
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`;
}

function _initials(track: TrackInQueue): string {
  const a = (track.artist || "?").trim().charAt(0).toUpperCase();
  const t = (track.title || "?").trim().charAt(0).toUpperCase();
  return `${a}${t}`;
}

function ArtPlaceholder({ track }: { track: TrackInQueue }) {
  const seed = `${track.artist}${track.title}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  const hue = Math.abs(hash) % 360;
  return (
    <div
      className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md ring-1 ring-white/5"
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 45% 28%), hsl(${(hue + 60) % 360} 50% 18%))`,
      }}
    >
      <span className="font-mono text-xs font-bold text-white/90">{_initials(track)}</span>
    </div>
  );
}

export function TrackCard({
  track,
  onChange,
}: {
  track: TrackInQueue;
  onChange?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  async function retry() {
    if (busy) return;
    setBusy(true);
    try {
      await api.retryTrack(track.id);
      toast.success(`Retrying "${track.title}"`);
      onChange?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setBusy(false);
    }
  }

  async function drop() {
    if (busy) return;
    if (!confirm(`Remove "${track.artist} – ${track.title}"?`)) return;
    setBusy(true);
    try {
      await api.deleteTrack(track.id);
      toast.success("Removed");
      onChange?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  const downloading = track.status === "downloading" && track.bytes_total > 0;
  const pct = downloading ? Math.min(100, (track.bytes_done / track.bytes_total) * 100) : 0;
  const left = downloading ? Math.max(0, track.bytes_total - track.bytes_done) : 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="group rounded-xl border border-border bg-bg-subtle/40 p-4 transition-colors hover:border-border-strong"
    >
      <div className="flex items-start gap-4">
        <ArtPlaceholder track={track} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <h3 className="truncate text-base font-semibold tracking-tight">
              {track.title}
            </h3>
            {track.track_no && (
              <span className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                trk {track.track_no}
              </span>
            )}
            {track.year && (
              <span className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                {track.year}
              </span>
            )}
            <span className="font-mono text-[11px] text-fg-muted">
              · {fmtDuration(track.duration_s)}
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-fg-muted">
            <span className="truncate font-medium">{track.artist}</span>
            {track.album && <span className="truncate text-fg-subtle">· {track.album}</span>}
          </div>
          <div className="mt-1 flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
            <Link
              href={`/playlists/${track.playlist_id}`}
              className="truncate transition-colors hover:text-fg"
            >
              {track.playlist_source} · {track.playlist_name}
            </Link>
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          <StatusPill status={track.status} />
          {track.status === "done" && track.quality_format && (
            <Badge tone="success" className="font-mono">
              {track.quality_format.toUpperCase()}
              {track.quality_bitrate ? ` · ${track.quality_bitrate} kbps` : ""}
              {track.quality_lossless ? " · lossless" : ""}
            </Badge>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setSearchOpen(true)}
            disabled={busy}
            aria-label="Manual search"
            title="Manual search"
          >
            <Search className="h-3.5 w-3.5" />
          </Button>
          {(track.status === "failed" || track.status === "done") && (
            <Button
              size="icon"
              variant="ghost"
              onClick={retry}
              disabled={busy}
              aria-label="Retry"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={drop}
            disabled={busy}
            aria-label="Remove"
            className="text-fg-subtle hover:bg-danger/10 hover:text-danger"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {downloading && (
        <div className="mt-3 grid gap-1.5">
          <Progress value={pct} className="h-1.5" />
          <div className="flex justify-between gap-2 font-mono text-[11px] text-fg-muted">
            <span>
              {fmtBytes(track.bytes_done)} / {fmtBytes(track.bytes_total)}
            </span>
            <span>{fmtSpeed(track.speed_kbps)}</span>
            <span>ETA {fmtEta(left, track.speed_kbps)}</span>
            <span className="text-fg-subtle">{pct.toFixed(0)}%</span>
          </div>
        </div>
      )}

      {track.error && track.status === "failed" && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span className="leading-relaxed">{track.error}</span>
        </div>
      )}

      <ManualSearchDialog
        trackId={track.id}
        initialQuery={`${track.artist} ${track.title}`.trim()}
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onPicked={() => onChange?.()}
      />
    </motion.div>
  );
}
