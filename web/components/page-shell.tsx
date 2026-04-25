"use client";

import { motion } from "framer-motion";

export function PageShell({
  children,
  title,
  eyebrow,
  description,
  actions,
}: {
  children: React.ReactNode;
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="mx-auto w-full max-w-6xl px-6 py-10"
    >
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          {eyebrow && (
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-fg-subtle">
              {eyebrow}
            </div>
          )}
          <h1 className="text-3xl font-semibold tracking-tight gradient-text inline-block pb-1">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-fg-muted">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children}
    </motion.div>
  );
}
