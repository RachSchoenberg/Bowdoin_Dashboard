---
title: Bowdoin Deep Dive
theme: dashboard
---

```js
const raw      = await FileAttachment("data/bowdoin_cds.csv").csv({ typed: true });
const peersAvg = await FileAttachment("data/peers_avg.csv").csv({ typed: true });
const cur      = raw[raw.length - 1];
```

# Bowdoin College — Full Data Profile

All data from published Common Data Sets, 2001–${cur.year}.

---

## Application Pipeline {#pipeline}

```js
viewof genderView = Inputs.radio(["Total","Men","Women"], { value: "Total", label: "Show" })
```

```js
const appKey = genderView === "Men" ? "apps_men"     : genderView === "Women" ? "apps_women"     : "total_apps";
const admKey = genderView === "Men" ? "admits_men"   : genderView === "Women" ? "admits_women"   : "total_admits";
const enrKey = genderView === "Men" ? "enrolled_men" : genderView === "Women" ? "enrolled_women" : "total_enrolled";

Plot.plot({
  width, height: 300,
  x: { tickFormat: "d", label: "Entering class" },
  y: { label: "Students", grid: true, tickFormat: "~s" },
  marks: [
    Plot.ruleY([0]),
    Plot.line(raw, { x: "year", y: appKey, stroke: "#1B3D6E", strokeWidth: 2.5, tip: true, title: d => `Applications: ${d[appKey]?.toLocaleString()}` }),
    Plot.line(raw, { x: "year", y: admKey, stroke: "#4A7FC1", strokeWidth: 2,   tip: true, title: d => `Admitted: ${d[admKey]?.toLocaleString()}` }),
    Plot.line(raw, { x: "year", y: enrKey, stroke: "#C5A028", strokeWidth: 2,   tip: true, title: d => `Enrolled: ${d[enrKey]?.toLocaleString()}` }),
    Plot.dot(raw.slice(-1), { x: "year", y: appKey, fill: "#1B3D6E", r: 5 }),
    Plot.dot(raw.slice(-1), { x: "year", y: admKey, fill: "#4A7FC1", r: 5 }),
    Plot.dot(raw.slice(-1), { x: "year", y: enrKey, fill: "#C5A028", r: 5 }),
  ]
})
```

```js
// Stacked enrolled gender
const genderData = raw.flatMap(d => [
  { year: d.year, group: "Men",   value: d.enrolled_men },
  { year: d.year, group: "Women", value: d.enrolled_women },
]);
Plot.plot({
  width, height: 150,
  x: { tickFormat: "d", label: "Entering class" },
  y: { label: "Enrolled", grid: false },
  color: { legend: true, domain: ["Men","Women"], range: ["#1B3D6E","#93B7D9"] },
  marks: [
    Plot.barY(genderData, Plot.stackY({ x: "year", y: "value", fill: "group", tip: true, title: d => `${d.group}: ${d.value}` })),
    Plot.ruleY([0]),
  ]
})
```

---

### Early Decision {#ed}

```js
const edRate = raw.filter(d => d.ed_apps && d.ed_admits)
  .map(d => ({ ...d, ed_rate: d.ed_admits / d.ed_apps * 100 }));

Plot.plot({
  width, height: 260,
  x: { tickFormat: "d", label: "Entering class" },
  y: { label: "Students / Rate", grid: true },
  marks: [
    Plot.ruleY([0]),
    Plot.line(edRate, { x: "year", y: "ed_apps",   stroke: "#1B3D6E", strokeWidth: 2.5, tip: true, title: d => `ED apps: ${d.ed_apps}` }),
    Plot.line(edRate, { x: "year", y: "ed_admits", stroke: "#4A7FC1", strokeWidth: 2,   tip: true, title: d => `ED admits: ${d.ed_admits}` }),
    Plot.line(edRate, { x: "year", y: "ed_rate",   stroke: "#C5A028", strokeWidth: 2, strokeDasharray:"5,3", tip: true, title: d => `ED rate: ${d.ed_rate.toFixed(1)}%` }),
  ]
})
```

---

## Selectivity & Yield {#selectivity}

