"use client";

import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import Link from "next/link";
import { Check, History as HistoryIcon, X } from "lucide-react";
import type { TrackInQueue, TrackStatus } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { TrackCard } from "@/components/track-card";
import { Card } from "@/components/ui/card";

const FILTERS: { id: "all" | TrackStatus; label: string }[] = [
  { id: "all", label: "All" },
  { id: "done", label: "Completed" },
  { id: "failed", label: "Failed" },
  { id: "skipped", label: "Skipped" },
];

export default function HistoryPage() {
  const { data, isLoading, mutate } = useSWR<TrackInQueue[]>("/history?limit=300", {
    refreshInterval: 5000,
  });
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");

  const tracks = (data ?? []).filter((t) => filter === "all" || t.status === filter);
  const counts = {
    done: data?.filter((t) => t.status === "done").length ?? 0,
    failed: data?.filter((t) => t.status === "failed").length ?? 0,
    skipped: data?.filter((t) => t.status === "skipped").length ?? 0,
  };

  return (
    <PageShell
      eyebrow="archive"
      title="History"
      description="Past activity — completed, failed, or skipped tracks. Click into any to retry or open its import."
    >
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <Stat label="Completed" value={counts.done} icon={Check} accent="success" />
        <Stat label="Failed" value={counts.failed} icon={X} accent="danger" />
        <Stat label="Skipped" value={counts.skipped} icon={HistoryIcon} accent="neutral" />
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-widest transition-colors ${
              filter === f.id
                ? "border-accent bg-accent/10 text-accent"
                : "border-border bg-bg-subtle/40 text-fg-muted hover:bg-bg-hover"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <Card className="p-12 text-center text-sm text-fg-muted">Loading…</Card>
      )}

      {!isLoading && tracks.length === 0 && (
        <Card className="p-12 text-center">
          <HistoryIcon className="mx-auto mb-4 h-10 w-10 text-fg-subtle" />
          <p className="text-sm text-fg-muted">Nothing here yet.</p>
          <Link
            href="/"
            className="mt-3 inline-block text-sm text-accent hover:underline"
          >
            Import something →
          </Link>
        </Card>
      )}

      <div className="grid gap-3">
        {tracks.map((t) => (
          <TrackCard key={t.id} track={t} onChange={mutate} />
        ))}
      </div>
    </PageShell>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  accent: "neutral" | "success" | "danger";
}) {
  const tone =
    accent === "success"
      ? "text-success border-success/30 bg-success/5"
      : accent === "danger"
      ? "text-danger border-danger/30 bg-danger/5"
      : "text-fg border-border bg-bg-subtle/40";
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-center gap-3 rounded-lg border p-3 ${tone}`}
    >
      <Icon className="h-5 w-5" />
      <div>
        <div className="font-mono text-[10px] uppercase tracking-widest opacity-70">
          {label}
        </div>
        <div className="text-xl font-semibold tracking-tight">{value}</div>
      </div>
    </motion.div>
  );
}
