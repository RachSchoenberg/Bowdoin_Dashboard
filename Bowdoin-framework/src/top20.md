---
title: Liberal Arts College Comparison
theme: dashboard
---

```js
const peersRaw = await FileAttachment("data/peers_raw.csv").csv({ typed: true });
const peersAvg = await FileAttachment("data/peers_avg.csv").csv({ typed: true });

const SCHOOL_NAMES = {
  maine: ["Bowdoin College","Bates College","Colby College"],
  top20: [
    "Bowdoin College","Williams College","Amherst College","Swarthmore College",
    "Wellesley College","Carleton College","Pomona College","Middlebury College",
    "Claremont McKenna College","Harvey Mudd College","Vassar College","Smith College",
    "Colby College","Bates College","Hamilton College","Wesleyan University",
    "Davidson College","Grinnell College","Barnard College","Washington and Lee University",
  ],
};

const SCHOOL_COLORS = {
  "Bowdoin College":              "#1B3D6E",
  "Bates College":                "#8C2131",
  "Colby College":                "#1F5BA8",
  "Williams College":             "#500082",
  "Amherst College":              "#C07400",
  "Wellesley College":            "#2E7D32",
  "Swarthmore College":           "#558B2F",
  "Pomona College":               "#E65100",
  "Middlebury College":           "#4E342E",
  "Carleton College":             "#00838F",
  "Smith College":                "#00695C",
  "Vassar College":               "#6A1B9A",
  "Barnard College":              "#AD1457",
  "Claremont McKenna College":    "#827717",
  "Harvey Mudd College":          "#37474F",
  "Hamilton College":             "#283593",
  "Wesleyan University":          "#C62828",
  "Davidson College":             "#BF360C",
  "Grinnell College":             "#1565C0",
  "Washington and Lee University":"#004D40",
};

const GROUP_LABELS = new Map([
  ["maine", "Maine rivals (Bowdoin, Bates, Colby)"],
  ["top20", "All Top-20 LACs"],
]);

function filterGroup(group) {
  const names = new Set(SCHOOL_NAMES[group]);
  return peersRaw
    .filter(d => names.has(d.inst_name))
    .map(d => ({ ...d, color: SCHOOL_COLORS[d.inst_name] ?? "#999" }));
}

const presentNames = new Set(peersRaw.map(d => d.inst_name));
const missingNames = SCHOOL_NAMES.top20.filter(n => !presentNames.has(n));
```

# Liberal Arts College Comparison

Peer data from IPEDS via the Urban Institute Education Data Portal. Bowdoin is highlighted throughout.

```js
if (missingNames.length > 0) display(html`
  <div class="card" style="padding:12px 16px;border-left:3px solid #C5A028;font-size:.85em;color:#666;margin-bottom:12px;">
    <strong>Note:</strong> The following schools were not matched in peers_raw.csv:
    <code>${missingNames.join(", ")}</code>
  </div>`);
```

---

## Acceptance Rate {#selectivity}

```js
viewof selGroup = Inputs.select(GROUP_LABELS, { value: "maine", label: "Show" })
```

