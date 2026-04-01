---
title: Executive Overview
theme: dashboard
---

```js
const raw  = await FileAttachment("data/bowdoin_cds.csv").csv({ typed: true });
const cur  = raw[raw.length - 1];
const prev = raw[raw.length - 2];
const base = raw[0];

// Walk back to find most recent non-null value for gapped fields
const latestRet  = [...raw].reverse().find(d => d.retention_rate != null && d.retention_rate !== "");
const latestGrad = [...raw].reverse().find(d => d.grad_rate_6yr  != null && d.grad_rate_6yr  !== "");

function pp(a, b) { const d = +(a) - +(b); return (d >= 0 ? "+" : "") + d.toFixed(1) + " pp"; }
function ct(a, b) { const d = +(a) - +(b); return (d >= 0 ? "+" : "") + Math.round(d).toLocaleString(); }
```

# Bowdoin College — Executive Overview

**Entering class ${cur.year} · Common Data Sets 2001–${cur.year}**

---

```js
html`
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:20px;">

  <div class="card" style="border-top:4px solid #1B3D6E; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">Total Applications</div>
    <div style="font-size:2.5em;font-weight:800;color:#1B3D6E;line-height:1.1;">${cur.total_apps.toLocaleString()}</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">${ct(cur.total_apps, prev.total_apps)} vs prior year</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">${(cur.total_apps / base.total_apps).toFixed(1)}× volume since ${base.year}</div>
  </div>

  <div class="card" style="border-top:4px solid #1B3D6E; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">Acceptance Rate</div>
    <div style="font-size:2.5em;font-weight:800;color:#1B3D6E;line-height:1.1;">${cur.accept_rate.toFixed(1)}%</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">${pp(cur.accept_rate, prev.accept_rate)} pp vs prior year</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">Was ${base.accept_rate}% in ${base.year}</div>
  </div>

  <div class="card" style="border-top:4px solid #1B3D6E; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">Yield Rate</div>
    <div style="font-size:2.5em;font-weight:800;color:#1B3D6E;line-height:1.1;">${cur.yield_rate.toFixed(1)}%</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">${pp(cur.yield_rate, prev.yield_rate)} pp vs prior year</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">Was ${base.yield_rate}% in ${base.year}</div>
  </div>

  <div class="card" style="border-top:4px solid #2E5FA3; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">Enrolled Class</div>
    <div style="font-size:2.5em;font-weight:800;color:#2E5FA3;line-height:1.1;">${cur.total_enrolled.toLocaleString()}</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">${ct(cur.total_enrolled, prev.total_enrolled)} vs prior year</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">Total undergrad: ${cur.total_undergrad.toLocaleString()}</div>
  </div>

  <div class="card" style="border-top:4px solid #2E5FA3; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">Retention Rate</div>
    <div style="font-size:2.5em;font-weight:800;color:#2E5FA3;line-height:1.1;">${latestRet ? latestRet.retention_rate.toFixed(1) + "%" : "—"}</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">First- to second-year</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">${latestRet ? "Reported for class of " + latestRet.year : "No recent data"}</div>
  </div>

  <div class="card" style="border-top:4px solid #2E5FA3; padding:18px 20px;">
    <div style="font-size:.72em;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:6px;">6-Year Grad Rate</div>
    <div style="font-size:2.5em;font-weight:800;color:#2E5FA3;line-height:1.1;">${latestGrad ? latestGrad.grad_rate_6yr.toFixed(1) + "%" : "—"}</div>
    <div style="font-size:.82em;color:#888;margin-top:6px;">Most recent reported value</div>
    <div style="font-size:.76em;color:#bbb;margin-top:2px;">${latestGrad ? "Reported for class of " + latestGrad.year : "No recent data"}</div>
  </div>

</div>
`
```

## Acceptance Rate & Yield, ${base.year}–${cur.year}

```js
Plot.plot({
  width, height: 180,
  x: { tickFormat: "d", label: null },
  y: { label: "Percent", grid: true, ticks: 4 },
  marks: [
    Plot.ruleY([0]),
    Plot.line(raw, { x: "year", y: "accept_rate", stroke: "#1B3D6E", strokeWidth: 2.5, tip: true, title: d => `Acceptance: ${d.accept_rate}%` }),
    Plot.line(raw, { x: "year", y: "yield_rate",  stroke: "purple", strokeWidth: 2, strokeDasharray: "5,3", tip: true, title: d => `Yield: ${d.yield_rate}%` }),
    Plot.text([{ year: 2004, v: 23 }], { x: "year", y: "v", text: () => "Acceptance rate", fill: "purple", fontSize: 10, dy: -10 }),
    Plot.text([{ year: 2004, v: 43 }], { x: "year", y: "v", text: () => "Yield rate",      fill: "#C5A028", fontSize: 10, dy: -10 }),
  ]
})
```

Applications have grown **${(cur.total_apps / base.total_apps).toFixed(1)}×** since ${base.year} while the enrolled class has held near 500, compressing the acceptance rate from ${base.accept_rate}% to ${cur.accept_rate.toFixed(1)}%.

---

## Explore the Data

```js
html`
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:4px;">

  <a href="./bowdoin" style="text-decoration:none;">
    <div class="card" style="padding:16px 18px; border-left:3px solid #1B3D6E; cursor:pointer;">
      <div style="font-size:.95em;font-weight:700;color:#1B3D6E;">Bowdoin Deep Dive</div>
      <div style="font-size:.82em;color:#666;margin-top:4px;">Full pipeline, geography, ethnicity, degrees, and institutional health — Bowdoin only</div>
    </div>
  </a>

  <a href="./top20" style="text-decoration:none;">
    <div class="card" style="padding:16px 18px; border-left:3px solid #2E5FA3; cursor:pointer;">
      <div style="font-size:.95em;font-weight:700;color:#2E5FA3;">Top-20 LAC Comparison</div>
      <div style="font-size:.82em;color:#666;margin-top:4px;">Selectivity, yield, enrollment, and class composition across the top 20 liberal arts colleges</div>
    </div>
  </a>

  <a href="./top20#maine" style="text-decoration:none;">
    <div class="card" style="padding:16px 18px; border-left:3px solid #8C2131; cursor:pointer;">
      <div style="font-size:.95em;font-weight:700;color:#8C2131;">Maine Rivals</div>
      <div style="font-size:.82em;color:#666;margin-top:4px;">Head-to-head: Bowdoin vs. Bates vs. Colby on every key metric</div>
    </div>
  </a>

</div>
`
```

*Source: Bowdoin College Common Data Sets, 2001–${cur.year}.*