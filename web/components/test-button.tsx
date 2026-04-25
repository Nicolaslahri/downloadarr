"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, Plug, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { TestResult } from "@/lib/api";

type Tone = "idle" | "ok" | "fail";

export function TestButton({
  label = "Test",
  onTest,
  className,
}: {
  label?: string;
  onTest: () => Promise<TestResult>;
  className?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [tone, setTone] = useState<Tone>("idle");

  async function run() {
    if (busy) return;
    setBusy(true);
    setTone("idle");
    try {
      const r = await onTest();
      setTone(r.ok ? "ok" : "fail");
      if (r.ok) toast.success(r.message);
      else toast.error(r.message);
    } catch (e) {
      setTone("fail");
      toast.error(e instanceof Error ? e.message : "Test failed");
    } finally {
      setBusy(false);
      // Reset tone after a few seconds so the button doesn't stay coloured
      setTimeout(() => setTone("idle"), 4000);
    }
  }

  const Icon =
    tone === "ok" ? CheckCircle2 : tone === "fail" ? XCircle : busy ? Loader2 : Plug;

  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      onClick={run}
      disabled={busy}
      className={cn(
        "gap-1.5 transition-colors",
        tone === "ok" && "border-success/40 bg-success/10 text-success hover:bg-success/15",
        tone === "fail" && "border-danger/40 bg-danger/10 text-danger hover:bg-danger/15",
        className
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={`${tone}-${busy}`}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.15 }}
          className="inline-flex items-center gap-1.5"
        >
          <Icon className={cn("h-3.5 w-3.5", busy && "animate-spin")} />
          {busy ? "Testing" : label}
        </motion.span>
      </AnimatePresence>
    </Button>
  );
}
