/**
 * AuthentiText: hero "reading lens" text field.
 *
 * A faint wall of text sits behind the hero. Words near the pointer darken and
 * some pick up the same signal underlines as the sentence viewer (dotted, dashed,
 * solid). When the pointer is idle or absent (touch), the lens drifts on its own.
 *
 * Markup:
 *   [data-hero]        the section that receives pointer events
 *   [data-hero-field]  the <canvas>
 *   [data-hero-quiet]  the text block; the field fades out behind it
 *
 * Colours come from CSS custom properties (--field-*) in static/src/input.css.
 * Decorative only: aria-hidden, no pointer events, still frame for reduced motion.
 */
(() => {
  "use strict";

  const CONFIG = {
    fontSize: 15,
    lineHeight: 30,
    wordGap: 7,
    lensRadius: 170,
    lensEase: 0.08,          // 0-1, how quickly the lens follows the pointer
    idleAfterMs: 2500,       // start drifting after this long without movement
    lensDarkness: 0.7,       // max opacity of words under the lens
    quietFloor: 0.2,         // resting opacity behind the text block
    quietLensFloor: 0.12,    // lens strength behind the text block
    quietEdge: 120,          // px over which the quiet zone fades in
    topFade: 60,             // px fade at the top of the hero
  };

  const PASSAGE = (
    "A sentence is a small machine for moving attention. Writers choose where it starts, how long it runs, " +
    "and what it leaves out. Some prose hurries; some lingers on a single stained page. Every habit leaves a trace: " +
    "the transitions we lean on, the words we repeat, the rhythm of short against long. Reading closely means noticing " +
    "those traces without mistaking them for a verdict. Signals invite a second look. They never prove who held the pen."
  ).split(/\s+/);

  /** Deterministic 0-1 value per word, so the pattern is identical on every load. */
  function hash(n) {
    n = (n ^ 61) ^ (n >>> 16);
    n = n + (n << 3);
    n = n ^ (n >>> 4);
    n = Math.imul(n, 0x27d4eb2d);
    return ((n ^ (n >>> 15)) >>> 0) / 4294967295;
  }

  function levelFor(index) {
    const r = hash(index + 7);
    if (r > 0.95) return "high";
    if (r > 0.85) return "mid";
    if (r > 0.70) return "low";
    return null;
  }

  function smoothstep(t) { return t * t * (3 - 2 * t); }
  function clamp01(t) { return Math.min(1, Math.max(0, t)); }

  function readColors() {
    const css = getComputedStyle(document.documentElement);
    const get = (name) => css.getPropertyValue(name).trim();
    return { rest: get("--field-rest"), ink: get("--field-ink"),
             low: get("--field-low"), mid: get("--field-mid"), high: get("--field-high") };
  }

  class HeroField {
    constructor(hero, canvas, quietEl) {
      this.hero = hero;
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.quietEl = quietEl;
      this.reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      this.colors = readColors();
      this.words = [];
      this.base = null;           // offscreen canvas holding the resting field
      this.quiet = null;          // text-block rectangle, hero coordinates
      this.lens = { x: 0, y: 0, tx: 0, ty: 0, active: false, lastMove: 0 };
      this.running = false;
      this.frame = this.frame.bind(this);
    }

    init() {
      this.layout();
      this.bindEvents();
      this.reduceMotion ? this.render() : this.start();
    }

    /* ---------- Layout ---------- */

    layout() {
      const { canvas, ctx } = this;
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.width = this.hero.clientWidth;
      this.height = this.hero.clientHeight;
      canvas.width = Math.round(this.width * this.dpr);
      canvas.height = Math.round(this.height * this.dpr);
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.font = `${CONFIG.fontSize}px "Times New Roman", Times, serif`;

      this.words = this.buildWords();
      this.quiet = this.measureQuietZone();
      this.drawBase();

      if (!this.lens.active) {
        this.lens.x = this.lens.tx = this.width * 0.72;
        this.lens.y = this.lens.ty = this.height * 0.5;
      }
    }

    buildWords() {
      const words = [];
      let index = 0;
      for (let y = CONFIG.lineHeight; y < this.height + CONFIG.lineHeight; y += CONFIG.lineHeight) {
        let x = -((y / CONFIG.lineHeight) % 3) * 24; // stagger line starts
        while (x < this.width) {
          const text = PASSAGE[index % PASSAGE.length];
          const w = this.ctx.measureText(text).width;
          words.push({ text, x, y, w, cx: x + w / 2, cy: y - CONFIG.fontSize / 3, level: levelFor(index) });
          x += w + CONFIG.wordGap;
          index += 1;
        }
      }
      return words;
    }

    measureQuietZone() {
      const heroRect = this.hero.getBoundingClientRect();
      const r = this.quietEl.getBoundingClientRect();
      const pad = 24;
      return { left: r.left - heroRect.left - pad, right: r.right - heroRect.left + pad,
               top: r.top - heroRect.top - pad, bottom: r.bottom - heroRect.top + pad };
    }

    /** 1 far from the text block, easing to `floor` inside it. */
    quietFactor(word, floor) {
      const q = this.quiet;
      const dx = Math.max(q.left - word.cx, 0, word.cx - q.right);
      const dy = Math.max(q.top - word.cy, 0, word.cy - q.bottom);
      const e = smoothstep(Math.min(1, Math.hypot(dx, dy) / CONFIG.quietEdge));
      return floor + (1 - floor) * e;
    }

    topFactor(word) { return clamp01(word.cy / CONFIG.topFade); }

    /* ---------- Drawing ---------- */

    drawBase() {
      const base = document.createElement("canvas");
      base.width = this.canvas.width;
      base.height = this.canvas.height;
      const b = base.getContext("2d");
      b.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      b.font = this.ctx.font;
      b.fillStyle = this.colors.rest;
      for (const word of this.words) {
        b.globalAlpha = this.quietFactor(word, CONFIG.quietFloor) * this.topFactor(word);
        b.fillText(word.text, word.x, word.y);
      }
      this.base = base;
    }

    drawUnderline(word, strength) {
      const { ctx } = this;
      ctx.strokeStyle = this.colors[word.level];
      ctx.globalAlpha = strength;
      ctx.lineWidth = word.level === "high" ? 2.5 : 1.6;
      ctx.setLineDash(word.level === "low" ? [1.5, 3] : word.level === "mid" ? [5, 3] : []);
      ctx.beginPath();
      ctx.moveTo(word.x, word.y + 5);
      ctx.lineTo(word.x + word.w, word.y + 5);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    render() {
      if (!this.base) return;
      const { ctx, lens } = this;
      const r2 = CONFIG.lensRadius * CONFIG.lensRadius;
      ctx.clearRect(0, 0, this.width, this.height);
      ctx.globalAlpha = 1;
      ctx.drawImage(this.base, 0, 0, this.width, this.height);

      ctx.fillStyle = this.colors.ink;
      for (const word of this.words) {
        const dx = word.cx - lens.x;
        const dy = word.cy - lens.y;
        const d2 = dx * dx + dy * dy;
        if (d2 > r2) continue;

        let t = smoothstep(1 - Math.sqrt(d2) / CONFIG.lensRadius);
        t *= this.quietFactor(word, CONFIG.quietLensFloor) * this.topFactor(word);

        ctx.globalAlpha = t * CONFIG.lensDarkness;
        ctx.fillText(word.text, word.x, word.y);
        if (word.level && t > 0.25) this.drawUnderline(word, Math.min(1, (t - 0.25) * 1.6));
      }
      ctx.globalAlpha = 1;
    }

    /* ---------- Animation ---------- */

    frame(now) {
      const { lens } = this;
      if (!lens.active || now - lens.lastMove > CONFIG.idleAfterMs) {
        const s = now / 1000;
        lens.tx = this.width * (0.62 + 0.22 * Math.sin(s * 0.23));
        lens.ty = this.height * (0.5 + 0.32 * Math.sin(s * 0.31 + 1.3));
      }
      lens.x += (lens.tx - lens.x) * CONFIG.lensEase;
      lens.y += (lens.ty - lens.y) * CONFIG.lensEase;
      this.render();
      if (this.running) requestAnimationFrame(this.frame);
    }

    start() {
      if (this.running || this.reduceMotion) return;
      this.running = true;
      requestAnimationFrame(this.frame);
    }

    stop() { this.running = false; }

    /* ---------- Events ---------- */

    bindEvents() {
      this.hero.addEventListener("pointermove", (event) => {
        const rect = this.hero.getBoundingClientRect();
        this.lens.tx = event.clientX - rect.left;
        this.lens.ty = event.clientY - rect.top;
        this.lens.active = true;
        this.lens.lastMove = performance.now();
      });
      this.hero.addEventListener("pointerleave", () => { this.lens.active = false; });

      // Pause when the hero is off-screen or the tab is hidden.
      new IntersectionObserver(([entry]) => (entry.isIntersecting ? this.start() : this.stop()))
        .observe(this.hero);
      document.addEventListener("visibilitychange", () => (document.hidden ? this.stop() : this.start()));

      let resizeTimer;
      new ResizeObserver(() => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
          this.layout();
          if (this.reduceMotion) this.render();
        }, 120);
      }).observe(this.hero);
    }
  }

  function boot() {
    const hero = document.querySelector("[data-hero]");
    const canvas = document.querySelector("[data-hero-field]");
    const quiet = document.querySelector("[data-hero-quiet]");
    if (!hero || !canvas || !quiet || !canvas.getContext) return;
    new HeroField(hero, canvas, quiet).init();
  }

  // Wait for fonts so the quiet zone is measured around the final headline size.
  document.addEventListener("DOMContentLoaded", () => {
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(boot);
  });
})();
