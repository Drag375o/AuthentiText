/** AuthentiText design tokens. Change colours/fonts here, not in templates. */
module.exports = {
  content: ["./templates/**/*.html", "./**/templates/**/*.html", "./static/js/**/*.js", "./core/**/*.py"],
  // Built dynamically in templates (sig-{{ level }}), so the scanner can't see them.
  safelist: ["sig-low", "sig-mid", "sig-high"],
  theme: {
    extend: {
      colors: {
        paper: "#FFFFFF",
        ink: "#000000",
        graphite: "#333333",
        muted: "#6B6B6B",
        fog: "#F4F4F4",
        rule: "#E4E4E4",
        field: "#F0F0F0",  // resting colour of the hero text field
        slate: { DEFAULT: "#52627A", soft: "#E8ECF2" },
        indigo: { DEFAULT: "#5A5E8C", soft: "#EBECF4" },
        brass: { DEFAULT: "#A58556", soft: "#F5EFE5" },
        signal: {
          low: "#6F8699",   "low-bg": "#EEF2F5",
          mid: "#B08A3E",   "mid-bg": "#F7F0E1",
          high: "#8E3B46",  "high-bg": "#F6E9EB",
          ok: "#4F7A5A",    warn: "#B7791F",
        },
      },
      fontFamily: {
        display: ['"Montserrat"', "Helvetica Neue", "Arial", "sans-serif"],
        serif: ['"Times New Roman"', "Times", "Georgia", "serif"],
        label: ['"Julius Sans One"', '"Montserrat"', "Arial", "sans-serif"],
        script: ['"Cedarville Cursive"', '"Brush Script MT"', "cursive"],
      },
      fontSize: {
        // Modular scale (~1.25) with editorial display sizes
        "display-xl": ["clamp(2.5rem, 4.4vw, 4.5rem)", { lineHeight: "0.95", letterSpacing: "-0.035em" }],
        "display-brand": ["clamp(3.4rem, 5.6vw, 5.25rem)", { lineHeight: "1.05" }],
        "display-lg": ["clamp(2.5rem, 5vw, 4rem)", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        "display-md": ["clamp(1.75rem, 3vw, 2.5rem)", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
      },
      maxWidth: { page: "75rem", prose: "36rem" },
      borderRadius: { card: "0.375rem" },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04)",
        lift: "0 24px 48px -24px rgba(0,0,0,0.18)",
      },
    },
  },
  plugins: [],
};
