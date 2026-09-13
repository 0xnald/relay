import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17222d",
        canvas: "#f5f7f8",
        relay: "#176b5b",
        alert: "#b45309"
      }
    }
  },
  plugins: []
};

export default config;
