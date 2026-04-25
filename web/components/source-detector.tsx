"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Apple, Music2, Sparkles, Youtube, Cloud, Link2, AlertCircle } from "lucide-react";
import type { DetectedSource } from "@/lib/source-detect";

const ICON: Record<DetectedSource["kind"], React.ComponentType<{ className?: string }>> = {
  spotify: Music2,
  apple_music: Apple,
  youtube_music: Youtube,
  youtube: Youtube,
  soundcloud: Cloud,
  ai_video: Sparkles,
  unknown: Link2,
};

const TONE: Record<DetectedSource["kind"], string> = {
  spotify: "text-success border-success/40 bg-success/10",
  apple_music: "text-fg border-border bg-bg-hover",
  youtube_music: "text-danger border-danger/30 bg-danger/10",
  youtube: "text-danger border-danger/30 bg-danger/10",
  soundcloud: "text-warn border-warn/30 bg-warn/10",
  ai_video: "text-accent border-accent/40 bg-accent/10 animate-pulseGlow",
  unknown: "text-fg-subtle border-border bg-bg-hover",
};

export function SourceDetector({ source }: { source: DetectedSource }) {
  const Icon = source.kind === "unknown" && source.label.startsWith("Not") ? AlertCircle : ICON[source.kind];
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={source.kind + source.label}
        initial={{ opacity: 0, y: 6, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -6, scale: 0.96 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wider ${TONE[source.kind]}`}
      >
        <Icon className="h-3.5 w-3.5" />
        {source.label}
      </motion.div>
    </AnimatePresence>
  );
}
