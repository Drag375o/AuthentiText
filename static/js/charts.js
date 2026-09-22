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

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
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

  document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.querySelector("[data-sentence-chart]");
    const script = document.getElementById("sentence-chart-data");
    if (!canvas || !script || !window.Chart) return;
    sentenceChart(canvas, JSON.parse(script.textContent));
  });
})();
