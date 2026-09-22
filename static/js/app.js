/**
 * AuthentiText: site-wide behaviour.
 * Mobile menu, sticky-nav border, icon rendering, hero image fallback, meters.
 */
(() => {
  "use strict";

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initIcons() {
    if (window.lucide) window.lucide.createIcons();
  }

  function initMobileMenu() {
    const toggle = document.querySelector("[data-menu-toggle]");
    const menu = document.querySelector("[data-menu]");
    if (!toggle || !menu) return;

    const setOpen = (open) => {
      menu.classList.toggle("hidden", !open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector(".sr-only").textContent = open ? "Close menu" : "Open menu";
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  function initStickyNav() {
    const nav = document.querySelector("[data-sticky-nav]");
    if (!nav) return;
    const update = () => nav.classList.toggle("border-rule", window.scrollY > 8);
    update();
    window.addEventListener("scroll", update, { passive: true });
  }

  /** Fills .meter bars to their data-meter value when they scroll into view. */
  function initMeters() {
    const bars = document.querySelectorAll("[data-meter]");
    const fill = (bar) => { bar.style.transform = `scaleX(${Number(bar.dataset.meter) / 100})`; };
    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      bars.forEach(fill);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        fill(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.4 });
    bars.forEach((bar) => observer.observe(bar));
  }

  /** Images marked data-hide-on-error disappear if the file is missing,
   *  leaving their container's background instead of a broken icon. */
  function initImageFallbacks() {
    document.querySelectorAll("img[data-hide-on-error]").forEach((img) => {
      const hide = () => img.remove();
      if (img.complete && img.naturalWidth === 0) hide();
      else img.addEventListener("error", hide, { once: true });
    });
  }

  /** Forms with data-confirm ask before submitting (e.g. delete). */
  function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
      });
    });
  }

  /** The page's single orchestrated moment: the hero card rises, then marks
   *  itself up. Waits for fonts so the card doesn't shift mid-animation. */
  function initHeroCard() {
    const card = document.querySelector("[data-hero-card]");
    if (!card) return;
    const rise = () => requestAnimationFrame(() => card.classList.add("is-in"));
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(rise);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initIcons();
    initMobileMenu();
    initStickyNav();
    initMeters();
    initHeroCard();
    initConfirmForms();
    initImageFallbacks();
  });
})();
