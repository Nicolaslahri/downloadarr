"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Brain,
  FolderTree,
  Magnet,
  Music2,
  Newspaper,
  Plus,
  Save,
  Server,
  Sliders,
  Sparkles,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  AppSettings,
  SettingsUpdate,
  TorrentIndexer,
  UsenetIndexer,
  UsenetServer,
} from "@/lib/types";
import { PageShell } from "@/components/page-shell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { TestButton } from "@/components/test-button";
import { Wrench, CheckCircle2, AlertTriangle, Download } from "lucide-react";
import type { ToolsStatus } from "@/lib/api";

export default function SettingsPage() {
  const { data, mutate } = useSWR<AppSettings>("/settings");
  const [draft, setDraft] = useState<SettingsUpdate>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!data) return;
    setDraft((d) => ({
      library_path: data.library_path,
      quality_profile: data.quality_profile,
      preferred_sources: data.preferred_sources,
      usenet_indexers: data.usenet_indexers,
      usenet_servers: data.usenet_servers,
      torrent_indexers: data.torrent_indexers,
      ...d,
    }));
  }, [data]);

  function set<K extends keyof SettingsUpdate>(key: K, value: SettingsUpdate[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }
  function togglePref(name: string) {
    const list = draft.preferred_sources ?? data?.preferred_sources ?? [];
    set("preferred_sources", list.includes(name) ? list.filter((s) => s !== name) : [...list, name]);
  }

  async function save() {
    setSaving(true);
    try {
      const next = await api.updateSettings(draft);
      mutate(next);
      setDraft({});
      toast.success("Settings saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!data) return null;
  const prefs = draft.preferred_sources ?? data.preferred_sources;

  return (
    <PageShell
      eyebrow="config"
      title="Settings"
      description="Wire up your Usenet and torrent sources. The app does the indexing and downloading itself — no Prowlarr, SAB, or qBittorrent needed."
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
          <TabsTrigger value="usenet"><Newspaper className="h-3.5 w-3.5" /> Usenet</TabsTrigger>
          <TabsTrigger value="torrents"><Magnet className="h-3.5 w-3.5" /> Torrents</TabsTrigger>
          <TabsTrigger value="ai"><Brain className="h-3.5 w-3.5" /> AI</TabsTrigger>
          <TabsTrigger value="streaming"><Music2 className="h-3.5 w-3.5" /> Streaming</TabsTrigger>
          <TabsTrigger value="tools"><Wrench className="h-3.5 w-3.5" /> Tools</TabsTrigger>
        </TabsList>

        <TabsContent value="library">
          <Card>
            <CardHeader>
              <CardTitle>Library destination</CardTitle>
              <CardDescription>
                Final path for tagged downloads. Layout is{" "}
                <code className="rounded bg-bg-hover px-1 font-mono text-xs">
                  {"{library}/{Artist}/{Album}/{Title}.{ext}"}
                </code>
                .
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Field label="Path on disk">
                <Input
                  value={draft.library_path ?? ""}
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
            <CardContent className="grid gap-4">
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {QUALITY_OPTIONS.map((opt) => {
                  const active = (draft.quality_profile ?? data.quality_profile) === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => set("quality_profile", opt.value)}
                      className={`relative rounded-lg border p-4 text-left transition-all ${
                        active ? "border-accent bg-accent/10" : "border-border bg-bg-subtle/40 hover:bg-bg-hover"
                      }`}
                    >
                      {active && (
                        <motion.div layoutId="quality-active" className="absolute inset-0 rounded-lg ring-1 ring-accent" transition={{ type: "spring", stiffness: 380, damping: 30 }} />
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

        <TabsContent value="usenet">
          <UsenetIndexersCard
            value={draft.usenet_indexers ?? data.usenet_indexers}
            onChange={(v) => set("usenet_indexers", v)}
          />
          <div className="h-4" />
          <UsenetServersCard
            value={draft.usenet_servers ?? data.usenet_servers}
            onChange={(v) => set("usenet_servers", v)}
          />
        </TabsContent>

        <TabsContent value="torrents">
          <TorrentIndexersCard
            value={draft.torrent_indexers ?? data.torrent_indexers}
            onChange={(v) => set("torrent_indexers", v)}
          />
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
            <CardContent className="grid gap-3">
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
                  value={draft.anthropic_api_key ?? ""}
                  onChange={(e) => set("anthropic_api_key", e.target.value)}
                  className="font-mono"
                />
              </Field>
              <div>
                <TestButton onTest={() => api.testAnthropic({ api_key: draft.anthropic_api_key })} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tools">
          <ToolsCard />
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
                badge={<Badge tone={data.spotify_configured ? "success" : "ghost"}>{data.spotify_configured ? "configured" : "not set"}</Badge>}
              >
                <Input
                  value={draft.spotify_client_id ?? ""}
                  onChange={(e) => set("spotify_client_id", e.target.value)}
                  className="font-mono"
                />
              </Field>
              <Field label="Spotify Client Secret">
                <Input
                  type="password"
                  value={draft.spotify_client_secret ?? ""}
                  onChange={(e) => set("spotify_client_secret", e.target.value)}
                  className="font-mono"
                  placeholder="••••"
                />
              </Field>
              <div>
                <TestButton
                  onTest={() =>
                    api.testSpotify({
                      client_id: draft.spotify_client_id,
                      client_secret: draft.spotify_client_secret,
                    })
                  }
                />
              </div>
            </CardContent>
          </Card>
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
        <span className="font-mono text-[10px] uppercase tracking-widest text-fg-muted">{label}</span>
        {badge}
      </div>
      {children}
      {hint && <p className="mt-1 text-[11px] text-fg-subtle">{hint}</p>}
    </label>
  );
}

function ListShell({
  icon: Icon,
  title,
  description,
  empty,
  onAdd,
  children,
  count,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  empty: string;
  onAdd: () => void;
  children: React.ReactNode;
  count: number;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Icon className="h-4 w-4" /> {title}
            <Badge tone={count > 0 ? "success" : "ghost"}>
              {count} {count === 1 ? "entry" : "entries"}
            </Badge>
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onAdd}>
          <Plus className="h-3.5 w-3.5" /> Add
        </Button>
      </CardHeader>
      <CardContent>
        {count === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-bg-subtle/30 p-6 text-center text-sm text-fg-muted">
            {empty}
          </div>
        ) : (
          <div className="grid gap-3">{children}</div>
        )}
      </CardContent>
    </Card>
  );
}

function UsenetIndexersCard({
  value,
  onChange,
}: {
  value: UsenetIndexer[];
  onChange: (v: UsenetIndexer[]) => void;
}) {
  function update(i: number, patch: Partial<UsenetIndexer>) {
    onChange(value.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }
  function remove(i: number) {
    onChange(value.filter((_, idx) => idx !== i));
  }
  function add() {
    onChange([
      ...value,
      { name: "NZBGeek", url: "https://api.nzbgeek.info", api_key: "" },
    ]);
  }
  return (
    <ListShell
      icon={Newspaper}
      title="Usenet indexers"
      description="Newznab-compatible search APIs (NZBGeek, DrunkenSlug, NZBPlanet, etc.). Add as many as you want — every search fans out across all of them in parallel."
      empty="No indexers yet. Add one to enable Usenet search."
      onAdd={add}
      count={value.length}
    >
      {value.map((row, i) => (
        <motion.div
          key={i}
          layout
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-2 rounded-lg border border-border bg-bg-subtle/40 p-3"
        >
          <div className="grid gap-2 md:grid-cols-[140px_1fr_220px_36px]">
            <Field label="Name">
              <Input value={row.name} onChange={(e) => update(i, { name: e.target.value })} />
            </Field>
            <Field label="API URL">
              <Input
                value={row.url}
                onChange={(e) => update(i, { url: e.target.value })}
                placeholder="https://api.nzbgeek.info"
                className="font-mono"
              />
            </Field>
            <Field
              label="API key"
              badge={<Badge tone={row.api_key_set ? "success" : "ghost"}>{row.api_key_set ? "saved" : "not set"}</Badge>}
            >
              <Input
                type="password"
                value={row.api_key ?? ""}
                onChange={(e) => update(i, { api_key: e.target.value })}
                placeholder={row.api_key_set ? "•••• (leave blank to keep)" : "key"}
                className="font-mono"
              />
            </Field>
            <div className="flex items-end pb-1">
              <Button variant="ghost" size="icon" onClick={() => remove(i)} className="h-9 w-9 text-danger hover:bg-danger/10">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="flex justify-end">
            <TestButton
              onTest={() =>
                api.testUsenetIndexer({
                  name: row.name,
                  url: row.url,
                  api_key: row.api_key,
                })
              }
            />
          </div>
        </motion.div>
      ))}
    </ListShell>
  );
}

function UsenetServersCard({
  value,
  onChange,
}: {
  value: UsenetServer[];
  onChange: (v: UsenetServer[]) => void;
}) {
  function update(i: number, patch: Partial<UsenetServer>) {
    onChange(value.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }
  function remove(i: number) {
    onChange(value.filter((_, idx) => idx !== i));
  }
  function add() {
    onChange([
      ...value,
      {
        name: "Newshosting",
        host: "news.newshosting.com",
        port: 563,
        ssl: true,
        username: "",
        password: "",
        connections: 20,
      },
    ]);
  }
  return (
    <ListShell
      icon={Server}
      title="Usenet news servers"
      description="NNTP servers used for the actual download. Each connection is a TLS socket — Newshosting, Eweka, UsenetServer, Frugal, etc."
      empty="No servers yet. Add one before you can download from Usenet."
      onAdd={add}
      count={value.length}
    >
      {value.map((row, i) => (
        <motion.div
          key={i}
          layout
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-2 rounded-lg border border-border bg-bg-subtle/40 p-3"
        >
          <div className="grid gap-2 md:grid-cols-[140px_1fr_90px_70px_36px]">
            <Field label="Name">
              <Input value={row.name} onChange={(e) => update(i, { name: e.target.value })} />
            </Field>
            <Field label="Host">
              <Input
                value={row.host}
                onChange={(e) => update(i, { host: e.target.value })}
                className="font-mono"
                placeholder="news.example.com"
              />
            </Field>
            <Field label="Port">
              <Input
                type="number"
                value={row.port}
                onChange={(e) => update(i, { port: Number(e.target.value) || 563 })}
                className="font-mono"
              />
            </Field>
            <Field label="SSL">
              <div className="flex h-10 items-center">
                <Switch checked={row.ssl} onCheckedChange={(v) => update(i, { ssl: v })} />
              </div>
            </Field>
            <div className="flex items-end pb-1">
              <Button variant="ghost" size="icon" onClick={() => remove(i)} className="h-9 w-9 text-danger hover:bg-danger/10">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-[1fr_1fr_120px]">
            <Field label="Username">
              <Input value={row.username} onChange={(e) => update(i, { username: e.target.value })} className="font-mono" />
            </Field>
            <Field
              label="Password"
              badge={<Badge tone={row.password_set ? "success" : "ghost"}>{row.password_set ? "saved" : "not set"}</Badge>}
            >
              <Input
                type="password"
                value={row.password ?? ""}
                onChange={(e) => update(i, { password: e.target.value })}
                placeholder={row.password_set ? "•••• (leave blank to keep)" : ""}
                className="font-mono"
              />
            </Field>
            <Field label="Connections">
              <Input
                type="number"
                value={row.connections}
                onChange={(e) => update(i, { connections: Number(e.target.value) || 10 })}
                className="font-mono"
              />
            </Field>
          </div>
          <div className="flex justify-end">
            <TestButton
              onTest={() =>
                api.testUsenetServer({
                  name: row.name,
                  host: row.host,
                  port: row.port,
                  ssl: row.ssl,
                  username: row.username,
                  password: row.password,
                })
              }
            />
          </div>
        </motion.div>
      ))}
    </ListShell>
  );
}

function TorrentIndexersCard({
  value,
  onChange,
}: {
  value: TorrentIndexer[];
  onChange: (v: TorrentIndexer[]) => void;
}) {
  function update(i: number, patch: Partial<TorrentIndexer>) {
    onChange(value.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }
  function remove(i: number) {
    onChange(value.filter((_, idx) => idx !== i));
  }
  function add() {
    onChange([...value, { name: "Tracker", url: "", api_key: "" }]);
  }
  return (
    <ListShell
      icon={Magnet}
      title="Torrent indexers"
      description="Torznab-compatible APIs. Searches go straight to each indexer; the embedded libtorrent engine handles the download (magnet or .torrent) inside this app."
      empty="No torrent indexers configured."
      onAdd={add}
      count={value.length}
    >
      {value.map((row, i) => (
        <motion.div
          key={i}
          layout
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-2 rounded-lg border border-border bg-bg-subtle/40 p-3"
        >
          <div className="grid gap-2 md:grid-cols-[140px_1fr_220px_36px]">
            <Field label="Name">
              <Input value={row.name} onChange={(e) => update(i, { name: e.target.value })} />
            </Field>
            <Field label="API URL">
              <Input
                value={row.url}
                onChange={(e) => update(i, { url: e.target.value })}
                className="font-mono"
                placeholder="https://… (Torznab endpoint)"
              />
            </Field>
            <Field
              label="API key"
              badge={<Badge tone={row.api_key_set ? "success" : "ghost"}>{row.api_key_set ? "saved" : "not set"}</Badge>}
            >
              <Input
                type="password"
                value={row.api_key ?? ""}
                onChange={(e) => update(i, { api_key: e.target.value })}
                placeholder={row.api_key_set ? "•••• (leave blank to keep)" : "optional"}
                className="font-mono"
              />
            </Field>
            <div className="flex items-end pb-1">
              <Button variant="ghost" size="icon" onClick={() => remove(i)} className="h-9 w-9 text-danger hover:bg-danger/10">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="flex justify-end">
            <TestButton
              onTest={() =>
                api.testTorrentIndexer({
                  name: row.name,
                  url: row.url,
                  api_key: row.api_key,
                })
              }
            />
          </div>
        </motion.div>
      ))}
    </ListShell>
  );
}

function ToolsCard() {
  const { data, mutate } = useSWR<ToolsStatus>("/settings/tools", { refreshInterval: 4000 });
  const [installing, setInstalling] = useState<"none" | "install" | "force">("none");

  async function install(force: boolean) {
    setInstalling(force ? "force" : "install");
    try {
      const next = await api.installTools(force);
      mutate(next);
      const ok = Object.values(next).every((t) => t.available);
      if (ok) toast.success("All tools available");
      else toast.message("Tools install ran — see status");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Install failed");
    } finally {
      setInstalling("none");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench className="h-4 w-4" /> External binaries
        </CardTitle>
        <CardDescription>
          par2 (repair) and unrar (extraction) are needed to fully post-process Usenet
          downloads. The app installs them automatically into{" "}
          <code className="rounded bg-bg-hover px-1 font-mono text-xs">backend/.data/tools/</code>.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {data ? (
          <>
            <ToolRow tool={data.par2} />
            <ToolRow tool={data.unrar} />
          </>
        ) : (
          <p className="text-sm text-fg-muted">Loading tool status…</p>
        )}
        <div className="mt-2 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => install(false)}
            disabled={installing !== "none"}
          >
            <Download className="h-3.5 w-3.5" />
            {installing === "install" ? "Installing…" : "Install missing"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => install(true)}
            disabled={installing !== "none"}
          >
            {installing === "force" ? "Reinstalling…" : "Reinstall all"}
          </Button>
        </div>
        <p className="mt-2 text-[11px] text-fg-subtle">
          unrar may need a manual step on Windows if the rarlab SFX can't silent-extract under your
          user account. If install keeps failing, download UnRAR.exe from rarlab.com and drop it
          into <code className="font-mono">backend/.data/tools/</code> — the app will pick it up
          on the next status check.
        </p>
      </CardContent>
    </Card>
  );
}

function ToolRow({ tool }: { tool: ToolsStatus[keyof ToolsStatus] }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-bg-subtle/40 p-3">
      <div className="mt-0.5">
        {tool.available ? (
          <CheckCircle2 className="h-5 w-5 text-success" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-warn" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium uppercase tracking-wider">{tool.name}</span>
          <Badge tone={tool.available ? "success" : "warn"}>
            {tool.available ? (tool.auto_managed ? "auto-installed" : "system") : "missing"}
          </Badge>
        </div>
        {tool.path && (
          <div className="mt-1 truncate font-mono text-[11px] text-fg-subtle">{tool.path}</div>
        )}
        {tool.error && (
          <div className="mt-1 text-[11px] text-warn">{tool.error}</div>
        )}
      </div>
    </div>
  );
}

const QUALITY_OPTIONS = [
  { value: "best" as const, label: "Best available", hint: "Whatever is highest fidelity, even if it's lossy." },
  { value: "lossless_first" as const, label: "Lossless first", hint: "Prefer FLAC; fall back to high-bitrate MP3/M4A." },
  { value: "320_only" as const, label: "320 kbps minimum", hint: "Reject anything below 320 kbps. Strict." },
];

const ALL_SOURCES = ["nzb", "torrent"];
