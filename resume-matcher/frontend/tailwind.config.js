/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 50: "#eef3fb", 100: "#d7e2f5", 700: "#132c5b", 800: "#0e2249", 900: "#0a1a3a", 950: "#06112a" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
