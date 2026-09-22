/**
 * AuthentiText: inline document rename.
 *
 * Progressive enhancement over a plain <details> form. With JS, a "Rename"
 * button swaps the title for an input: Enter saves (fetch, JSON), Esc or
 * Cancel restores the title. The server answers JSON when asked
 * (Accept: application/json) and redirects otherwise.
 */
(() => {
  "use strict";

  function initRename(root) {
    const view = root.querySelector("[data-rename-view]");
    const titleEl = root.querySelector("[data-rename-title]");
    const openBtn = root.querySelector("[data-rename-open]");
    const details = root.querySelector("[data-rename-fallback]");
    const form = root.querySelector("[data-rename-form]");
    const input = root.querySelector("[data-rename-input]");
    const error = root.querySelector("[data-rename-error]");
    const save = root.querySelector("[data-rename-save]");
    const saveLabel = root.querySelector("[data-rename-save-label]");
    const cancel = root.querySelector("[data-rename-cancel]");

    // Switch from the no-JS fallback to the inline editor.
    details.open = true;
    details.querySelector("summary").hidden = true;
    details.hidden = true;
    openBtn.classList.remove("hidden");
    cancel.classList.remove("hidden");

    let savedTitle = input.value;

    function showError(message) {
      error.textContent = message;
      error.classList.toggle("hidden", !message);
      input.setAttribute("aria-invalid", message ? "true" : "false");
    }

    function open() {
      input.value = savedTitle;
      showError("");
      view.hidden = true;
      details.hidden = false;
      input.focus();
      input.select();
    }

    function close() {
      details.hidden = true;
      view.hidden = false;
      openBtn.focus();
    }

    function setBusy(busy) {
      save.toggleAttribute("aria-busy", busy);
      saveLabel.textContent = busy ? "Saving\u2026" : "Save";
    }

    async function submit(event) {
      event.preventDefault();
      if (save.getAttribute("aria-busy")) return;
      setBusy(true);
      showError("");
      try {
        const response = await fetch(root.dataset.renameUrl, {
          method: "POST",
          body: new FormData(form),                       // includes the CSRF token
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.ok) {
          showError(data.error || "Couldn't rename this document. Try again.");
          return;
        }
        savedTitle = data.title;
        titleEl.textContent = data.display_name;
        input.placeholder = data.display_name;
        document.querySelectorAll("[data-confirm-name]").forEach((el) => { el.dataset.confirmName = data.display_name; });
        document.title = document.title.replace(/^[^\u00b7]+\u00b7/, `${data.display_name} \u00b7`);
        titleEl.classList.remove("rename-flash");
        void titleEl.offsetWidth;                         // restart the confirmation flash
        titleEl.classList.add("rename-flash");
        close();
      } catch {
        showError("Couldn't reach the server. Check your connection and try again.");
      } finally {
        setBusy(false);
      }
    }

    openBtn.addEventListener("click", open);
    cancel.addEventListener("click", close);
    form.addEventListener("submit", submit);
    input.addEventListener("input", () => showError(""));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-rename]").forEach(initRename);
  });
})();
