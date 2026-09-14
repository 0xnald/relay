import type { Config } from "tailwindcss";

// Relay design tokens. Colors are exposed as CSS variables in globals.css and referenced here so
// components never carry raw hex values.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--relay-bg) / <alpha-value>)",
        surface: "rgb(var(--relay-surface) / <alpha-value>)",
        elevated: "rgb(var(--relay-elevated) / <alpha-value>)",
        line: "rgb(var(--relay-line) / <alpha-value>)",
        ink: "rgb(var(--relay-ink) / <alpha-value>)",
        "ink-2": "rgb(var(--relay-ink-2) / <alpha-value>)",
        "ink-3": "rgb(var(--relay-ink-3) / <alpha-value>)",
        mint: "rgb(var(--relay-mint) / <alpha-value>)",
        amber: "rgb(var(--relay-amber) / <alpha-value>)",
        danger: "rgb(var(--relay-danger) / <alpha-value>)"
      },
      backgroundColor: {
        "mint-soft": "rgb(var(--relay-mint) / 0.10)",
        "amber-soft": "rgb(var(--relay-amber) / 0.10)",
        "danger-soft": "rgb(var(--relay-danger) / 0.10)"
      },
      borderRadius: {
        card: "16px",
        "card-sm": "12px",
        "card-lg": "20px"
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      fontSize: {
        "2xs": ["11px", { lineHeight: "16px", letterSpacing: "0.06em" }],
        xs: ["12px", { lineHeight: "18px" }],
        sm: ["13px", { lineHeight: "20px" }],
        base: ["14px", { lineHeight: "22px" }],
        md: ["15px", { lineHeight: "24px" }],
        lg: ["17px", { lineHeight: "26px" }],
        xl: ["20px", { lineHeight: "28px" }],
        "2xl": ["24px", { lineHeight: "32px" }],
        "3xl": ["30px", { lineHeight: "36px", letterSpacing: "-0.01em" }]
      },
      boxShadow: {
        card: "0 1px 0 0 rgb(0 0 0 / 0.25), 0 8px 24px -16px rgb(0 0 0 / 0.6)",
        "card-hover": "0 1px 0 0 rgb(0 0 0 / 0.3), 0 16px 32px -18px rgb(0 0 0 / 0.7)",
        ring: "0 0 0 1px rgb(var(--relay-mint) / 0.6), 0 0 0 4px rgb(var(--relay-mint) / 0.15)"
      },
      transitionDuration: {
        fast: "160ms",
        base: "200ms"
      },
      keyframes: {
        shimmer: { "0%": { backgroundPosition: "200% 0" }, "100%": { backgroundPosition: "-200% 0" } },
        rise: { "0%": { opacity: "0", transform: "translateY(4px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulseDot: { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0.35" } }
      },
      animation: {
        shimmer: "shimmer 1.8s linear infinite",
        rise: "rise 220ms ease-out both",
        "pulse-dot": "pulseDot 2s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;
