/**
 * AuthentiText: shared confirmation dialog.
 *
 *   const ok = await window.ConfirmDialog.ask({
 *     title: "Delete this analysis?",
 *     message: "This can't be undone.",
 *     confirmLabel: "Delete",
 *     busyLabel: "Deleting\u2026",   // optional: keep the dialog open with a spinner
 *   });
 *
 * Resolves true only when the confirm button is chosen. Cancel, Esc and a
 * click on the backdrop all resolve false. Cancel has focus when it opens, so
 * an accidental Enter never confirms a destructive action.
 *
 * Declarative use (handled in app.js): <form data-confirm="..." data-confirm-title="...">
 */
(() => {
  "use strict";

  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setup() {
    const dialog = document.querySelector("[data-confirm-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return null;

    const el = {
      title: dialog.querySelector("[data-confirm-title]"),
      message: dialog.querySelector("[data-confirm-message]"),
      ok: dialog.querySelector("[data-confirm-ok]"),
      okLabel: dialog.querySelector("[data-confirm-ok-label]"),
      cancel: dialog.querySelector("[data-confirm-cancel]"),
    };
    let resolveCurrent = null;
    let lastFocus = null;

    function finish(result) {
      if (!resolveCurrent) return;
      const resolve = resolveCurrent;
      resolveCurrent = null;
      resolve(result);
    }

    /** Plays the exit animation, then closes. */
    function close(result) {
      if (!dialog.open) return;
      if (reduceMotion()) {
        dialog.close(result);
        return;
      }
      dialog.classList.add("is-closing");
      dialog.addEventListener("animationend", () => {
        dialog.classList.remove("is-closing");
        dialog.close(result);
      }, { once: true });
    }

    function setBusy(label) {
      el.ok.setAttribute("aria-busy", "true");
      el.okLabel.textContent = label;
      el.cancel.setAttribute("aria-disabled", "true");
      dialog.dataset.busy = "true";
    }

    function reset() {
      el.ok.removeAttribute("aria-busy");
      el.cancel.removeAttribute("aria-disabled");
      delete dialog.dataset.busy;
    }

    // The <form method="dialog"> closes the dialog on submit; intercept to animate.
    dialog.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      if (dialog.dataset.busy) return;
      const confirmed = event.submitter === el.ok;
      if (confirmed && dialog.dataset.busyLabel) {
        setBusy(dialog.dataset.busyLabel);   // stays open while the page navigates
        finish(true);
        return;
      }
      finish(confirmed);
      close(confirmed ? "confirm" : "cancel");
    });

    // Esc: animate out instead of closing instantly. Blocked while busy.
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      if (dialog.dataset.busy) return;
      finish(false);
      close("cancel");
    });

    // Click on the backdrop (outside the panel) cancels.
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog || dialog.dataset.busy) return;
      finish(false);
      close("cancel");
    });

    dialog.addEventListener("close", () => {
      reset();
      finish(false);
      if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
    });

    function ask({ title, message = "", confirmLabel = "Confirm", busyLabel = "", tone = "danger" } = {}) {
      if (resolveCurrent) finish(false);
      el.title.textContent = title || "Are you sure?";
      el.message.textContent = message;
      el.okLabel.textContent = confirmLabel;
      dialog.dataset.tone = tone;
      el.ok.className = `${tone === "danger" ? "btn-danger" : "btn-primary"} !py-3`;
      if (busyLabel) dialog.dataset.busyLabel = busyLabel;
      else delete dialog.dataset.busyLabel;
      reset();
      lastFocus = document.activeElement;
      dialog.showModal();
      el.cancel.focus();
      return new Promise((resolve) => { resolveCurrent = resolve; });
    }

    return { ask };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const api = setup();
    // Fallback for very old browsers without <dialog>: the native confirm box.
    window.ConfirmDialog = api || {
      ask: ({ title, message }) => Promise.resolve(window.confirm([title, message].filter(Boolean).join("\n\n"))),
    };
  });
})();
