"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Check,
  CheckSquare,
  Clock,
  Music,
  Play,
  RefreshCw,
  RotateCcw,
  Square,
  Trash2,
  X,
} from "lucide-react";
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
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [selectionInited, setSelectionInited] = useState(false);

  // Default: all pending tracks selected on first load
  if (data && !selectionInited) {
    const initial = new Set<number>();
    for (const t of data.tracks) {
      if (t.status === "pending") initial.add(t.id);
    }
    setSelected(initial);
    setSelectionInited(true);
  }

  function toggle(trackId: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(trackId)) next.delete(trackId);
      else next.add(trackId);
      return next;
    });
  }
  function selectAll() {
    if (!data) return;
    setSelected(new Set(data.tracks.filter((t) => t.status === "pending").map((t) => t.id)));
  }
  function deselectAll() {
    setSelected(new Set());
  }
  function invert() {
    if (!data) return;
    const next = new Set<number>();
    for (const t of data.tracks) {
      if (t.status === "pending" && !selected.has(t.id)) next.add(t.id);
    }
    setSelected(next);
  }

  async function retry(track: Track) {
    try {
      await api.retryTrack(track.id);
      toast.success(`Retrying "${track.title}"`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Retry failed");
    }
  }

  async function start(opts?: { onlySelected?: boolean; limit?: number }) {
    if (actioning) return;
    setActioning(true);
    try {
      const trackIds = opts?.onlySelected ? Array.from(selected) : undefined;
      const r = await api.startPlaylist(id, { trackIds, limit: opts?.limit });
      toast.success(r.message ?? `Queued ${r.queued} tracks`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Start failed");
    } finally {
      setActioning(false);
    }
  }

  async function retryFailed() {
    if (actioning) return;
    setActioning(true);
    try {
      const r = await api.retryFailed(id);
      toast.success(r.message ?? `Retrying ${r.queued} failed tracks`);
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Retry-all failed");
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

  async function deleteOneTrack(t: Track) {
    try {
      await api.deleteTrack(t.id);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(t.id);
        return next;
      });
      mutate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  const total = data?.track_count ?? 0;
  const done = data?.done_count ?? 0;
  const pending = data?.pending_count ?? 0;
  const active = data?.active_count ?? 0;
  const failed = data?.tracks.filter((t) => t.status === "failed").length ?? 0;
  const pct = total ? Math.round((done / total) * 100) : 0;

  const selectedCount = selected.size;
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
            {failed > 0 && (
              <Button variant="outline" size="sm" onClick={retryFailed} disabled={actioning}>
                <RotateCcw className="h-4 w-4" />
                Retry failed ({failed})
              </Button>
            )}
            <Button
              onClick={() => start({ onlySelected: selectedCount > 0 })}
              disabled={startDisabled || selectedCount === 0}
            >
              <Play className="h-4 w-4" />
              {selectedCount > 0 && selectedCount !== pending
                ? `Start selected (${selectedCount})`
                : `Start (${pending})`}
            </Button>
            <Button variant="outline" onClick={stop} disabled={stopDisabled}>
              <Square className="h-4 w-4" /> Stop
            </Button>
            <Button
              variant="ghost"
              onClick={destroy}
              disabled={actioning}
              className="text-danger hover:bg-danger/10"
            >
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
                  Uncheck any you don't want before pressing Start.
                  {total > 50 &&
                    " For a big playlist, try Start first 10 to verify your sources work."}
                </span>
              </div>
              {total > 50 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => start({ limit: 10 })}
                  disabled={actioning}
                >
                  Start first 10
                </Button>
              )}
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

          {pending > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-fg-muted">
              <span className="font-mono uppercase tracking-widest text-fg-subtle">
                {selectedCount}/{pending} selected
              </span>
              <button
                onClick={selectAll}
                className="rounded border border-border bg-bg-subtle/40 px-2 py-1 hover:bg-bg-hover"
              >
                Select all
              </button>
              <button
                onClick={deselectAll}
                className="rounded border border-border bg-bg-subtle/40 px-2 py-1 hover:bg-bg-hover"
              >
                Deselect all
              </button>
              <button
                onClick={invert}
                className="rounded border border-border bg-bg-subtle/40 px-2 py-1 hover:bg-bg-hover"
              >
                Invert
              </button>
            </div>
          )}

          <Card className="overflow-hidden">
            <div className="grid grid-cols-[28px_40px_1fr_140px_80px_180px_60px] gap-3 border-b border-border bg-bg-subtle/40 px-4 py-2.5 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
              <div></div>
              <div>#</div>
              <div>Track</div>
              <div>Album</div>
              <div className="text-right">
                <Clock className="ml-auto h-3 w-3" />
              </div>
              <div>Status</div>
              <div></div>
            </div>
            <ul className="scrollbar-slim max-h-[60vh] overflow-y-auto">
              <AnimatePresence initial={false}>
                {data.tracks.map((t, i) => {
                  const checkable = t.status === "pending";
                  const checked = selected.has(t.id);
                  return (
                    <motion.li
                      key={t.id}
                      layout
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, delay: Math.min(i * 0.005, 0.4) }}
                      className="group grid grid-cols-[28px_40px_1fr_140px_80px_180px_60px] items-center gap-3 border-b border-border/60 px-4 py-3 transition-colors hover:bg-bg-hover/40"
                    >
                      <div className="flex items-center justify-center">
                        {checkable ? (
                          <button
                            onClick={() => toggle(t.id)}
                            className={`flex h-4 w-4 items-center justify-center rounded border transition-colors ${
                              checked
                                ? "border-accent bg-accent text-white"
                                : "border-border bg-bg-subtle hover:border-fg-muted"
                            }`}
                            aria-label={checked ? "Deselect" : "Select"}
                          >
                            {checked && <Check className="h-3 w-3" />}
                          </button>
                        ) : (
                          <span className="font-mono text-[10px] text-fg-subtle">—</span>
                        )}
                      </div>
                      <div className="font-mono text-xs text-fg-subtle">
                        {(i + 1).toString().padStart(2, "0")}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 truncate text-sm">
                          <Music className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
                          <span className="truncate font-medium">{t.title}</span>
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 truncate text-xs text-fg-muted">
                          <span className="truncate">{t.artist}</span>
                          {t.track_no && (
                            <span className="font-mono text-[10px] text-fg-subtle">
                              · trk {t.track_no}
                            </span>
                          )}
                        </div>
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
                          <div className="w-full min-w-[160px]">
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
                            {t.quality_lossless ? " · lossless" : ""}
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
                        {t.status === "pending" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => deleteOneTrack(t)}
                            className="text-danger opacity-0 group-hover:opacity-100 hover:bg-danger/10"
                            aria-label="Delete track"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          </Card>

          {openCandidates !== null && (
            <Card className="mt-3 border-accent/30 bg-bg-subtle/40 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-accent">
                  candidates · track #{openCandidates}
                </span>
                <button
                  onClick={() => setOpenCandidates(null)}
                  className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle hover:text-fg"
                >
                  close
                </button>
              </div>
              <CandidatesPanel
                trackId={openCandidates}
                open={true}
                onClose={() => setOpenCandidates(null)}
              />
            </Card>
          )}
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
