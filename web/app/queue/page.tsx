"use client";

import useSWR from "swr";
import Link from "next/link";
import { Activity, Pause, Play, Tag } from "lucide-react";
import type { TrackInQueue } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { TrackCard } from "@/components/track-card";
import { Card } from "@/components/ui/card";

export default function QueuePage() {
  const { data, isLoading, mutate } = useSWR<TrackInQueue[]>("/queue", {
    refreshInterval: 2500,
    revalidateOnFocus: false,
  });

  const tracks = data ?? [];
  const downloading = tracks.filter((t) => t.status === "downloading");
  const tagging = tracks.filter((t) => t.status === "tagging");
  const resolving = tracks.filter((t) => t.status === "resolving");
  const pending = tracks.filter((t) => t.status === "pending");

  const totalBytesDone = downloading.reduce((s, t) => s + t.bytes_done, 0);
  const totalBytesTotal = downloading.reduce((s, t) => s + t.bytes_total, 0);
  const totalKbps = downloading.reduce((s, t) => s + t.speed_kbps, 0);

  return (
    <PageShell
      eyebrow="live · sse"
      title="Queue"
      description="Everything in flight, top-level. Click a row's source label to jump to its import."
    >
      <div className="mb-6 grid gap-3 sm:grid-cols-4">
        <Stat label="Downloading" value={downloading.length} icon={Play} accent="accent" />
        <Stat label="Tagging" value={tagging.length} icon={Tag} accent="accent" />
        <Stat label="Pending" value={pending.length} icon={Pause} accent="neutral" />
        <Stat
          label="Throughput"
          value={
            totalKbps > 1024
              ? `${(totalKbps / 1024).toFixed(1)} MB/s`
              : `${totalKbps} KB/s`
          }
          icon={Activity}
          accent="success"
        />
      </div>

      {downloading.length > 0 && (
        <Section title={`Downloading · ${downloading.length}`}>
          {downloading.map((t) => (
            <TrackCard key={t.id} track={t} onChange={mutate} />
          ))}
        </Section>
      )}

      {(tagging.length > 0 || resolving.length > 0) && (
        <Section title="Working on it">
          {[...resolving, ...tagging].map((t) => (
            <TrackCard key={t.id} track={t} onChange={mutate} />
          ))}
        </Section>
      )}

      {pending.length > 0 && (
        <Section title={`Pending · ${pending.length}`} muted>
          {pending.slice(0, 30).map((t) => (
            <TrackCard key={t.id} track={t} onChange={mutate} />
          ))}
          {pending.length > 30 && (
            <p className="px-2 text-xs text-fg-subtle">
              + {pending.length - 30} more pending — they'll start as slots free up.
            </p>
          )}
        </Section>
      )}

      {!isLoading && tracks.length === 0 && (
        <Card className="p-12 text-center">
          <Activity className="mx-auto mb-4 h-10 w-10 text-fg-subtle" />
          <p className="text-sm text-fg-muted">Nothing in the queue right now.</p>
          <Link
            href="/"
            className="mt-3 inline-block text-sm text-accent hover:underline"
          >
            Add something →
          </Link>
        </Card>
      )}
    </PageShell>
  );
}

function Section({
  title,
  children,
  muted,
}: {
  title: string;
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <section className="mb-8">
      <h2
        className={`mb-3 font-mono text-[10px] uppercase tracking-widest ${
          muted ? "text-fg-subtle" : "text-fg-muted"
        }`}
      >
        {title}
      </h2>
      <div className="grid gap-3">{children}</div>
    </section>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  accent: "neutral" | "accent" | "success";
}) {
  const tone =
    accent === "accent"
      ? "text-accent border-accent/30 bg-accent/5"
      : accent === "success"
      ? "text-success border-success/30 bg-success/5"
      : "text-fg border-border bg-bg-subtle/40";
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${tone}`}
    >
      <Icon className="h-5 w-5" />
      <div className="min-w-0">
        <div className="font-mono text-[10px] uppercase tracking-widest opacity-70">
          {label}
        </div>
        <div className="text-xl font-semibold tracking-tight">{value}</div>
      </div>
    </div>
  );
}
