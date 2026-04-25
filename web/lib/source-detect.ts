export type DetectedSource =
  | { kind: "spotify"; label: "Spotify" }
  | { kind: "apple_music"; label: "Apple Music" }
  | { kind: "youtube_music"; label: "YouTube Music" }
  | { kind: "youtube"; label: "YouTube" }
  | { kind: "soundcloud"; label: "SoundCloud" }
  | { kind: "ai_video"; label: "AI — video tracklist" }
  | { kind: "unknown"; label: "Detect when you paste" };

export function detectSource(raw: string): DetectedSource {
  const url = raw.trim();
  if (!url) return { kind: "unknown", label: "Detect when you paste" };
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, "");
    if (host.includes("spotify.com")) return { kind: "spotify", label: "Spotify" };
    if (host.includes("music.apple.com")) return { kind: "apple_music", label: "Apple Music" };
    if (host === "music.youtube.com") return { kind: "youtube_music", label: "YouTube Music" };
    if (host.includes("soundcloud.com")) return { kind: "soundcloud", label: "SoundCloud" };
    if (host === "youtube.com" || host === "youtu.be" || host.endsWith(".youtube.com")) {
      const isPlaylist = u.searchParams.get("list") || u.pathname.includes("/playlist");
      if (isPlaylist) return { kind: "youtube", label: "YouTube" };
      return { kind: "ai_video", label: "AI — video tracklist" };
    }
    return { kind: "unknown", label: "Unrecognized link" };
  } catch {
    return { kind: "unknown", label: "Not a valid URL yet" };
  }
}
