"use client";

import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SWRConfig } from "swr";
import { fetcher } from "@/lib/api";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ fetcher, revalidateOnFocus: false }}>
      <TooltipProvider delayDuration={200}>
        {children}
        <Toaster
          theme="dark"
          richColors
          toastOptions={{
            style: {
              background: "rgba(13,13,18,0.92)",
              border: "1px solid #2a2a38",
              backdropFilter: "blur(12px)",
            },
          }}
        />
      </TooltipProvider>
    </SWRConfig>
  );
}
