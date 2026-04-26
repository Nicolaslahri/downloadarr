"use client";

import { Progress } from "@/components/ui/progress";

function fmtBytes(n: number): string {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function fmtSpeed(kbps: number): string {
  if (!kbps) return "—";
  if (kbps < 1024) return `${kbps} KB/s`;
  return `${(kbps / 1024).toFixed(1)} MB/s`;
}

function fmtEta(bytesLeft: number, kbps: number): string {
  if (!kbps || !bytesLeft) return "—";
  const seconds = Math.round(bytesLeft / 1024 / kbps);
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`;
}

export function TrackProgressBar({
  bytesDone,
  bytesTotal,
  speedKbps,
}: {
  bytesDone: number;
  bytesTotal: number;
  speedKbps: number;
}) {
  const pct = bytesTotal > 0 ? Math.min(100, (bytesDone / bytesTotal) * 100) : 0;
  const left = Math.max(0, bytesTotal - bytesDone);
  return (
    <div className="grid w-full gap-1">
      <Progress value={pct} className="h-1" />
      <div className="flex justify-between gap-2 font-mono text-[10px] text-fg-subtle">
        <span>
          {fmtBytes(bytesDone)} / {fmtBytes(bytesTotal)}
        </span>
        <span>{fmtSpeed(speedKbps)}</span>
        <span>ETA {fmtEta(left, speedKbps)}</span>
      </div>
    </div>
  );
}
