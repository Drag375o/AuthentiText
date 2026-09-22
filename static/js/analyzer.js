/**
 * AuthentiText: Analyze page editor.
 *
 * Live statistics (via text-stats.js, the twin of the server's rules),
 * the evidence gauge, the character limit, Ctrl/Cmd+Enter to save,
 * Clear, and a warning before leaving with unsaved text.
 * Limits come from the server through the "editor-config" json_script.
 */
(() => {
  "use strict";

  const number = new Intl.NumberFormat();

  function readConfig() {
    const el = document.getElementById("editor-config");
    try { return JSON.parse(el.textContent); } catch { return { maxChars: 100000, minWords: 150 }; }
  }

  function formatReading(minutes, words) {
    if (!words) return "0 min";
    return minutes <= 1 ? "1 min" : `${number.format(minutes)} min`;
  }

  function evidenceMessage(words, minWords) {
    if (!words) return `Add at least ${number.format(minWords)} words for a reliable result.`;
    if (words < minWords) {
      const more = minWords - words;
      return `Add ${number.format(more)} more word${more === 1 ? "" : "s"} for a reliable result. Shorter texts are reported as \u201cInsufficient evidence\u201d.`;
    }
    return "Enough text for a reliable result.";
  }

  function initEditor(form) {
    const config = readConfig();
    const textarea = form.querySelector("textarea");
    const title = form.querySelector("input[name='title']");
    const charCount = form.querySelector("[data-char-count]");
    const meter = form.querySelector("[data-evidence-meter]");
    const meterBar = meter.querySelector("span");
    const evidenceText = form.querySelector("[data-evidence-text]");
    const announce = form.querySelector("[data-stats-announce]");
    const submit = form.querySelector("[data-editor-submit]");
    const stat = (name) => form.querySelector(`[data-stat="${name}"]`);
    const out = { words: stat("words"), sentences: stat("sentences"), paragraphs: stat("paragraphs"),
                  characters: stat("characters"), reading: stat("reading") };

    let frame = 0;
    let announceTimer = 0;
    let submitting = false;
    let lastStats = window.TextStats.compute(textarea.value);

    function render() {
      frame = 0;
      const s = window.TextStats.compute(textarea.value);
      lastStats = s;
      out.words.textContent = number.format(s.words);
      out.sentences.textContent = number.format(s.sentences);
      out.paragraphs.textContent = number.format(s.paragraphs);
      out.characters.textContent = number.format(s.characters);
      out.reading.textContent = formatReading(s.reading_minutes, s.words);

      const over = s.characters > config.maxChars;
      charCount.textContent = `${number.format(s.characters)} / ${number.format(config.maxChars)} characters`;
      charCount.classList.toggle("editor-over-limit", over);

      const progress = Math.min(1, s.words / config.minWords);
      meterBar.style.transform = `scaleX(${progress})`;
      meter.setAttribute("aria-valuenow", String(Math.min(s.words, config.minWords)));
      evidenceText.textContent = evidenceMessage(s.words, config.minWords);

      // Announce a short summary only after typing pauses.
      clearTimeout(announceTimer);
      announceTimer = setTimeout(() => {
        announce.textContent = `${number.format(s.words)} words, ${number.format(s.sentences)} sentences.`;
      }, 1200);
    }

    const schedule = () => { if (!frame) frame = requestAnimationFrame(render); };
    textarea.addEventListener("input", schedule);
    render();

    // Ctrl/Cmd + Enter saves from anywhere in the form.
    form.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    form.querySelector("[data-editor-clear]").addEventListener("click", () => {
      if (lastStats.words > 20 && !window.confirm("Clear the editor? Your text isn't saved yet.")) return;
      textarea.value = "";
      if (title) title.value = "";
      render();
      textarea.focus();
    });

    form.addEventListener("submit", (event) => {
      const s = window.TextStats.compute(textarea.value);
      if (!s.words) {
        event.preventDefault();
        evidenceText.textContent = "Add some text to analyze first.";
        textarea.focus();
        return;
      }
      if (s.characters > config.maxChars) {
        event.preventDefault();
        evidenceText.textContent = `This text is over the ${number.format(config.maxChars)}-character limit. Split it into smaller documents.`;
        textarea.focus();
        return;
      }
      submitting = true;
      submit.textContent = "Saving\u2026";
      submit.setAttribute("aria-busy", "true");
    });

    // Warn before leaving with unsaved text.
    window.addEventListener("beforeunload", (event) => {
      if (!submitting && textarea.value.trim()) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("[data-editor-form]");
    if (form && window.TextStats) initEditor(form);
  });
})();
