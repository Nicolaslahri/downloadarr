"use client";

import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { toast } from "sonner";
import { ChevronDown, Magnet, Newspaper, Play, Users, X } from "lucide-react";
import { api, type TrackCandidate } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";

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
  const [showRejected, setShowRejected] = useState(false);

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

  const accepted = (data ?? []).filter((c) => c.accepted !== false);
  const rejected = (data ?? []).filter((c) => c.accepted === false);

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="overflow-hidden"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
              {accepted.length} accepted · {rejected.length} filtered
            </span>
            <button
              onClick={() => mutate()}
              className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle hover:text-fg"
            >
              refresh
            </button>
          </div>
          {isLoading && <div className="text-xs text-fg-muted">loading…</div>}

          {accepted.length === 0 && rejected.length === 0 && (
            <div className="rounded border border-dashed border-border p-3 text-xs text-fg-muted">
              No candidates yet — Start to run a search.
            </div>
          )}

          {accepted.length > 0 && (
            <ul className="grid gap-1.5">
              {accepted.map((c, i) => (
                <CandidateLi
                  key={c.url + i}
                  c={c}
                  busy={busyUrl !== null}
                  busyMine={busyUrl === c.url}
                  onPick={pick}
                />
              ))}
            </ul>
          )}

          {rejected.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setShowRejected((v) => !v)}
                className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle hover:text-fg"
              >
                {showRejected ? "▾" : "▸"} {rejected.length} filtered out — show
              </button>
              {showRejected && (
                <ul className="mt-2 grid gap-1.5">
                  {rejected.map((c, i) => (
                    <CandidateLi
                      key={c.url + i}
                      c={c}
                      busy={busyUrl !== null}
                      busyMine={busyUrl === c.url}
                      onPick={pick}
                      rejected
                    />
                  ))}
                </ul>
              )}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function CandidateLi({
  c,
  busy,
  busyMine,
  onPick,
  rejected,
}: {
  c: TrackCandidate;
  busy: boolean;
  busyMine: boolean;
  onPick: (c: TrackCandidate) => void;
  rejected?: boolean;
}) {
  const Icon = c.source === "torrent" ? Magnet : Newspaper;
  const reasons = c.reject_reasons ?? [];
  const reasonText = reasons.map((r) => `${r.spec}: ${r.reason}`).join("\n");

  return (
    <li
      className={`grid grid-cols-[24px_1fr_70px_60px_70px_80px] items-center gap-3 rounded border px-2.5 py-2 text-xs transition-colors ${
        rejected
          ? "border-border/60 bg-bg-subtle/20 opacity-70"
          : "border-border bg-bg-subtle/50 hover:bg-bg-hover/50"
      }`}
    >
      <Icon className={`h-3.5 w-3.5 ${rejected ? "text-fg-subtle" : "text-fg-muted"}`} />
      <div className="min-w-0">
        <div
          className={`truncate font-medium ${rejected ? "text-fg-muted line-through decoration-danger/40" : ""}`}
        >
          {c.title}
        </div>
        <div className="truncate font-mono text-[10px] text-fg-subtle">
          {c.indexer ?? c.source}
          {rejected && reasons.length > 0 && (
            <span className="ml-2 text-warn">
              · rejected: {reasons[0].reason}
              {reasons.length > 1 ? ` (+${reasons.length - 1})` : ""}
            </span>
          )}
        </div>
      </div>
      <Badge tone={rejected ? "warn" : "ghost"} className="justify-self-start">
        {c.source}
      </Badge>
      <span className="font-mono text-[10px] text-fg-muted">{fmtBytes(c.size ?? 0)}</span>
      <span className="flex items-center gap-1 font-mono text-[10px] text-fg-muted">
        {c.seeders ? (
          <>
            <Users className="h-3 w-3" />
            {c.seeders}
          </>
        ) : (
          <span className="text-fg-subtle">{c.score.toFixed(2)}</span>
        )}
      </span>
      {rejected ? (
        <Tooltip content={<div className="max-w-xs whitespace-pre-line text-xs">{reasonText}</div>}>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPick(c)}
            disabled={busy}
            className="h-7 px-2 text-[10px]"
            title="Override filter and use this anyway"
          >
            {busyMine ? "queuing…" : "force"}
          </Button>
        </Tooltip>
      ) : (
        <Button
          size="sm"
          variant="outline"
          onClick={() => onPick(c)}
          disabled={busy}
          className="h-7 px-2 text-[10px]"
        >
          <Play className="h-3 w-3" />
          {busyMine ? "queuing…" : "use"}
        </Button>
      )}
    </li>
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
