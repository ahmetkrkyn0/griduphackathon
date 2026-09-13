// EK-II/14 olculerine (1600 x 1500 mm) gore KENDI cizimimiz: 2D on gorunus.
// Komitenin PDF'inden gorsel alinmadi. Koordinat: mm, y asagi dogru.
// renderFront(svg, points, { highlight, tokens })

(function () {
  const NS = "http://www.w3.org/2000/svg";
  const el = (name, attrs, parent) => {
    const n = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };

  const BAR_Y = { L1: 510, L2: 695, L3: 880 };
  const N_Y = 1290;
  const dsyaX = (n) => 120 + 160 * (n - 1);

  function pointPos(pt) {
    let m = pt.match(/^DSYA(\d)_L(\d)$/);
    if (m) return { x: dsyaX(+m[1]) + (+m[2] - 2) * 30, y: 1080 };
    m = pt.match(/^GIRIS_(L\d|N)$/);
    if (m) {
      if (m[1] === "N") return { x: 1540, y: N_Y };
      return { x: 1330 + 70 * (+m[1][1] - 1), y: BAR_Y[m[1]] };
    }
    return null;
  }

  window.renderFront = function (svg, points, opts = {}) {
    const t = Object.assign(
      {
        enclosure: "#F7F7F4", stroke: "#8E958F", zone: "#EEEFEA", bar: "#B9B4A6", dsya: "#5D646A",
        dot: "#A3A9AD", ours: "#2C63C9", ink: "#3A4045", warn: "#D6A100", alarm: "#DD6418", critical: "#C62828",
        font: "inherit",
      },
      opts.tokens || {}
    );
    svg.setAttribute("viewBox", "-30 -30 1660 1560");
    svg.innerHTML = "";

    // Govde ve bolgeler
    el("rect", { x: 0, y: 0, width: 1600, height: 1500, fill: t.enclosure, stroke: t.stroke, "stroke-width": 6, rx: 6 }, svg);
    el("rect", { x: 0, y: 0, width: 1600, height: 350, fill: t.zone }, svg);
    el("rect", { x: 0, y: 1100, width: 1600, height: 400, fill: t.zone }, svg);
    el("line", { x1: 0, y1: 350, x2: 1600, y2: 350, stroke: t.stroke, "stroke-width": 3 }, svg);
    el("line", { x1: 0, y1: 1100, x2: 1600, y2: 1100, stroke: t.stroke, "stroke-width": 3, "stroke-dasharray": "14 10" }, svg);

    // Ust bolme: Pano Beyni (bizim urun), TVOC-2, modem, sigortalar, kompanzasyon
    el("line", { x1: 60, y1: 205, x2: 1540, y2: 205, stroke: t.stroke, "stroke-width": 10 }, svg);
    el("rect", { x: 240, y: 150, width: 170, height: 110, rx: 8, fill: t.ours }, svg);
    el("rect", { x: 90, y: 158, width: 120, height: 94, rx: 6, fill: t.dsya }, svg);
    el("rect", { x: 440, y: 160, width: 120, height: 90, rx: 6, fill: t.dsya, opacity: 0.55 }, svg);
    for (let i = 0; i < 5; i++) el("rect", { x: 610 + i * 42, y: 172, width: 30, height: 66, rx: 3, fill: t.dsya, opacity: 0.4 }, svg);
    for (let i = 0; i < 3; i++) el("circle", { cx: 1010 + i * 105, cy: 205, r: 42, fill: "none", stroke: t.dsya, "stroke-width": 8, opacity: 0.45 }, svg);

    // Baralar
    for (const y of Object.values(BAR_Y)) el("rect", { x: 40, y: y - 10, width: 1520, height: 20, rx: 3, fill: t.bar }, svg);
    el("rect", { x: 40, y: N_Y - 8, width: 1520, height: 16, rx: 3, fill: t.bar, opacity: 0.8 }, svg);
    // Giris baralari (ustten)
    for (let p = 0; p < 3; p++) el("rect", { x: 1320 + 70 * p, y: 0, width: 20, height: Object.values(BAR_Y)[p], fill: t.bar }, svg);
    el("rect", { x: 1532, y: 0, width: 16, height: N_Y, fill: t.bar, opacity: 0.8 }, svg);

    // DSYA seritleri
    for (let n = 1; n <= 7; n++) {
      const x = dsyaX(n);
      el("rect", { x: x - 50, y: 420, width: 100, height: 620, rx: 10, fill: t.dsya, opacity: n >= 6 ? 0.45 : 1 }, svg);
      const lbl = el("text", { x, y: 405, "text-anchor": "middle", "font-size": 40, fill: t.ink, "font-family": t.font }, svg);
      lbl.textContent = n >= 6 ? `${n} yedek` : `DSYA-${n}`;
      if (n <= 5) for (let p = -1; p <= 1; p++) el("line", { x1: x + p * 30, y1: 1080, x2: x + p * 30, y2: 1500, stroke: t.dsya, "stroke-width": 12, opacity: 0.35 }, svg);
    }

    // Olcum noktalari
    const color = { normal: t.dot, warn: t.warn, alarm: t.alarm, critical: t.critical, stale: "none" };
    for (const p of points) {
      const pos = pointPos(p.pt);
      if (!pos) continue;
      const g = el("g", { class: "pt", "data-pt": p.pt }, svg);
      if (p.state !== "normal" && p.state !== "stale") {
        el("circle", { cx: pos.x, cy: pos.y, r: 44, fill: "none", stroke: color[p.state], "stroke-width": 7, class: "pt-halo" }, g);
      }
      el("circle", { cx: pos.x, cy: pos.y, r: 15, fill: color[p.state], stroke: p.state === "stale" ? t.dot : "#fff", "stroke-width": 5 }, g);
      const title = el("title", {}, g);
      title.textContent = `${p.label}: ${p.t_c} °C, ΔT ${p.dt_c} K`;
    }

    if (opts.highlight) {
      const pos = pointPos(opts.highlight.pt);
      const g = el("g", {}, svg);
      el("line", { x1: pos.x + 40, y1: pos.y + 30, x2: pos.x + 170, y2: pos.y + 180, stroke: t.ink, "stroke-width": 4 }, g);
      const tx = el("text", { x: pos.x + 180, y: pos.y + 205, "font-size": 48, fill: t.ink, "font-family": t.font, "font-weight": 600 }, g);
      tx.textContent = opts.highlight.text;
    }
  };
})();
