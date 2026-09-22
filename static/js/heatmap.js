/**
 * AuthentiText: sentence viewer.
 *
 * Any element with [data-sentence-viewer] becomes interactive:
 *   - sentence buttons toggle aria-pressed (one active at a time)
 *   - [data-detail-panel] gets a full explanation
 *   - [data-detail-compact] gets a one-line summary
 * Sentence data comes from a json_script block (id "sample-document" on the
 * landing page; the results page will pass real analysis data the same way).
 */
(() => {
  "use strict";

  function readSentences(scriptId) {
    const el = document.getElementById(scriptId);
    if (!el) return [];
    try { return JSON.parse(el.textContent); } catch { return []; }
  }

  /** Builds the explanation panel with DOM APIs (no innerHTML, so no injection). */
  function renderDetail(container, sentence, index) {
    container.replaceChildren();

    const heading = document.createElement("p");
    heading.className = "label";
    heading.textContent = `Sentence ${index + 1}: ${sentence.level_label}`;

    const quote = document.createElement("blockquote");
    quote.className = "mt-4 font-serif text-lg text-ink leading-relaxed border-l-2 border-ink pl-4";
    quote.textContent = sentence.text;

    const list = document.createElement("ul");
    list.className = "mt-6 space-y-3";
    sentence.reasons.forEach((reason) => {
      const item = document.createElement("li");
      item.className = "flex gap-2 text-graphite";
      const mark = document.createElement("span");
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = "\u2014";
      const text = document.createElement("span");
      text.textContent = reason;
      item.append(mark, text);
      list.append(item);
    });

    const caveat = document.createElement("p");
    caveat.className = "meta mt-8";
    caveat.textContent = "These are signals, not proof.";

    container.append(heading, quote, list, caveat);
  }

  function initViewer(viewer, sentences) {
    const buttons = viewer.querySelectorAll("[data-sentence-index]");
    const panelBody = viewer.querySelector("[data-detail-body]");
    const compact = viewer.querySelector("[data-detail-compact]");

    const select = (button) => {
      const index = Number(button.dataset.sentenceIndex);
      const sentence = sentences[index];
      if (!sentence) return;
      const wasActive = button.getAttribute("aria-pressed") === "true";
      buttons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      if (wasActive) return;
      button.setAttribute("aria-pressed", "true");
      if (panelBody) renderDetail(panelBody, sentence, index);
      if (compact) compact.textContent = `${sentence.level_label}: ${sentence.reasons.join("; ")}.`;
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => select(button));
      // role="button" needs keyboard activation added by hand.
      button.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select(button);
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const sentences = readSentences("sample-document");
    document.querySelectorAll("[data-sentence-viewer]").forEach((viewer) => initViewer(viewer, sentences));
  });
})();
