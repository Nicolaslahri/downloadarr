"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  Activity,
  History,
  Library,
  Settings as SettingsIcon,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Add", icon: Sparkles },
  { href: "/queue", label: "Queue", icon: Activity },
  { href: "/library", label: "Library", icon: Library },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-bg-subtle/40 backdrop-blur-md md:flex">
      <Link href="/" className="flex items-center gap-2.5 px-5 pb-5 pt-6">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-success shadow-[0_0_24px_-6px_rgba(124,92,255,0.7)]">
          <span className="font-mono text-sm font-black text-bg">M</span>
          <span className="absolute inset-0 rounded-lg ring-1 ring-white/20" />
        </div>
        <div className="leading-none">
          <div className="font-semibold tracking-tight">MusicDownloadarr</div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-fg-subtle">v0.2.0</div>
        </div>
      </Link>

      <nav className="flex flex-col gap-0.5 px-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active ? "text-fg" : "text-fg-muted hover:text-fg hover:bg-bg-hover/50"
              )}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-md bg-bg-hover"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <Icon className="relative z-10 h-4 w-4" />
              <span className="relative z-10">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-5 pb-5">
        <div className="rounded-lg border border-border bg-bg-subtle/60 p-3">
          <div className="mb-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-fg-subtle">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
            </span>
            Live
          </div>
          <p className="text-[11px] leading-relaxed text-fg-muted">
            Background activity streams over SSE. The Queue tab shows everything currently in flight.
          </p>
        </div>
      </div>
    </aside>
  );
}
