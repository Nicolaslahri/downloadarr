"use client";

import useSWR from "swr";
import Link from "next/link";
import { motion } from "framer-motion";
import { Disc3, ArrowRight } from "lucide-react";
import type { Playlist } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";

export default function PlaylistsPage() {
  const { data, isLoading } = useSWR<Playlist[]>("/playlists", { refreshInterval: 3000 });

  return (
    <PageShell
      eyebrow="library"
      title="Playlists"
      description="Every list you've imported. Click any to inspect tracks, retry failures, or override sources."
    >
      <div className="grid gap-3">
        {isLoading &&
          [0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}

        {data?.length === 0 && !isLoading && (
          <Card className="p-12 text-center">
            <Disc3 className="mx-auto mb-4 h-10 w-10 text-fg-subtle" />
            <p className="text-sm text-fg-muted">No playlists yet.</p>
            <Link href="/" className="mt-3 inline-block text-sm text-accent hover:underline">
              Import one →
            </Link>
          </Card>
        )}

        {data?.map((p, i) => {
          const total = p.track_count ?? 0;
          const done = p.done_count ?? 0;
          const pct = total ? Math.round((done / total) * 100) : 0;
          return (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0, transition: { delay: i * 0.03 } }}
            >
              <Link
                href={`/playlists/${p.id}`}
                className="group block rounded-xl border border-border bg-bg-subtle/40 p-5 transition-all hover:border-accent/40 hover:bg-bg-hover"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                      {p.source}
                    </div>
                    <div className="truncate text-base font-medium">{p.name}</div>
                    <div className="mt-1 truncate font-mono text-[10px] text-fg-subtle">
                      {p.source_url}
                    </div>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-fg-subtle transition-all group-hover:translate-x-0.5 group-hover:text-fg" />
                </div>
                <div className="mt-4 flex items-center gap-3">
                  <Progress value={pct} className="flex-1" />
                  <span className="font-mono text-[11px] text-fg-muted">
                    {done}/{total}
                  </span>
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </PageShell>
  );
}
