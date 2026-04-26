"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Magnet, Newspaper, Play, Search, Users } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, type TrackCandidate } from "@/lib/api";

function fmtBytes(n: number): string {
  if (!n) return "—";
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(0)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function ManualSearchDialog({
  trackId,
  initialQuery = "",
  open,
  onOpenChange,
  onPicked,
}: {
  trackId: number;
  initialQuery?: string;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onPicked?: () => void;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<TrackCandidate[]>([]);
  const [searching, setSearching] = useState(false);
  const [pickingUrl, setPickingUrl] = useState<string | null>(null);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim() || searching) return;
    setSearching(true);
    try {
      const r = await api.manualSearch(trackId, query.trim());
      setResults(r);
      if (r.length === 0) toast.message("No results — try a different query.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function pick(c: TrackCandidate) {
    setPickingUrl(c.url);
    try {
      await api.useCandidate(trackId, c);
      toast.success(`Re-queued with: ${c.title}`);
      onOpenChange(false);
      onPicked?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Pick failed");
    } finally {
      setPickingUrl(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-4 w-4" /> Manual search
          </DialogTitle>
          <DialogDescription>
            Type a custom query — the indexers run it as-is, ignoring our album cross-check
            and other auto filters. Pick any result to download.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={runSearch} className="flex gap-2">
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g.  RAYE Escapism FLAC"
            disabled={searching}
            className="flex-1"
          />
          <Button type="submit" disabled={!query.trim() || searching}>
            {searching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Searching
              </>
            ) : (
              <>
                <Search className="h-4 w-4" /> Search
              </>
            )}
          </Button>
        </form>

        <div className="mt-4 max-h-[60vh] overflow-y-auto scrollbar-slim">
          {results.length === 0 && !searching && (
            <p className="rounded border border-dashed border-border p-6 text-center text-xs text-fg-muted">
              Run a search to see indexer results.
            </p>
          )}
          <ul className="grid gap-1.5">
            {results.map((c, i) => {
              const Icon = c.source === "torrent" ? Magnet : Newspaper;
              return (
                <motion.li
                  key={c.url + i}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: i * 0.02 } }}
                  className="grid grid-cols-[24px_1fr_70px_60px_70px_80px] items-center gap-3 rounded border border-border bg-bg-subtle/50 px-2.5 py-2 text-xs"
                >
                  <Icon className="h-3.5 w-3.5 text-fg-subtle" />
                  <div className="min-w-0">
                    <div className="truncate font-medium">{c.title}</div>
                    <div className="truncate font-mono text-[10px] text-fg-subtle">
                      {c.indexer ?? c.source}
                    </div>
                  </div>
                  <Badge tone="ghost" className="justify-self-start">
                    {c.source}
                  </Badge>
                  <span className="font-mono text-[10px] text-fg-muted">
                    {fmtBytes(c.size ?? 0)}
                  </span>
                  <span className="flex items-center gap-1 font-mono text-[10px] text-fg-muted">
                    {c.seeders ? (
                      <>
                        <Users className="h-3 w-3" />
                        {c.seeders}
                      </>
                    ) : (
                      <span className="text-fg-subtle">{c.score.toFixed(2)}</span>
                    )}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => pick(c)}
                    disabled={pickingUrl !== null}
                    className="h-7 px-2 text-[10px]"
                  >
                    <Play className="h-3 w-3" />
                    {pickingUrl === c.url ? "queuing…" : "use"}
                  </Button>
                </motion.li>
              );
            })}
          </ul>
        </div>
      </DialogContent>
    </Dialog>
  );
}