```js
const selData  = filterGroup(selGroup);
const selYears = [...new Set(selData.map(d => d.year))].sort((a,b) => a - b);
const selMax   = selYears.at(-1);

Plot.plot({
  width, height: 400,
  x: { tickFormat: "d", label: "Year" },
  y: { label: "Acceptance rate (%)", grid: true },
  color: {
    legend: true,
    domain: SCHOOL_NAMES[selGroup].filter(n => presentNames.has(n)),
    range:  SCHOOL_NAMES[selGroup].filter(n => presentNames.has(n)).map(n => SCHOOL_COLORS[n] ?? "#999"),
  },
  marks: [
    Plot.line(peersAvg, {
      x: "year", y: "avg_acceptance_rate",
      stroke: "#ccc", strokeWidth: 1.5, strokeDasharray: "4,3"
    }),
    Plot.text([peersAvg.at(-1)], {
      x: "year", y: "avg_acceptance_rate",
      text: () => "LAC avg", fill: "#bbb", fontSize: 10, dx: 6, textAnchor: "start"
    }),
    Plot.ruleY([0]),
    Plot.line(selData, {
      x: "year", y: "acceptance_rate", stroke: "inst_name",
      strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.5,
      strokeOpacity: d => d.inst_name === "Bowdoin College" ? 1 : 0.7,
      tip: true, title: d => `${d.inst_name} ${d.year}: ${d.acceptance_rate?.toFixed(1)}%`,
    }),
    Plot.dot(selData.filter(d => d.year === selMax), {
      x: "year", y: "acceptance_rate", fill: "inst_name", r: 5
    }),
    Plot.text(selData.filter(d => d.year === selMax), {
      x: "year", y: "acceptance_rate",
      text: d => `${d.acceptance_rate?.toFixed(1)}%`,
      fontSize: 9, dx: 8, textAnchor: "start",
    }),
  ]
})
```

---

## Yield Rate {#yield}

```js
viewof yldGroup = Inputs.select(GROUP_LABELS, { value: "maine", label: "Show" })
```

```js
const yldData = filterGroup(yldGroup);
const yldMax  = Math.max(...yldData.map(d => d.year));

Plot.plot({
  width, height: 380,
  x: { tickFormat: "d", label: "Year" },
  y: { label: "Yield rate (%)", grid: true },
  color: {
    legend: true,
    domain: SCHOOL_NAMES[yldGroup].filter(n => presentNames.has(n)),
    range:  SCHOOL_NAMES[yldGroup].filter(n => presentNames.has(n)).map(n => SCHOOL_COLORS[n] ?? "#999"),
  },
  marks: [
    Plot.line(peersAvg, {
      x: "year", y: "avg_yield_rate",
      stroke: "#ccc", strokeWidth: 1.5, strokeDasharray: "4,3"
    }),
    Plot.text([peersAvg.at(-1)], {
      x: "year", y: "avg_yield_rate",
      text: () => "LAC avg", fill: "#bbb", fontSize: 10, dx: 6, textAnchor: "start"
    }),
    Plot.ruleY([0]),
    Plot.line(yldData, {
      x: "year", y: "yield_rate", stroke: "inst_name",
      strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.5,
      strokeOpacity: d => d.inst_name === "Bowdoin College" ? 1 : 0.7,
      tip: true, title: d => `${d.inst_name} ${d.year}: ${d.yield_rate?.toFixed(1)}%`,
    }),
    Plot.dot(yldData.filter(d => d.year === yldMax), {
      x: "year", y: "yield_rate", fill: "inst_name", r: 5
    }),
  ]
})
```

---

## Selectivity vs. Yield Scatter {#scatter}

High selectivity does not guarantee high yield. Schools above the horizontal line have above-average admitted-student preference.

```js
viewof scGroup = Inputs.select(GROUP_LABELS, { value: "maine", label: "Show" })
```

```js
const scData = filterGroup(scGroup);
const scMax  = Math.max(...scData.map(d => d.year));
const scPt   = scData.filter(d => d.year === scMax);

Plot.plot({
  width, height: 380,
  x: { label: "Acceptance rate (%) — lower = more selective →", reverse: true, grid: true },
  y: { label: "Yield rate (%) — higher = more preferred →", grid: true },
  marks: [
    Plot.ruleX([10], { stroke: "#eee", strokeDasharray: "4" }),
    Plot.ruleY([40], { stroke: "#eee", strokeDasharray: "4" }),
    Plot.dot(scPt, {
      x: "acceptance_rate", y: "yield_rate",
      fill: "color", r: 22, fillOpacity: 0.85,
      tip: true,
      title: d => `${d.inst_name}\nAcceptance: ${d.acceptance_rate?.toFixed(1)}%\nYield: ${d.yield_rate?.toFixed(1)}%`,
    }),
    Plot.text(scPt, {
      x: "acceptance_rate", y: "yield_rate",
      text: d => d.inst_name.replace(" College","").replace(" University",""),
      fill: "white", fontSize: 10, fontWeight: "600",
    }),
  ]
})
```

