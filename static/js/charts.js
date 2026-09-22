/**
 * AuthentiText: Chart.js visualisations for the document page.
 * Sentence rhythm: one bar per sentence plus a dashed average line.
 * Selecting a bar scrolls to that sentence in the list and highlights it.
 * Colours come from the page's CSS so charts follow the design tokens.
 */
(() => {
  "use strict";

  function cssColor(name, fallback) {
    const probe = document.createElement("span");
    probe.className = name;
    probe.style.display = "none";
    document.body.append(probe);
    const color = getComputedStyle(probe).color || fallback;
    probe.remove();
    return color;
  }

  function focusSentence(index) {
    const row = document.getElementById(`sentence-${index}`);
    if (!row) return;
    row.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    row.focus({ preventScroll: true });
    row.classList.remove("is-highlighted");
    void row.offsetWidth;
    row.classList.add("is-highlighted");
  }

  function sentenceChart(canvas, data) {
    const ink = cssColor("text-ink", "#000");
    const muted = cssColor("text-muted", "#6b6b6b");
    const rule = cssColor("text-rule", "#e4e4e4");
    const brass = cssColor("text-brass", "#a58556");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const labels = data.lengths.map((_, i) => String(i + 1));

    return new Chart(canvas, {
      data: {
        labels,
        datasets: [
          { type: "bar", label: "Words", data: data.lengths, backgroundColor: ink, hoverBackgroundColor: muted,
            borderRadius: 2, maxBarThickness: 28 },
          { type: "line", label: "Average", data: labels.map(() => data.mean), borderColor: brass, borderWidth: 2,
            borderDash: [6, 4], pointRadius: 0, pointHitRadius: 0 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: reduceMotion ? false : { duration: 700, easing: "easeOutQuart" },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: (item) => item.datasetIndex === 0,
            callbacks: {
              title: (items) => `Sentence ${items[0].label}: ${items[0].raw} words`,
              label: (item) => data.texts[item.dataIndex],
            },
            displayColors: false,
            padding: 12,
            bodyFont: { size: 12 },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: muted, maxTicksLimit: 20 }, title: { display: true, text: "Sentence", color: muted } },
          y: { beginAtZero: true, grid: { color: rule }, ticks: { color: muted, precision: 0 }, title: { display: true, text: "Words", color: muted } },
        },
        onClick: (_, elements) => { if (elements.length) focusSentence(elements[0].index); },
        onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? "pointer" : "default"; },
      },
    });
  }

  /** Horizontal bars: parts of speech as a share of words. */
  function posChart(canvas, data) {
    const ink = cssColor("text-ink", "#000");
    const muted = cssColor("text-muted", "#6b6b6b");
    const rule = cssColor("text-rule", "#e4e4e4");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return new Chart(canvas, {
      type: "bar",
      data: { labels: data.labels, datasets: [{ data: data.values, backgroundColor: ink, borderRadius: 2, maxBarThickness: 16 }] },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        animation: reduceMotion ? false : { duration: 700, easing: "easeOutQuart" },
        plugins: {
          legend: { display: false },
          tooltip: { displayColors: false, callbacks: { label: (item) => `${item.raw}% of words` } },
        },
        scales: {
          x: { beginAtZero: true, grid: { color: rule }, ticks: { color: muted, callback: (v) => `${v}%` } },
          y: { grid: { display: false }, ticks: { color: ink } },
        },
      },
    });
  }

  function readJson(id) {
    const el = document.getElementById(id);
    try { return el ? JSON.parse(el.textContent) : null; } catch { return null; }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!window.Chart) return;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    const rhythm = document.querySelector("[data-sentence-chart]");
    const rhythmData = readJson("sentence-chart-data");
    if (rhythm && rhythmData) sentenceChart(rhythm, rhythmData);
    const pos = document.querySelector("[data-pos-chart]");
    const posData = readJson("pos-chart-data");
    if (pos && posData) posChart(pos, posData);
  });
})();