```js
Plot.plot({
  width, height: 220,
  x: { tickFormat: "d", label: "Entering class" },
  y: { label: "Rate (%)", grid: true },
  color: { legend: true, domain: ["Acceptance rate","Yield rate","LAC peer avg (acceptance)"], range: ["#1B3D6E","#C5A028","#ccc"] },
  marks: [
    // Peer average benchmark
    Plot.line(peersAvg, { x: "year", y: "avg_acceptance_rate", stroke: "#ccc", strokeWidth: 1.5, strokeDasharray: "4,3",
      tip: true, title: d => `LAC avg ${d.year}: ${d.avg_acceptance_rate?.toFixed(1)}% (n=${d.n_institutions})` }),
    Plot.ruleY([0]),
    Plot.line(raw, { x: "year", y: "accept_rate", stroke: "#1B3D6E", strokeWidth: 2.5, tip: true, title: d => `Acceptance: ${d.accept_rate}%` }),
    Plot.line(raw, { x: "year", y: "yield_rate",  stroke: "#C5A028", strokeWidth: 2, strokeDasharray:"5,3", tip: true, title: d => `Yield: ${d.yield_rate}%` }),
    Plot.dot(raw.slice(-1), { x: "year", y: "accept_rate", fill: "#1B3D6E", r: 5 }),
    Plot.dot(raw.slice(-1), { x: "year", y: "yield_rate",  fill: "#C5A028", r: 5 }),
  ]
})
```

---

## Geographic Reach {#geography}

```js
viewof geoView = Inputs.radio(["Enrolled (all years)","Applications (2023–2025 only)"], {
  value: "Enrolled (all years)", label: "View"
})
```

```js
if (geoView === "Enrolled (all years)") {
  const geoData = raw.flatMap(d => [
    { year: d.year, group: "In-state",      value: d.enrolled_instate },
    { year: d.year, group: "Out-of-state",  value: d.enrolled_outofstate },
    { year: d.year, group: "International", value: d.enrolled_intl },
  ]).filter(d => d.value != null);

  display(Plot.plot({
    width, height: 280,
    x: { tickFormat: "d", label: "Entering class" },
    y: { label: "Students enrolled", grid: true },
    color: { legend: true, domain: ["In-state","Out-of-state","International"], range: ["#1B3D6E","#4A7FC1","#C5A028"] },
    marks: [
      Plot.ruleY([0]),
      Plot.line(geoData, { x: "year", y: "value", stroke: "group", strokeWidth: 2, tip: true }),
      Plot.dot(geoData.filter(d => d.year === Math.max(...geoData.map(g => g.year))), { x: "year", y: "value", fill: "group", r: 5 }),
    ]
  }));
} else {
  const geoApps = raw.filter(d => d.apps_instate).flatMap(d => [
    { year: String(d.year), segment: "In-state",      apps: d.apps_instate,    enrolled: d.enrolled_instate },
    { year: String(d.year), segment: "Out-of-state",  apps: d.apps_outofstate, enrolled: d.enrolled_outofstate },
    { year: String(d.year), segment: "International", apps: d.apps_intl,       enrolled: d.enrolled_intl },
  ]);
  display(html`
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
      <div>
        <div style="font-size:.85em;font-weight:600;margin-bottom:8px;color:#555;">Applications by Origin</div>
        ${Plot.plot({ height:220, x:{label:null}, y:{label:"Applications",grid:true,tickFormat:"~s"},
          color:{legend:true,domain:["In-state","Out-of-state","International"],range:["#1B3D6E","#4A7FC1","#C5A028"]},
          marks:[Plot.barY(geoApps.map(d=>({...d,value:d.apps})),Plot.stackY({x:"year",y:"value",fill:"segment",tip:true})),Plot.ruleY([0])] })}
      </div>
      <div>
        <div style="font-size:.85em;font-weight:600;margin-bottom:8px;color:#555;">Enrolled by Origin</div>
        ${Plot.plot({ height:220, x:{label:null}, y:{label:"Enrolled",grid:true},
          color:{legend:false,domain:["In-state","Out-of-state","International"],range:["#1B3D6E","#4A7FC1","#C5A028"]},
          marks:[Plot.barY(geoApps.map(d=>({...d,value:d.enrolled})),Plot.stackY({x:"year",y:"value",fill:"segment",tip:true})),Plot.ruleY([0])] })}
      </div>
    </div>
  `);
}
```

---

## Class Composition by Ethnicity {#diversity}

```js
viewof ethYear = Inputs.range(
  [d3.min(raw, d => d.year), d3.max(raw, d => d.year)],
  { step: 1, value: d3.max(raw, d => d.year), label: "Entering class" }
)
```

```js
viewof ethMode = Inputs.radio(["Count","Percent"], { value: "Count", label: "Show as" })
```