---

## Application Volume {#volume}

```js
viewof volGroup = Inputs.select(GROUP_LABELS, { value: "maine", label: "Show" })
```

```js
const volData = filterGroup(volGroup);
const volMax  = Math.max(...volData.map(d => d.year));

Plot.plot({
  width, height: 380,
  x: { tickFormat: "d", label: "Year" },
  y: { label: "Applications received", grid: true, tickFormat: "~s" },
  color: {
    legend: true,
    domain: SCHOOL_NAMES[volGroup].filter(n => presentNames.has(n)),
    range:  SCHOOL_NAMES[volGroup].filter(n => presentNames.has(n)).map(n => SCHOOL_COLORS[n] ?? "#999"),
  },
  marks: [
    Plot.ruleY([0]),
    Plot.line(volData, {
      x: "year", y: "applied", stroke: "inst_name",
      strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.5,
      strokeOpacity: d => d.inst_name === "Bowdoin College" ? 1 : 0.7,
      tip: true, title: d => `${d.inst_name} ${d.year}: ${d.applied?.toLocaleString()}`,
    }),
    Plot.dot(volData.filter(d => d.year === volMax), {
      x: "year", y: "applied", fill: "inst_name", r: 5
    }),
  ]
})
```

---

## 6-Year Graduation Rate {#gradrate}

```js
viewof gradGroup = Inputs.select(GROUP_LABELS, { value: "maine", label: "Show" })
```

```js
const gradData = filterGroup(gradGroup).filter(d => d.grad_rate_150 != null);
const gradMax  = Math.max(...gradData.map(d => d.year));

Plot.plot({
  width, height: 340,
  x: { tickFormat: "d", label: "Year" },
  y: { label: "6-year graduation rate (%)", grid: true },
  color: {
    legend: true,
    domain: SCHOOL_NAMES[gradGroup].filter(n => presentNames.has(n)),
    range:  SCHOOL_NAMES[gradGroup].filter(n => presentNames.has(n)).map(n => SCHOOL_COLORS[n] ?? "#999"),
  },
  marks: [
    Plot.line(peersAvg.filter(d => d.avg_grad_rate_150 != null), {
      x: "year", y: "avg_grad_rate_150",
      stroke: "#ccc", strokeWidth: 1.5, strokeDasharray: "4,3",
    }),
    Plot.ruleY([0]),
    Plot.line(gradData, {
      x: "year", y: "grad_rate_150", stroke: "inst_name",
      strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.5,
      strokeOpacity: d => d.inst_name === "Bowdoin College" ? 1 : 0.7,
      tip: true, title: d => `${d.inst_name} ${d.year}: ${d.grad_rate_150}%`,
    }),
    Plot.dot(gradData.filter(d => d.year === gradMax), {
      x: "year", y: "grad_rate_150", fill: "inst_name", r: 5
    }),
  ]
})
```

---

## Latest-Year Rankings Table {#rankings}

All metrics for the most recent year in the dataset, sortable by column.

```js
viewof rankGroup = Inputs.select(GROUP_LABELS, { value: "top20", label: "Show" })
```

