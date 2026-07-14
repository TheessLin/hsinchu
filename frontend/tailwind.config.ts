import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        field: "#f4f7f5"
      }
    }
  },
  plugins: []
} satisfies Config;

