"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, Pause, Play, Trash2 } from "lucide-react";
import { jobsEventSource } from "@/lib/api";
import type { JobEvent } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function JobsPage() {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [follow, setFollow] = useState(true);
  const esRef = useRef<EventSource | null>(null);
  const containerRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (paused) return;
    const es = jobsEventSource();
    if (!es) return;
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        const data: JobEvent = JSON.parse(e.data);
        setEvents((prev) => [data, ...prev].slice(0, 500));
      } catch {
        // ignore
      }
    };
    return () => {
      es.close();
      esRef.current = null;
    };
  }, [paused]);

  // Follow mode: keep scroll at the top so newest events stay visible.
  useEffect(() => {
    if (!follow) return;
    containerRef.current?.scrollTo({ top: 0 });
  }, [events, follow]);

  return (
    <PageShell
      eyebrow="dev · raw stream"
      title="Activity log"
      description="Verbose backend events. The Queue tab is the better place to watch downloads — this view is for debugging."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={() => setPaused((p) => !p)}>
            {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setEvents([])}>
            <Trash2 className="h-3.5 w-3.5" /> Clear
          </Button>
        </>
      }
    >
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-border bg-bg-subtle/40 px-4 py-2.5 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
          <div className="flex items-center gap-2">
            <span className="relative flex h-1.5 w-1.5">
              {!paused && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              )}
              <span
                className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
                  paused ? "bg-fg-subtle" : "bg-success"
                }`}
              />
            </span>
            {paused ? "stream paused" : "stream live"} · {events.length} events
          </div>
          <label className="flex cursor-pointer items-center gap-1.5 text-fg-subtle hover:text-fg">
            <input
              type="checkbox"
              checked={follow}
              onChange={(e) => setFollow(e.target.checked)}
              className="h-3 w-3 accent-accent"
            />
            follow
          </label>
        </div>

        <ul
          ref={containerRef}
          className="scrollbar-slim max-h-[70vh] overflow-y-auto font-mono text-xs"
        >
          {events.map((e, i) => (
            <li
              key={`${e.ts}-${i}`}
              className="flex items-baseline gap-3 border-b border-border/40 px-4 py-1.5 hover:bg-bg-hover/30"
            >
              <span className="shrink-0 text-fg-subtle">
                {new Date(e.ts).toLocaleTimeString()}
              </span>
              <span
                className={`shrink-0 ${
                  e.level === "error"
                    ? "text-danger"
                    : e.level === "warn"
                    ? "text-warn"
                    : "text-fg-muted"
                }`}
              >
                [{e.kind}]
              </span>
              <span className="flex-1 break-all text-fg">
                {e.message ?? JSON.stringify(e)}
              </span>
            </li>
          ))}
          {events.length === 0 && (
            <li className="flex items-center justify-center gap-2 py-12 text-fg-subtle">
              <Activity className="h-4 w-4 animate-pulse" />
              <span className="text-xs">waiting for events…</span>
            </li>
          )}
        </ul>
      </Card>
    </PageShell>
  );
}
