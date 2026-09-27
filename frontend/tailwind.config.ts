import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/app/**/*.{ts,tsx}", "./src/components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#0F766E", dark: "#0B5F59", light: "#DFF5F0" },
        background: "#F7FAF9",
        surface: "#FFFFFF",
        text: "#10201D",
        secondary: "#52635F",
        muted: "#71817D",
        success: "#16794A",
        warning: "#A9650D",
        error: "#B93F45",
        info: "#245F9E",
        warm: { DEFAULT: "#F5EAD8", strong: "#D79B46" },
        line: "#DBE6E3",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"], editorial: ["Georgia", "Cambria", "serif"] },
      borderRadius: { sm: "10px", md: "18px", lg: "30px" },
      boxShadow: {
        subtle: "0 1px 2px rgba(15, 23, 42, 0.04), 0 6px 24px rgba(15, 64, 58, 0.05)",
        editorial: "0 28px 70px rgba(15, 64, 58, 0.10)",
      },
      maxWidth: { content: "1280px", reading: "760px" },
      screens: { xs: "320px", sm: "375px", md: "768px", lg: "1024px", xl: "1440px" },
    },
  },
  plugins: [],
};
export default config;
