"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Clock, Music, Play, RefreshCw, Square, Trash2 } from "lucide-react";
import { useState } from "react";
import type { PlaylistDetail, Track } from "@/lib/types";
import { api } from "@/lib/api";
import { PageShell } from "@/components/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusPill } from "@/components/status-pill";
import { TrackProgressBar } from "@/components/track-progress";
import { CandidatesPanel, ExpandCandidatesButton } from "@/components/candidate-row";

function fmtDuration(s: number | null) {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function PlaylistDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const { data, isLoading, mutate } = useSWR<PlaylistDetail>(
    Number.isFinite(id) ? `/playlists/${id}` : null,
    { refreshInterval: 2000 }
  );
  const [actioning, setActioning] = useState(false);
  const [openCandidates, setOpenCandidates] = useState<number | null>(null);

  async function retry(track: Track) {
    try {
      await api.retryTrack(track.id);
      toast.success(`Retrying "${track.title}"`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Retry failed");
    }
  }

  async function start(limit?: number) {
    if (actioning) return;
    setActioning(true);
    try {
      const r = await api.startPlaylist(id, limit);
      toast.success(r.message ?? `Queued ${r.queued} tracks`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Start failed");
    } finally {
      setActioning(false);
    }
  }

  async function stop() {
    if (actioning) return;
    setActioning(true);
    try {
      const r = await api.stopPlaylist(id);
      toast.success(`Stopped — ${r.cancelled} task(s) cancelled`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Stop failed");
    } finally {
      setActioning(false);
    }
  }

  async function destroy() {
    if (!confirm(`Delete this playlist and stop any in-flight downloads?`)) return;
    if (actioning) return;
    setActioning(true);
    try {
      await api.deletePlaylist(id);
      toast.success("Deleted");
      router.push("/playlists");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
      setActioning(false);
    }
  }

  const total = data?.track_count ?? 0;
  const done = data?.done_count ?? 0;
  const pending = data?.pending_count ?? 0;
  const active = data?.active_count ?? 0;
  const failed = data?.tracks.filter((t) => t.status === "failed").length ?? 0;
  const pct = total ? Math.round((done / total) * 100) : 0;

  const startDisabled = actioning || (pending === 0 && active === 0);
  const stopDisabled = actioning || active === 0;

  return (
    <PageShell
      eyebrow={data ? data.source : "loading…"}
      title={data?.name ?? "Loading"}
      description={data?.source_url}
      actions={
        data ? (
          <>
            {pending > 0 && total > 50 && (
              <Button variant="outline" size="sm" onClick={() => start(10)} disabled={startDisabled}>
                Start first 10
              </Button>
            )}
            <Button onClick={() => start()} disabled={startDisabled}>
              <Play className="h-4 w-4" />
              {pending > 0 ? `Start (${pending})` : "Start"}
            </Button>
            <Button variant="outline" onClick={stop} disabled={stopDisabled}>
              <Square className="h-4 w-4" /> Stop
            </Button>
            <Button variant="ghost" onClick={destroy} disabled={actioning} className="text-danger hover:bg-danger/10">
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        ) : null
      }
    >
      {isLoading && <Skeleton className="h-40 w-full" />}

      {data && (
        <>
          {pending === total && total > 0 && (
            <div className="mb-4 flex items-center gap-3 rounded-lg border border-accent/40 bg-accent/10 p-4">
              <Play className="h-4 w-4 text-accent" />
              <div className="flex-1 text-sm text-fg">
                <span className="font-semibold">{total} tracks resolved.</span>{" "}
                <span className="text-fg-muted">
                  Nothing is downloading yet — review the list and press Start when ready.
                  {total > 50 && " For a big playlist, try Start first 10 to make sure your sources are working."}
                </span>
              </div>
            </div>
          )}

          <Card className="mb-6 p-5">
            <div className="flex flex-wrap items-center gap-6">
              <Stat label="Tracks" value={total} />
              <Stat label="Pending" value={pending} accent="accent" />
              <Stat label="Active" value={active} accent="accent" />
              <Stat label="Done" value={done} accent="success" />
              <Stat label="Failed" value={failed} accent="danger" />
              <Stat label="Progress" value={`${pct}%`} accent="accent" />
              <div className="min-w-[160px] flex-1">
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
                    transition={{ duration: 0.25, delay: Math.min(i * 0.005, 0.4) }}
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
                    <div className="flex flex-col items-start gap-1">
                      <StatusPill status={t.status} />
                      {t.status === "downloading" && (t.bytes_total ?? 0) > 0 && (
                        <div className="w-full min-w-[180px]">
                          <TrackProgressBar
                            bytesDone={t.bytes_done ?? 0}
                            bytesTotal={t.bytes_total ?? 0}
                            speedKbps={t.speed_kbps ?? 0}
                          />
                        </div>
                      )}
                      {t.status === "done" && t.quality_format && (
                        <span className="font-mono text-[10px] uppercase text-fg-subtle">
                          {t.quality_format}
                          {t.quality_bitrate ? ` · ${t.quality_bitrate} kbps` : ""}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-end gap-1">
                      <ExpandCandidatesButton
                        open={openCandidates === t.id}
                        onToggle={() =>
                          setOpenCandidates(openCandidates === t.id ? null : t.id)
                        }
                      />
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
              {openCandidates !== null && (
                <li className="border-b border-border/60">
                  <div className="bg-bg-subtle/30 px-4 py-3">
                    <CandidatesInline
                      trackId={openCandidates}
                      onClose={() => setOpenCandidates(null)}
                    />
                  </div>
                </li>
              )}
            </ul>
          </Card>
        </>
      )}
    </PageShell>
  );
}

function CandidatesInline({
  trackId,
  onClose,
}: {
  trackId: number;
  onClose: () => void;
}) {
  return (
    <div>
      <CandidatesPanel trackId={trackId} open={true} onClose={onClose} />
    </div>
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
