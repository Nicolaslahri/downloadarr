import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#08080b",
          subtle: "#0d0d12",
          raised: "#13131a",
          hover: "#1b1b24",
        },
        border: {
          DEFAULT: "#1f1f2a",
          strong: "#2a2a38",
        },
        fg: {
          DEFAULT: "#e8e8ee",
          muted: "#9a9aa8",
          subtle: "#5a5a68",
        },
        accent: {
          DEFAULT: "#7c5cff",
          glow: "#a18bff",
        },
        success: "#22d3a5",
        warn: "#f5c451",
        danger: "#f87171",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 50% 0%, rgba(124,92,255,0.16), transparent 60%), radial-gradient(circle at 80% 80%, rgba(34,211,165,0.10), transparent 50%)",
        "grid-lines":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(124,92,255,0.5)" },
          "50%": { boxShadow: "0 0 0 8px rgba(124,92,255,0)" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.2" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        shimmer: "shimmer 2.5s linear infinite",
        pulseGlow: "pulseGlow 2s ease-in-out infinite",
        scan: "scan 3s linear infinite",
        fadeIn: "fadeIn 0.4s ease-out both",
        blink: "blink 1.4s ease-in-out infinite",
        gradient: "gradient 8s ease infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