```js
const rankMax  = Math.max(...filterGroup(rankGroup).map(d => d.year));
const rankRows = filterGroup(rankGroup)
  .filter(d => d.year === rankMax)
  .map(d => ({
    School:          d.inst_name,
    "Accept %":      d.acceptance_rate != null ? +d.acceptance_rate.toFixed(1) : null,
    "Yield %":       d.yield_rate      != null ? +d.yield_rate.toFixed(1)      : null,
    "Applications":  d.applied         != null ? Math.round(d.applied)         : null,
    "6yr Grad %":    d.grad_rate_150   != null ? +d.grad_rate_150.toFixed(1)   : null,
  }))
  .sort((a, b) => (a["Accept %"] ?? 99) - (b["Accept %"] ?? 99));  // default: most selective first

Inputs.table(rankRows, {
  format: {
    School: (v) => {
      const color = SCHOOL_COLORS[v] ?? "#888";
      const isBow = v === "Bowdoin College";
      return html`<span style="display:inline-flex;align-items:center;gap:6px;">
        <span style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;"></span>
        <span style="font-weight:${isBow ? 700 : 400};color:${isBow ? "#1B3D6E" : "inherit"}">${v}</span>
      </span>`;
    },
    "Accept %":  v => v != null ? `${v}%` : "—",
    "Yield %":   v => v != null ? `${v}%` : "—",
    "6yr Grad %":v => v != null ? `${v}%` : "—",
    "Applications": v => v != null ? v.toLocaleString() : "—",
  },
  width: { School: 240 },
})
```

---

## Maine Rivals Head-to-Head {#maine}

```js
const maineData = filterGroup("maine");
const maineMax  = Math.max(...maineData.map(d => d.year));
const maineDom  = SCHOOL_NAMES.maine.filter(n => presentNames.has(n));
const maineRng  = maineDom.map(n => SCHOOL_COLORS[n]);

html`
<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">

  <div>
    <div style="font-size:.85em;font-weight:600;margin-bottom:6px;color:#555;">Acceptance Rate</div>
    ${Plot.plot({ height: 200,
      x: { tickFormat: "d", label: null },
      y: { label: "%", grid: true },
      color: { legend: true, domain: maineDom, range: maineRng },
      marks: [
        Plot.ruleY([0]),
        Plot.line(maineData, {
          x: "year", y: "acceptance_rate", stroke: "inst_name",
          strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.8, tip: true
        }),
      ]
    })}
  </div>

  <div>
    <div style="font-size:.85em;font-weight:600;margin-bottom:6px;color:#555;">Yield Rate</div>
    ${Plot.plot({ height: 200,
      x: { tickFormat: "d", label: null },
      y: { label: "%", grid: true },
      color: { legend: false, domain: maineDom, range: maineRng },
      marks: [
        Plot.ruleY([0]),
        Plot.line(maineData, {
          x: "year", y: "yield_rate", stroke: "inst_name",
          strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.8, tip: true
        }),
      ]
    })}
  </div>

  <div>
    <div style="font-size:.85em;font-weight:600;margin-bottom:6px;color:#555;">Application Volume</div>
    ${Plot.plot({ height: 200,
      x: { tickFormat: "d", label: null },
      y: { label: "Apps", grid: true, tickFormat: "~s" },
      color: { legend: false, domain: maineDom, range: maineRng },
      marks: [
        Plot.ruleY([0]),
        Plot.line(maineData, {
          x: "year", y: "applied", stroke: "inst_name",
          strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.8, tip: true
        }),
      ]
    })}
  </div>

  <div>
    <div style="font-size:.85em;font-weight:600;margin-bottom:6px;color:#555;">6-Year Graduation Rate</div>
    ${Plot.plot({ height: 200,
      x: { tickFormat: "d", label: null },
      y: { label: "%", grid: true },
      color: { legend: false, domain: maineDom, range: maineRng },
      marks: [
        Plot.ruleY([0]),
        Plot.line(maineData.filter(d => d.grad_rate_150 != null), {
          x: "year", y: "grad_rate_150", stroke: "inst_name",
          strokeWidth: d => d.inst_name === "Bowdoin College" ? 3 : 1.8, tip: true
        }),
      ]
    })}
  </div>

</div>
`
```

*Peer data from IPEDS via the Urban Institute Education Data Portal (ODC-By license). Carnegie class 21 — Baccalaureate: Arts & Sciences Focus, private nonprofit.*