```js
{
  const ETH_FIELDS = [
    { key: "enroll_white",        label: "White" },
    { key: "enroll_hispanic",     label: "Hispanic/Latino" },
    { key: "enroll_black",        label: "Black/African American" },
    { key: "enroll_asian",        label: "Asian" },
    { key: "enroll_two_or_more",  label: "Two or More Races" },
    { key: "enroll_unknown",      label: "Unknown/Unreported" },
    { key: "enroll_aian",         label: "Amer. Indian/Alaska Native" },
    { key: "enroll_nhpi",         label: "Native Hawaiian/Pacific Isl." },
  ];
  const ETH_COLORS = ["#1B3D6E","#F97316","#8B5CF6","#06B6D4","#10B981","#94A3B8","#EF4444","#F59E0B"];

  const W = width, H = 440, R = Math.min(W / 2.2, 180);
  const cx = W * 0.38, cy = H / 2;

  function sliceValues(year) {
    const row   = raw.find(d => d.year === year) ?? raw[raw.length - 1];
    const total = ETH_FIELDS.reduce((s, f) => s + (row[f.key] ?? 0), 0);
    return ETH_FIELDS.map((f, i) => ({
      label: f.label, color: ETH_COLORS[i],
      raw:   row[f.key] ?? 0,
      pct:   total > 0 ? (row[f.key] ?? 0) / total * 100 : 0,
    }));
  }

  const arc    = d3.arc().innerRadius(R * 0.52).outerRadius(R);
  const arcHov = d3.arc().innerRadius(R * 0.52).outerRadius(R * 1.06);
  const pie    = d3.pie().value(d => d.raw).sort(null);

  const svg = d3.create("svg").attr("width", W).attr("height", H)
    .style("font-family","system-ui,sans-serif");

  const centreYear  = svg.append("text").attr("x",cx).attr("y",cy-10)
    .attr("text-anchor","middle").attr("font-size",22).attr("font-weight",800).attr("fill","#1B3D6E");
  const centreTotal = svg.append("text").attr("x",cx).attr("y",cy+14)
    .attr("text-anchor","middle").attr("font-size",12).attr("fill","#888");

  const gArcs = svg.append("g").attr("transform",`translate(${cx},${cy})`);

  const tip = d3.select(document.body).append("div")
    .style("position","fixed").style("pointer-events","none")
    .style("background","rgba(0,0,0,.78)").style("color","#fff")
    .style("padding","7px 11px").style("border-radius","6px")
    .style("font-size","12px").style("line-height","1.5")
    .style("opacity",0).style("z-index",9999);

  const legendX = cx + R + 28, legendY = cy - (ETH_FIELDS.length * 18) / 2;
  const gLegend = svg.append("g");
  ETH_FIELDS.forEach((f, i) => {
    const g = gLegend.append("g").attr("transform",`translate(${legendX},${legendY + i*22})`);
    g.append("rect").attr("width",11).attr("height",11).attr("rx",2).attr("fill",ETH_COLORS[i]);
    g.append("text").attr("x",16).attr("y",10).attr("font-size",11).attr("fill","#444").text(f.label);
  });

  function update(year, mode) {
    const data  = sliceValues(year);
    const arcs  = pie(data);
    const total = data.reduce((s,d) => s + d.raw, 0);
    const isPct = mode === "Percent";

    centreYear.text(year);
    centreTotal.text(`n = ${total.toLocaleString()}`);

    const paths = gArcs.selectAll("path").data(arcs, d => d.data.label);

    const onEnter = (sel) => sel
      .on("mousemove", (event, d) => {
        tip.style("opacity",1)
          .style("left",(event.clientX+14)+"px").style("top",(event.clientY-28)+"px")
          .html(`<strong>${d.data.label}</strong><br>${d.data.raw.toLocaleString()} students (${d.data.pct.toFixed(1)}%)`);
        d3.select(event.currentTarget).transition().duration(120).attr("d", arcHov(d));
      })
      .on("mouseleave", (event, d) => {
        tip.style("opacity",0);
        d3.select(event.currentTarget).transition().duration(120).attr("d", arc(d));
      });

    paths.enter().append("path")
      .attr("fill", d => d.data.color).attr("stroke","#fff").attr("stroke-width",1.5)
      .attr("d", d3.arc().innerRadius(R*.52).outerRadius(R*.52))
      .call(onEnter)
      .transition().duration(600).attrTween("d", function(d) {
        const i = d3.interpolate({startAngle:d.startAngle,endAngle:d.startAngle}, d);
        return t => arc(i(t));
      });

    paths.call(onEnter)
      .transition().duration(600).attrTween("d", function(d) {
        const prev = this._current ?? d; this._current = d;
        const i = d3.interpolate(prev, d);
        return t => arc(i(t));
      });

    paths.exit().transition().duration(400)
      .attrTween("d", function(d) {
        const i = d3.interpolate(d,{startAngle:d.endAngle,endAngle:d.endAngle});
        return t => arc(i(t));
      }).remove();

    gLegend.selectAll(".lval").remove();
    data.forEach((d,i) => {
      gLegend.select(`g:nth-child(${i+1})`).append("text").attr("class","lval")
        .attr("x",16).attr("y",22).attr("font-size",10).attr("fill","#888")
        .text(isPct ? `${d.pct.toFixed(1)}%` : d.raw.toLocaleString());
    });
  }

  update(ethYear, ethMode);
  invalidation.then(() => tip.remove());
  display(svg.node());
}
```

