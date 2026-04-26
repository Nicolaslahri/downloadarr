"use client";

import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { toast } from "sonner";
import { ChevronDown, Magnet, Newspaper, Play, Users } from "lucide-react";
import { api, type TrackCandidate } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function fmtBytes(n: number): string {
  if (!n) return "—";
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(0)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function CandidatesPanel({
  trackId,
  open,
  onClose,
}: {
  trackId: number;
  open: boolean;
  onClose: () => void;
}) {
  const { data, isLoading, mutate } = useSWR<TrackCandidate[]>(
    open ? `/tracks/${trackId}/candidates` : null
  );
  const [busyUrl, setBusyUrl] = useState<string | null>(null);

  async function pick(c: TrackCandidate) {
    setBusyUrl(c.url);
    try {
      await api.useCandidate(trackId, c);
      toast.success(`Re-queued with: ${c.title}`);
      onClose();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Use-candidate failed");
    } finally {
      setBusyUrl(null);
    }
  }

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.tr
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="bg-bg-subtle/30"
        >
          <td colSpan={6} className="px-4 py-3">
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                  Indexer candidates · top {data?.length ?? 0}
                </span>
                <button
                  onClick={() => mutate()}
                  className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle hover:text-fg"
                >
                  refresh
                </button>
              </div>
              {isLoading && <div className="text-xs text-fg-muted">loading…</div>}
              {data && data.length === 0 && (
                <div className="rounded border border-dashed border-border p-3 text-xs text-fg-muted">
                  No candidates yet — try Start to run a search.
                </div>
              )}
              <ul className="grid gap-1.5">
                {data?.map((c, i) => {
                  const Icon = c.source === "torrent" ? Magnet : Newspaper;
                  return (
                    <li
                      key={c.url + i}
                      className="grid grid-cols-[24px_1fr_70px_60px_70px_80px] items-center gap-3 rounded border border-border bg-bg-subtle/50 px-2.5 py-2 text-xs"
                    >
                      <Icon className="h-3.5 w-3.5 text-fg-subtle" />
                      <div className="min-w-0">
                        <div className="truncate font-medium">{c.title}</div>
                        <div className="truncate font-mono text-[10px] text-fg-subtle">
                          {c.indexer ?? c.source}
                        </div>
                      </div>
                      <Badge tone="ghost" className="justify-self-start">
                        {c.source}
                      </Badge>
                      <span className="font-mono text-[10px] text-fg-muted">
                        {fmtBytes(c.size ?? 0)}
                      </span>
                      <span className="flex items-center gap-1 font-mono text-[10px] text-fg-muted">
                        {c.seeders ? (
                          <>
                            <Users className="h-3 w-3" />
                            {c.seeders}
                          </>
                        ) : (
                          <span className="text-fg-subtle">
                            score {c.score.toFixed(2)}
                          </span>
                        )}
                      </span>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => pick(c)}
                        disabled={busyUrl !== null}
                        className="h-7 px-2 text-[10px]"
                      >
                        <Play className="h-3 w-3" />
                        {busyUrl === c.url ? "queuing…" : "use"}
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </motion.div>
          </td>
        </motion.tr>
      )}
    </AnimatePresence>
  );
}

export function ExpandCandidatesButton({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="flex h-7 w-7 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-bg-hover hover:text-fg"
      aria-label="Show candidates"
    >
      <ChevronDown
        className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
      />
    </button>
  );
}
