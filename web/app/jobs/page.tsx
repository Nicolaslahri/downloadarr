"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, Pause, Play, Trash2 } from "lucide-react";
import { jobsEventSource } from "@/lib/api";
import type { JobEvent } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function JobsPage() {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (paused) return;
    const es = jobsEventSource();
    if (!es) return;
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        const data: JobEvent = JSON.parse(e.data);
        setEvents((prev) => [data, ...prev].slice(0, 200));
      } catch {
        // ignore
      }
    };
    return () => {
      es.close();
      esRef.current = null;
    };
  }, [paused]);

  return (
    <PageShell
      eyebrow="live · sse"
      title="Jobs"
      description="Background activity from the worker pipeline. Streamed in real time."
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
        <div className="flex items-center gap-2 border-b border-border bg-bg-subtle/40 px-4 py-2.5 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
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

        <ul className="scrollbar-slim max-h-[70vh] overflow-y-auto font-mono text-xs">
          <AnimatePresence initial={false}>
            {events.map((e, i) => (
              <motion.li
                key={`${e.ts}-${i}`}
                layout
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-baseline gap-3 border-b border-border/60 px-4 py-2 hover:bg-bg-hover/40"
              >
                <span className="text-fg-subtle">{new Date(e.ts).toLocaleTimeString()}</span>
                <span
                  className={
                    e.level === "error"
                      ? "text-danger"
                      : e.level === "warn"
                      ? "text-warn"
                      : "text-fg-muted"
                  }
                >
                  [{e.kind}]
                </span>
                <span className="flex-1 text-fg">{e.message ?? JSON.stringify(e)}</span>
              </motion.li>
            ))}
          </AnimatePresence>
          {events.length === 0 && (
            <li className="flex items-center justify-center gap-2 py-12 text-fg-subtle">
              <Activity className="h-4 w-4 animate-pulse" />
              <span className="text-xs">waiting for events…</span>
              <span className="ml-1 inline-block h-3 w-1 animate-blink bg-fg-subtle" />
            </li>
          )}
        </ul>
      </Card>
    </PageShell>
  );
}
