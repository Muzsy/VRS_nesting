/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        slate: "#334155",
        mist: "#e2e8f0",
        sand: "#f8fafc",
        accent: "#0ea5e9",
        danger: "#dc2626",
        success: "#16a34a"
      }
    }
  },
  plugins: [],
};
