export type DetectedSource =
  | { kind: "spotify"; label: "Spotify" }
  | { kind: "apple_music"; label: "Apple Music" }
  | { kind: "youtube_music"; label: "YouTube Music" }
  | { kind: "youtube"; label: "YouTube playlist" }
  | { kind: "soundcloud"; label: "SoundCloud" }
  | { kind: "youtube_video"; label: "Single video" }
  | { kind: "unknown"; label: string };

export function detectSource(raw: string): DetectedSource {
  const url = raw.trim();
  if (!url) return { kind: "unknown", label: "Detect when you paste" };
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, "");
    if (host.includes("spotify.com")) return { kind: "spotify", label: "Spotify" };
    if (host.includes("music.apple.com")) return { kind: "apple_music", label: "Apple Music" };
    if (host === "music.youtube.com") {
      // YT Music: /playlist is a playlist, /watch is a single video
      if (u.pathname === "/watch" && u.searchParams.get("v")) {
        return { kind: "youtube_video", label: "Single video" };
      }
      return { kind: "youtube_music", label: "YouTube Music" };
    }
    if (host.includes("soundcloud.com")) return { kind: "soundcloud", label: "SoundCloud" };
    if (host === "youtube.com" || host === "youtu.be" || host.endsWith(".youtube.com")) {
      // youtu.be/X is always a single video
      if (host === "youtu.be") return { kind: "youtube_video", label: "Single video" };
      // watch?v=X is a single video, even if list= is also present
      if (u.pathname === "/watch" && u.searchParams.get("v")) {
        return { kind: "youtube_video", label: "Single video" };
      }
      // /playlist?list=PL... (no v=) is a playlist; refuse RD* (radio mix) lists
      if (u.pathname.startsWith("/playlist") && u.searchParams.get("list")) {
        const list = u.searchParams.get("list") ?? "";
        if (list.startsWith("RD") || list.startsWith("UU") || list.startsWith("FL")) {
          return { kind: "unknown", label: "Auto-generated mix — paste the song URL instead" };
        }
        return { kind: "youtube", label: "YouTube playlist" };
      }
      return { kind: "unknown", label: "Unrecognized YouTube URL" };
    }
    return { kind: "unknown", label: "Unrecognized link" };
  } catch {
    return { kind: "unknown", label: "Not a valid URL yet" };
  }
}
