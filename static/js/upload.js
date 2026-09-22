/**
 * AuthentiText: file upload into the editor.
 *
 * - Turns the "Write or paste" / "Upload a file" panels into accessible tabs.
 * - Drag-and-drop or file picker. Quick checks run here for instant feedback;
 *   the server's validation (analyzer/services/uploads.py) is authoritative.
 * - Real progress: bytes sent come from XMLHttpRequest's upload events, then an
 *   indeterminate bar while the server extracts text.
 * - On success the text fills the editor with a signed token, and the page
 *   switches back to the editor for review.
 */
(() => {
  "use strict";

  const ALLOWED = [".txt", ".pdf", ".docx"];
  const KIND_LABEL = { txt: "TXT", pdf: "PDF", docx: "DOCX" };

  function readConfig() {
    try { return JSON.parse(document.getElementById("editor-config").textContent); } catch { return {}; }
  }

  function extensionOf(name) {
    const dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot).toLowerCase();
  }

  /* ---------- Tabs ---------- */

  function initTabs(root) {
    const tablist = root.querySelector("[data-tabs]");
    const tabs = [...tablist.querySelectorAll("[role=tab]")];
    const panels = Object.fromEntries([...root.querySelectorAll("[data-panel]")].map((p) => [p.dataset.panel, p]));
    tablist.classList.remove("hidden");

    function select(name, { focus = false } = {}) {
      tabs.forEach((tab) => {
        const active = tab.dataset.tab === name;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        if (active && focus) tab.focus();
      });
      Object.entries(panels).forEach(([key, panel]) => { panel.hidden = key !== name; });
    }

    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => select(tab.dataset.tab));
      tab.addEventListener("keydown", (event) => {
        const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
        if (!step) return;
        event.preventDefault();
        select(tabs[(i + step + tabs.length) % tabs.length].dataset.tab, { focus: true });
      });
    });

    select("write");
    return { select };
  }

  /* ---------- Upload ---------- */

  function initUpload(root, tabs, config) {
    const form = document.querySelector("[data-editor-form]");
    const uploadForm = document.getElementById("upload-form");
    const dropzone = root.querySelector("[data-dropzone]");
    const input = root.querySelector("[data-file-input]");
    const status = root.querySelector("[data-upload-status]");
    const statusText = root.querySelector("[data-upload-status-text]");
    const meter = status.querySelector(".meter");
    const bar = root.querySelector("[data-upload-bar]");
    const error = root.querySelector("[data-upload-error]");
    const textarea = form.querySelector("textarea[name=text]");
    const title = form.querySelector("input[name=title]");
    const token = form.querySelector("input[name=upload_token]");
    const chip = root.querySelector("[data-upload-chip]");
    const removeBtn = chip.querySelector("[data-upload-remove]");

    root.querySelector("[data-no-js-extract]").hidden = true;   // JS uploads on selection
    removeBtn.classList.remove("hidden");
    const defaultPlaceholder = title.placeholder;
    if (token.value) title.placeholder = chip.querySelector("[data-chip-name]").textContent.trim();

    function showError(message) {
      error.textContent = message;
      error.classList.toggle("hidden", !message);
    }

    function setStatus(state, text = "") {
      status.classList.toggle("hidden", state === "idle");
      dropzone.classList.toggle("is-busy", state !== "idle");
      meter.classList.toggle("is-indeterminate", state === "extracting");
      statusText.textContent = text;
    }

    function setText(value) {
      textarea.value = value;
      textarea.dispatchEvent(new Event("input", { bubbles: true }));   // refresh live stats
    }

    function showChip(data) {
      chip.querySelector("[data-chip-name]").textContent = data.filename;
      const pages = data.pages ? `, ${data.pages} page${data.pages === 1 ? "" : "s"}` : "";
      chip.querySelector("[data-chip-meta]").textContent =
        `${KIND_LABEL[data.kind] || data.kind}${pages}, ${Number(data.words).toLocaleString()} words. Review the text, then save.`;
      const notes = chip.querySelector("[data-chip-notes]");
      notes.replaceChildren(...(data.notes || []).map((note) => Object.assign(document.createElement("li"), { textContent: note })));
      chip.classList.remove("hidden");
    }

    function clearUpload() {
      token.value = "";
      chip.classList.add("hidden");
      title.placeholder = defaultPlaceholder;
    }

    function quickCheck(file) {
      if (!ALLOWED.includes(extensionOf(file.name))) {
        return extensionOf(file.name) === ".doc"
          ? "Older Word files (.doc) aren't supported. Open it in Word and save it as .docx."
          : "Upload a TXT, PDF or DOCX file.";
      }
      if (file.size === 0) return "This file is empty.";
      const limit = (config.maxUploadMb || 5) * 1024 * 1024;
      if (file.size > limit) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${config.maxUploadMb} MB.`;
      return "";
    }

    function send(file) {
      const body = new FormData(uploadForm);   // carries the CSRF token
      body.set("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", uploadForm.action);
      xhr.setRequestHeader("Accept", "application/json");
      xhr.responseType = "json";

      xhr.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;
        const ratio = event.loaded / event.total;
        bar.style.transform = `scaleX(${ratio})`;
        statusText.textContent = `Uploading ${file.name}\u2026 ${Math.round(ratio * 100)}%`;
      });
      xhr.upload.addEventListener("load", () => setStatus("extracting", "Extracting text\u2026"));

      return new Promise((resolve) => {
        xhr.addEventListener("load", () => resolve({ status: xhr.status, data: xhr.response || {} }));
        xhr.addEventListener("error", () => resolve({ status: 0, data: {} }));
        xhr.send(body);
      });
    }

    async function handle(file) {
      if (!file) return;
      showError("");
      const problem = quickCheck(file);
      if (problem) { showError(problem); return; }

      if (textarea.value.trim()) {
        const ok = await window.ConfirmDialog.ask({
          title: "Replace the text in the editor?",
          message: `The text from \u201c${file.name}\u201d will replace what's in the editor now.`,
          confirmLabel: "Replace text",
          tone: "neutral",
        });
        if (!ok) return;
      }

      bar.style.transform = "scaleX(0)";
      setStatus("uploading", `Uploading ${file.name}\u2026`);
      const { status: code, data } = await send(file);
      setStatus("idle");
      input.value = "";

      if (code === 0) { showError("Couldn't reach the server. Check your connection and try again."); return; }
      if (!data.ok) { showError(data.error || "We couldn't process this document. Check that it's a valid PDF, DOCX or TXT file."); return; }

      setText(data.text);
      token.value = data.token;
      title.placeholder = data.filename;
      showChip(data);
      tabs.select("write");
      textarea.focus();
      textarea.setSelectionRange(0, 0);
      textarea.scrollTop = 0;
    }

    input.addEventListener("change", () => handle(input.files[0]));

    ["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    }));
    ["dragleave", "drop"].forEach((type) => dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      if (type === "dragleave" && dropzone.contains(event.relatedTarget)) return;
      dropzone.classList.remove("is-dragover");
    }));
    dropzone.addEventListener("drop", (event) => handle(event.dataTransfer.files[0]));

    // A file dropped on the editor uploads too; dropped anywhere else, the browser won't open it.
    textarea.addEventListener("drop", (event) => {
      if (!event.dataTransfer.files.length) return;
      event.preventDefault();
      handle(event.dataTransfer.files[0]);
    });
    window.addEventListener("dragover", (event) => event.preventDefault());
    window.addEventListener("drop", (event) => event.preventDefault());

    removeBtn.addEventListener("click", async () => {
      const ok = await window.ConfirmDialog.ask({
        title: "Remove this file?",
        message: "The file's text will be cleared from the editor.",
        confirmLabel: "Remove",
      });
      if (!ok) return;
      clearUpload();
      setText("");
      textarea.focus();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-input-modes]");
    if (!root || !window.ConfirmDialog) return;
    const tabs = initTabs(root);
    initUpload(root, tabs, readConfig());
  });
})();
