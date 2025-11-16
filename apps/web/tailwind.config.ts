import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f5f7fb",
          100: "#e3e8f6",
          200: "#c5d1ed",
          300: "#9eafe0",
          400: "#7a89d1",
          500: "#5f69c1",
          600: "#4a4ea8",
          700: "#3e4187",
          800: "#36386b",
          900: "#2d2f57"
        }
      }
    }
  },
  plugins: []
};

export default config;

