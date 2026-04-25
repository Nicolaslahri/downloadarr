"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  CircleDashed,
  CircleSlash,
  Download,
  Loader2,
  Search,
  Tag,
  XCircle,
} from "lucide-react";
import type { TrackStatus } from "@/lib/types";
import { cn } from "@/lib/cn";

const META: Record<
  TrackStatus,
  { label: string; tone: string; icon: React.ComponentType<{ className?: string }>; spin?: boolean; pulse?: boolean }
> = {
  pending: { label: "Pending", tone: "text-fg-subtle border-border bg-bg-hover", icon: CircleDashed },
  resolving: { label: "Resolving", tone: "text-warn border-warn/30 bg-warn/10", icon: Search, spin: true },
  downloading: { label: "Downloading", tone: "text-accent border-accent/30 bg-accent/10", icon: Download, pulse: true },
  tagging: { label: "Tagging", tone: "text-accent-glow border-accent/30 bg-accent/10", icon: Tag, spin: true },
  done: { label: "Done", tone: "text-success border-success/30 bg-success/10", icon: CheckCircle2 },
  failed: { label: "Failed", tone: "text-danger border-danger/30 bg-danger/10", icon: XCircle },
  skipped: { label: "Skipped", tone: "text-fg-muted border-border bg-bg-hover", icon: CircleSlash },
};

export function StatusPill({ status, className }: { status: TrackStatus; className?: string }) {
  const m = META[status] ?? META.pending;
  const Icon = m.spin ? Loader2 : m.icon;
  return (
    <motion.span
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider",
        m.tone,
        m.pulse && "animate-pulseGlow",
        className
      )}
    >
      <Icon className={cn("h-3 w-3", m.spin && "animate-spin")} />
      {m.label}
    </motion.span>
  );
}
