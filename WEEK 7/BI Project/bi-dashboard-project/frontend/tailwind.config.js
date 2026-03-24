/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(200 20% 98%)",
        foreground: "hsl(210 40% 12%)",
        card: "hsl(0 0% 100%)",
        border: "hsl(200 20% 90%)",
        primary: "hsl(180 78% 37%)",
        secondary: "hsl(180 30% 95%)",
        muted: "hsl(200 18% 94%)",
        "muted-foreground": "hsl(210 15% 50%)",
        success: "hsl(160 60% 45%)",
        warning: "hsl(38 92% 50%)",
        destructive: "hsl(0 72% 51%)",
        purple: "hsl(258 64% 67%)",
      },
      fontFamily: {
        sans: ["DM Sans", "sans-serif"],
        mono: ["DM Mono", "monospace"],
      },
      boxShadow: {
        soft: "0 10px 30px rgba(20, 40, 60, 0.08)",
      },
      borderRadius: {
        xl2: "1rem",
      },
    },
  },
  plugins: [],
};
