"use client";

import useSWR from "swr";
import { Github } from "lucide-react";
import { fetcher } from "@/lib/api";

export function TopBar() {
  const { data, error } = useSWR<{ status: string }>("/health", fetcher, {
    refreshInterval: 5000,
    shouldRetryOnError: true,
  });

  const ok = !error && data?.status === "ok";

  return (
    <div className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-border bg-bg/70 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-fg-subtle">
        <span className="relative flex h-1.5 w-1.5">
          {ok && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
          )}
          <span
            className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
              ok ? "bg-success" : "bg-danger"
            }`}
          />
        </span>
        api {ok ? "connected" : "offline"}
      </div>
      <a
        href="https://github.com/Nicolaslahri/downloadarr"
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-1.5 text-xs text-fg-muted transition-colors hover:text-fg"
      >
        <Github className="h-3.5 w-3.5" />
        repo
      </a>
    </div>
  );
}
