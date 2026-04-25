import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MusicDownloadarr",
  description: "Self-hosted music librarian",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
