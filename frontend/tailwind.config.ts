/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0f",
        foreground: "#e4e4e7",
        card: "#13131a",
        border: "#27272a",
        accent: "#6366f1",
      },
    },
  },
  plugins: [],
};
