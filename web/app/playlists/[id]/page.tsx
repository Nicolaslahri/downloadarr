"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Clock, Music, RefreshCw } from "lucide-react";
import type { PlaylistDetail, Track } from "@/lib/types";
import { api } from "@/lib/api";
import { PageShell } from "@/components/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusPill } from "@/components/status-pill";

function fmtDuration(s: number | null) {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function PlaylistDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { data, isLoading, mutate } = useSWR<PlaylistDetail>(
    Number.isFinite(id) ? `/playlists/${id}` : null,
    { refreshInterval: 2000 }
  );

  async function retry(track: Track) {
    try {
      await api.retryTrack(track.id);
      toast.success(`Retrying "${track.title}"`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Retry failed");
    }
  }

  const total = data?.tracks.length ?? 0;
  const done = data?.tracks.filter((t) => t.status === "done").length ?? 0;
  const failed = data?.tracks.filter((t) => t.status === "failed").length ?? 0;
  const pct = total ? Math.round((done / total) * 100) : 0;

  return (
    <PageShell
      eyebrow={data ? data.source : "loading…"}
      title={data?.name ?? "Loading"}
      description={data?.source_url}
    >
      {isLoading && <Skeleton className="h-40 w-full" />}

      {data && (
        <>
          <Card className="mb-6 p-5">
            <div className="flex items-center gap-6">
              <Stat label="Tracks" value={total} />
              <Stat label="Done" value={done} accent="success" />
              <Stat label="Failed" value={failed} accent="danger" />
              <Stat label="Progress" value={`${pct}%`} accent="accent" />
              <div className="flex-1">
                <Progress value={pct} />
              </div>
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="grid grid-cols-[40px_1fr_140px_80px_120px_80px] gap-3 border-b border-border bg-bg-subtle/40 px-4 py-2.5 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
              <div>#</div>
              <div>Track</div>
              <div>Album</div>
              <div className="text-right"><Clock className="ml-auto h-3 w-3" /></div>
              <div>Status</div>
              <div></div>
            </div>
            <ul className="scrollbar-slim max-h-[60vh] overflow-y-auto">
              <AnimatePresence initial={false}>
                {data.tracks.map((t, i) => (
                  <motion.li
                    key={t.id}
                    layout
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: Math.min(i * 0.015, 0.4) }}
                    className="group grid grid-cols-[40px_1fr_140px_80px_120px_80px] items-center gap-3 border-b border-border/60 px-4 py-3 transition-colors hover:bg-bg-hover/40"
                  >
                    <div className="font-mono text-xs text-fg-subtle">
                      {(i + 1).toString().padStart(2, "0")}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 truncate text-sm">
                        <Music className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
                        <span className="truncate font-medium">{t.title}</span>
                      </div>
                      <div className="mt-0.5 truncate text-xs text-fg-muted">{t.artist}</div>
                      {t.error && (
                        <div className="mt-0.5 truncate font-mono text-[10px] text-danger">
                          {t.error}
                        </div>
                      )}
                    </div>
                    <div className="truncate text-xs text-fg-muted">{t.album ?? "—"}</div>
                    <div className="text-right font-mono text-xs text-fg-muted">
                      {fmtDuration(t.duration_s)}
                    </div>
                    <div>
                      <StatusPill status={t.status} />
                    </div>
                    <div className="flex justify-end">
                      {(t.status === "failed" || t.status === "done") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => retry(t)}
                          className="opacity-0 group-hover:opacity-100"
                        >
                          <RefreshCw className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </Card>
        </>
      )}
    </PageShell>
  );
}

function Stat({
  label,
  value,
  accent = "neutral",
}: {
  label: string;
  value: string | number;
  accent?: "neutral" | "success" | "danger" | "accent";
}) {
  const tone =
    accent === "success" ? "text-success"
    : accent === "danger" ? "text-danger"
    : accent === "accent" ? "text-accent"
    : "text-fg";
  return (
    <div className="leading-tight">
      <div className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">{label}</div>
      <div className={`text-2xl font-semibold tracking-tight ${tone}`}>{value}</div>
    </div>
  );
}