---

## Degrees Conferred by Field {#degrees}

```js
const DEG_FIELDS = [
  { key:"deg_pct_social_sciences",          label:"Social Sciences" },
  { key:"deg_pct_biological_life_sciences", label:"Biology & Life Sciences" },
  { key:"deg_pct_physical_sciences",        label:"Physical Sciences" },
  { key:"deg_pct_mathematics",              label:"Mathematics & Statistics" },
  { key:"deg_pct_computer_info_sciences",   label:"Computer Science" },
  { key:"deg_pct_area_ethnic_studies",      label:"Ethnic & Area Studies" },
  { key:"deg_pct_visual_performing_arts",   label:"Visual & Performing Arts" },
  { key:"deg_pct_english",                  label:"English" },
  { key:"deg_pct_history",                  label:"History" },
  { key:"deg_pct_natural_resources",        label:"Natural Resources" },
  { key:"deg_pct_foreign_languages",        label:"Foreign Languages" },
  { key:"deg_pct_psychology",               label:"Psychology" },
  { key:"deg_pct_interdisciplinary",        label:"Interdisciplinary Studies" },
  { key:"deg_pct_philosophy_religion",      label:"Philosophy & Religion" },
  { key:"deg_diploma_pct_education",        label:"Education" },
];
const degData = raw.flatMap(d =>
  DEG_FIELDS.filter(f => d[f.key] != null && d[f.key] !== "")
    .map(f => ({ year: d.year, field: f.label, pct: +d[f.key] }))
);

Plot.plot({
  width, height: 420, marginLeft: 200,
  x: { tickFormat:"d", label:"Entering class", ticks:8 },
  y: { label: null },
  color: { scheme:"Blues", label:"Share of degrees (%)", legend:true, domain:[0,35] },
  marks: [
    Plot.cell(degData, { x:"year", y:"field", fill:"pct", tip:true, title:d=>`${d.field}\n${d.year}: ${d.pct.toFixed(1)}%` }),
    Plot.text(degData.filter(d=>d.pct>=8), { x:"year", y:"field", text:d=>d.pct.toFixed(0), fill:d=>d.pct>22?"white":"#333", fontSize:9 }),
  ]
})
```

---

## Institutional Health {#institutional}

```js
const retData  = raw.filter(d => d.retention_rate != null && d.retention_rate !== "");
const gradData = raw.filter(d => d.grad_rate_6yr  != null && d.grad_rate_6yr  !== "");

Plot.plot({
  width, height:260,
  x:{tickFormat:"d", label:"Entering class"},
  y:{label:"Rate (%)", grid:true, domain:[80,102]},
  marks:[
    Plot.ruleY([0]),
    Plot.line(retData,  {x:"year",y:"retention_rate",stroke:"#1B3D6E",strokeWidth:2.5,tip:true,title:d=>`Retention: ${d.retention_rate}%`}),
    Plot.dot(retData,   {x:"year",y:"retention_rate",fill:"#1B3D6E",r:3}),
    Plot.line(gradData, {x:"year",y:"grad_rate_6yr", stroke:"#C5A028",strokeWidth:2.5,strokeDasharray:"5,3",tip:true,title:d=>`6yr grad: ${d.grad_rate_6yr}%`}),
    Plot.dot(gradData,  {x:"year",y:"grad_rate_6yr", fill:"#C5A028",r:3}),
  ]
})
```

```js
Plot.plot({
  width, height:200,
  x:{tickFormat:"d", label:"Year"},
  y:{label:"Total undergraduates", grid:true, domain:[1500,2100]},
  marks:[
    Plot.ruleY([0]),
    Plot.line(raw, {x:"year",y:"total_undergrad",stroke:"#2E5FA3",strokeWidth:2.5,tip:true}),
    Plot.dot(raw,  {x:"year",y:"total_undergrad",fill:"#2E5FA3",r:3}),
  ]
})
```

*Source: Bowdoin College Common Data Sets, 2001–${cur.year}.*