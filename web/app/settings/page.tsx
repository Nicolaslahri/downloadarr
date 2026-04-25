"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Brain,
  Cloud,
  Download,
  FolderTree,
  Music2,
  Save,
  Server,
  Sliders,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AppSettings, SettingsUpdate } from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function SettingsPage() {
  const { data, mutate } = useSWR<AppSettings>("/settings");
  const [patch, setPatch] = useState<SettingsUpdate>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) {
      setPatch((p) => ({
        library_path: data.library_path,
        quality_profile: data.quality_profile,
        preferred_sources: data.preferred_sources,
        ...p,
      }));
    }
  }, [data]);

  async function save() {
    setSaving(true);
    try {
      const next = await api.updateSettings(patch);
      mutate(next);
      setPatch({});
      toast.success("Settings saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function set<K extends keyof SettingsUpdate>(key: K, value: SettingsUpdate[K]) {
    setPatch((p) => ({ ...p, [key]: value }));
  }

  function togglePref(name: string) {
    const list = patch.preferred_sources ?? data?.preferred_sources ?? [];
    const next = list.includes(name) ? list.filter((s) => s !== name) : [...list, name];
    set("preferred_sources", next);
  }

  if (!data) return null;
  const prefs = patch.preferred_sources ?? data.preferred_sources;

  return (
    <PageShell
      eyebrow="config"
      title="Settings"
      description="Wire up your indexers, download clients, AI provider, and library destination."
      actions={
        <Button onClick={save} disabled={saving}>
          <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
        </Button>
      }
    >
      <Tabs defaultValue="library">
        <TabsList>
          <TabsTrigger value="library"><FolderTree className="h-3.5 w-3.5" /> Library</TabsTrigger>
          <TabsTrigger value="quality"><Sliders className="h-3.5 w-3.5" /> Quality</TabsTrigger>
          <TabsTrigger value="ai"><Brain className="h-3.5 w-3.5" /> AI</TabsTrigger>
          <TabsTrigger value="streaming"><Music2 className="h-3.5 w-3.5" /> Streaming</TabsTrigger>
          <TabsTrigger value="indexers"><Server className="h-3.5 w-3.5" /> Indexers</TabsTrigger>
          <TabsTrigger value="clients"><Download className="h-3.5 w-3.5" /> Clients</TabsTrigger>
        </TabsList>

        <TabsContent value="library">
          <Card>
            <CardHeader>
              <CardTitle>Library destination</CardTitle>
              <CardDescription>
                Final path for tagged downloads. Layout is{" "}
                <code className="rounded bg-bg-hover px-1 font-mono text-xs">
                  {"{library}/{Artist}/{Album}/{NN - Title}.{ext}"}
                </code>
                .
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2">
              <Field label="Path on disk">
                <Input
                  value={patch.library_path ?? ""}
                  onChange={(e) => set("library_path", e.target.value)}
                  placeholder="/library or C:\\Music"
                  className="font-mono"
                />
              </Field>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="quality">
          <Card>
            <CardHeader>
              <CardTitle>Quality profile</CardTitle>
              <CardDescription>How aggressively to chase higher-fidelity files.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {QUALITY_OPTIONS.map((opt) => {
                  const active = (patch.quality_profile ?? data.quality_profile) === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => set("quality_profile", opt.value)}
                      className={`relative rounded-lg border p-4 text-left transition-all ${
                        active
                          ? "border-accent bg-accent/10"
                          : "border-border bg-bg-subtle/40 hover:bg-bg-hover"
                      }`}
                    >
                      {active && (
                        <motion.div
                          layoutId="quality-active"
                          className="absolute inset-0 rounded-lg ring-1 ring-accent"
                          transition={{ type: "spring", stiffness: 380, damping: 30 }}
                        />
                      )}
                      <div className="font-medium">{opt.label}</div>
                      <div className="mt-1 text-xs text-fg-muted">{opt.hint}</div>
                    </button>
                  );
                })}
              </div>

              <div>
                <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
                  Preferred source order
                </div>
                <div className="flex flex-wrap gap-2">
                  {ALL_SOURCES.map((s) => {
                    const on = prefs.includes(s);
                    return (
                      <button
                        key={s}
                        type="button"
                        onClick={() => togglePref(s)}
                        className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                          on
                            ? "border-accent/40 bg-accent/10 text-accent"
                            : "border-border bg-bg-subtle/40 text-fg-muted hover:bg-bg-hover"
                        }`}
                      >
                        {s}
                      </button>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent" /> AI tracklist extraction
              </CardTitle>
              <CardDescription>
                Anthropic Claude parses YouTube descriptions or Whisper transcripts into structured
                tracklists.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Field
                label="Anthropic API key"
                hint={data.anthropic_api_key_set ? "Stored — leave blank to keep" : "Required for AI extraction"}
                badge={
                  <Badge tone={data.anthropic_api_key_set ? "success" : "ghost"}>
                    {data.anthropic_api_key_set ? "configured" : "not set"}
                  </Badge>
                }
              >
                <Input
                  type="password"
                  placeholder="sk-ant-…"
                  value={patch.anthropic_api_key ?? ""}
                  onChange={(e) => set("anthropic_api_key", e.target.value)}
                  className="font-mono"
                />
              </Field>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="streaming">
          <Card>
            <CardHeader>
              <CardTitle>Streaming services</CardTitle>
              <CardDescription>
                Public Spotify playlists need a Spotify app's client credentials. Apple Music & YT
                Music work without keys.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Field
                label="Spotify Client ID"
                badge={<Badge tone={data.spotify_configured ? "success" : "ghost"}>
                  {data.spotify_configured ? "configured" : "not set"}
                </Badge>}
              >
                <Input
                  value={patch.spotify_client_id ?? ""}
                  onChange={(e) => set("spotify_client_id", e.target.value)}
                  className="font-mono"
                />
              </Field>
              <Field label="Spotify Client Secret">
                <Input
                  type="password"
                  value={patch.spotify_client_secret ?? ""}
                  onChange={(e) => set("spotify_client_secret", e.target.value)}
                  className="font-mono"
                  placeholder="••••"
                />
              </Field>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="indexers">
          <div className="grid gap-4 md:grid-cols-2">
            <IndexerCard
              title="Prowlarr"
              hint="Aggregates torrent indexers. Point at your Prowlarr instance."
              status={data.prowlarr_configured}
              urlValue={patch.prowlarr_url ?? ""}
              keyValue={patch.prowlarr_api_key ?? ""}
              onUrl={(v) => set("prowlarr_url", v)}
              onKey={(v) => set("prowlarr_api_key", v)}
            />
            <IndexerCard
              title="NZBHydra2"
              hint="Aggregates Usenet indexers (NZBGeek etc.)."
              status={data.nzbhydra_configured}
              urlValue={patch.nzbhydra_url ?? ""}
              keyValue={patch.nzbhydra_api_key ?? ""}
              onUrl={(v) => set("nzbhydra_url", v)}
              onKey={(v) => set("nzbhydra_api_key", v)}
            />
          </div>
        </TabsContent>

        <TabsContent value="clients">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cloud className="h-4 w-4" /> qBittorrent
                  <Badge tone={data.qbt_configured ? "success" : "ghost"}>
                    {data.qbt_configured ? "configured" : "not set"}
                  </Badge>
                </CardTitle>
                <CardDescription>WebUI URL & login. Used for torrent downloads.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                <Field label="URL"><Input value={patch.qbt_url ?? ""} onChange={(e) => set("qbt_url", e.target.value)} className="font-mono" /></Field>
                <Field label="Username"><Input value={patch.qbt_user ?? ""} onChange={(e) => set("qbt_user", e.target.value)} /></Field>
                <Field label="Password"><Input type="password" value={patch.qbt_pass ?? ""} onChange={(e) => set("qbt_pass", e.target.value)} placeholder="••••" /></Field>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cloud className="h-4 w-4" /> SABnzbd
                  <Badge tone={data.sab_configured ? "success" : "ghost"}>
                    {data.sab_configured ? "configured" : "not set"}
                  </Badge>
                </CardTitle>
                <CardDescription>Usenet download client.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                <Field label="URL"><Input value={patch.sab_url ?? ""} onChange={(e) => set("sab_url", e.target.value)} className="font-mono" /></Field>
                <Field label="API key"><Input type="password" value={patch.sab_api_key ?? ""} onChange={(e) => set("sab_api_key", e.target.value)} placeholder="••••" /></Field>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}

function Field({
  label,
  hint,
  badge,
  children,
}: {
  label: string;
  hint?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-fg-muted">
          {label}
        </span>
        {badge}
      </div>
      {children}
      {hint && <p className="mt-1 text-[11px] text-fg-subtle">{hint}</p>}
    </label>
  );
}

function IndexerCard({
  title,
  hint,
  status,
  urlValue,
  keyValue,
  onUrl,
  onKey,
}: {
  title: string;
  hint: string;
  status: boolean;
  urlValue: string;
  keyValue: string;
  onUrl: (v: string) => void;
  onKey: (v: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-4 w-4" /> {title}
          <Badge tone={status ? "success" : "ghost"}>
            {status ? "configured" : "not set"}
          </Badge>
        </CardTitle>
        <CardDescription>{hint}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <Field label="URL">
          <Input
            value={urlValue}
            onChange={(e) => onUrl(e.target.value)}
            className="font-mono"
            placeholder="http://localhost:9696"
          />
        </Field>
        <Field label="API key">
          <Input
            type="password"
            value={keyValue}
            onChange={(e) => onKey(e.target.value)}
            placeholder="••••"
          />
        </Field>
      </CardContent>
    </Card>
  );
}

const QUALITY_OPTIONS = [
  { value: "best" as const, label: "Best available", hint: "Whatever is highest fidelity, even if it's lossy." },
  { value: "lossless_first" as const, label: "Lossless first", hint: "Prefer FLAC; fall back to high-bitrate MP3/M4A." },
  { value: "320_only" as const, label: "320 kbps minimum", hint: "Reject anything below 320 kbps. Strict." },
];

const ALL_SOURCES = ["ytdlp", "spotdl", "torrent", "nzb", "zotify"];
