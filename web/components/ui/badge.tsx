import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider transition-colors",
  {
    variants: {
      tone: {
        neutral: "bg-bg-hover text-fg-muted border border-border",
        accent: "bg-accent/10 text-accent border border-accent/30",
        success: "bg-success/10 text-success border border-success/30",
        warn: "bg-warn/10 text-warn border border-warn/30",
        danger: "bg-danger/10 text-danger border border-danger/30",
        ghost: "bg-transparent text-fg-subtle border border-border",
      },
    },
    defaultVariants: { tone: "neutral" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
