# Section 2 — "What actually drives a country's happiness?"
# Responsive D3 dashboard (self-contained HTML): a life-evaluation line chart
# with a top toggle filter (turn country lines on/off + add any country),
# clickable per-line year-dots that cross-filter a driver-breakdown bar chart.
# Data + regression are precomputed here and embedded as JSON.
# Run from the repo root:  python3 charts/build_task2_drivers.py
import json
import pandas as pd, numpy as np

DATA = "charts/data/whr_2006_2025_cleaned.csv"
OUT  = "charts/task2_drivers.html"
df = pd.read_csv(DATA)
y = "life_evaluation"

# ---------- driver decomposition for every country-year (5 buckets) ----------
buckets = {
 "GDP per capita":           ["log_gdp"],
 "Healthy life expectancy":  ["hale"],
 "Social support":           ["social_support"],
 "Government effectiveness":  ["govt_effectv_score"],
 "Everything else":          ["freedom_make_choices", "generosity", "corruption_perception"],
}
DRIVERS = list(buckets.keys())
df["log_gdp"] = np.log(df["gdp_per_cap_ppp_2021_dollars"])
allvars = [v for vs in buckets.values() for v in vs]
sub = df.dropna(subset=[y] + allvars).copy()

X = sub[allvars].values
Xd = np.column_stack([np.ones(len(X)), X])
beta, *_ = np.linalg.lstsq(Xd, sub[y].values, rcond=None)
bmap = dict(zip(allvars, beta[1:]))
base = {v: sub[v].min() for v in allvars}   # dystopia baseline = world minimum

contrib = {}   # country -> year -> {le, d:{driver:pct}}
for _, r in sub.iterrows():
    le = float(r[y]); yr = int(r["year"])
    d = {b: round(100 * sum(bmap[v] * (r[v] - base[v]) for v in vs) / le, 1)
         for b, vs in buckets.items()}
    contrib.setdefault(r["country"], {})[yr] = {"le": round(le, 2), "d": d}

# ---------- line series: countries with >=8 yrs of data ----------
ld = df.dropna(subset=[y])[["country", "year", y]].copy()
ld = ld[ld.groupby("country")["year"].transform("count") >= 8].copy()
ld[y] = ld[y].round(3)
LINE = {}
for c, g in ld.groupby("country"):
    vals = g.sort_values("year")[["year", y]].values
    LINE[c] = [[int(a), float(b)] for a, b in vals]

latest = {c: pts[-1][1] for c, pts in LINE.items()}
order = sorted(latest, key=latest.get)
FEATURED = order[-3:][::-1] + order[:3]          # top 3 then bottom 3
COUNTRIES = sorted(LINE.keys())
YMIN = int(ld.year.min()); YMAX = int(ld.year.max())
TOPC = order[-1]
print("Featured:", FEATURED, "| default:", TOPC)

payload = {
    "LINE": LINE, "LATEST": {c: round(v, 2) for c, v in latest.items()},
    "CONTRIB": contrib, "COUNTRIES": COUNTRIES, "FEATURED": FEATURED,
    "DRIVERS": DRIVERS, "YMIN": YMIN, "YMAX": YMAX, "TOPC": TOPC,
}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  :root{--ink:#2f3542;--ink-soft:#6b7280;--line:#ece4d4;--sun:#f6b93b;--sun-deep:#e58e26;}
  *{box-sizing:border-box;}
  html,body{margin:0;background:#fff;color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
  #wrap{padding:14px 16px 18px;}
  h3{font-size:19px;font-weight:700;margin:2px 0 2px;}
  .sub{font-size:13px;color:var(--ink-soft);margin-bottom:10px;line-height:1.45;}
  /* top filter */
  .filter{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:4px 0 12px;}
  .filter .lab{font-size:12px;font-weight:600;color:var(--ink-soft);margin-right:2px;}
  .chip{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;
    border:1px solid var(--line);background:#fff;font-size:12px;font-weight:600;cursor:pointer;
    user-select:none;transition:opacity .12s,border-color .12s;}
  .chip .dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto;}
  .chip.off{opacity:.4;text-decoration:line-through;}
  .chip:hover{border-color:var(--sun);}
  select.add{font-size:12px;padding:3px 6px;border:1px solid var(--line);border-radius:8px;
    background:#fff;color:var(--ink);cursor:pointer;}
  svg{display:block;width:100%;overflow:visible;}
  .axis path,.axis line{stroke:var(--line);}
  .axis text{fill:var(--ink-soft);font-size:11px;}
  .axis .grid line{stroke:var(--line);stroke-opacity:.7;}
  .lbl{font-size:11.5px;font-weight:700;}
  .barlabel{font-size:12.5px;font-weight:700;fill:var(--ink);}
  .drvlabel{font-size:13px;fill:var(--ink);}
  .bhead{font-size:16px;font-weight:700;fill:var(--ink);}
  .tip{position:fixed;pointer-events:none;background:#fff;border:1px solid var(--line);
    border-radius:8px;padding:6px 9px;font-size:12px;color:var(--ink);
    box-shadow:0 4px 14px rgba(0,0,0,.10);opacity:0;transition:opacity .1s;z-index:5;}
  .dot-mark{cursor:pointer;stroke:#fff;stroke-width:1.2;}
  .secttitle{font-size:17px;font-weight:700;margin:18px 0 0;}
  .sectsub{font-size:12.5px;color:var(--ink-soft);margin:2px 0 4px;}
</style>
</head>
<body>
<div id="wrap">
  <h3>Life evaluation over time, 2006&ndash;2025</h3>
  <div class="sub">Top&nbsp;3 and bottom&nbsp;3 shown by default. Toggle a country chip to turn its line on or off, add any country from the dropdown, then click a year-dot on a line to break down that year below.</div>
  <div class="filter" id="filter"></div>
  <svg id="line"></svg>
  <div class="secttitle">What explains this country&rsquo;s happiness?</div>
  <div class="sectsub">Each driver&rsquo;s contribution to the score, vs. the world&rsquo;s lowest values (dystopia baseline). Click a year-dot above to change the country/year.</div>
  <svg id="bars"></svg>
</div>
<div class="tip" id="tip"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script>
const DATA = __PAYLOAD__;
const {LINE,LATEST,CONTRIB,COUNTRIES,FEATURED,DRIVERS,YMIN,YMAX,TOPC} = DATA;
const color = d3.scaleSequential(d3.interpolateRdYlGn).domain([2.5,8]);
const tip = d3.select("#tip");

const state = {
  active: new Map(FEATURED.map(c=>[c,true])),   // country -> visible?
  sel: {country:TOPC, year:latestYear(TOPC)}
};
function latestYear(c){ const ys=Object.keys(CONTRIB[c]||{}).map(Number); return ys.length?Math.max(...ys):YMAX; }
function contribFor(c,y){ const cc=CONTRIB[c]; if(!cc) return null; if(cc[y]) return {year:y,...cc[y]};
  const yr=latestYear(c); return cc[yr]?{year:yr,...cc[yr]}:null; }

function renderFilter(){
  const f=d3.select("#filter"); f.html("");
  f.append("span").attr("class","lab").text("Countries:");
  const order=[...state.active.keys()];
  f.selectAll("span.chip").data(order,d=>d).join("span")
    .attr("class",d=>"chip"+(state.active.get(d)?"":" off"))
    .on("click",(e,d)=>{ state.active.set(d,!state.active.get(d));
      if(!state.active.get(d) && state.sel.country===d){
        const on=[...state.active].filter(x=>x[1]).map(x=>x[0]);
        if(on.length) state.sel={country:on[0],year:latestYear(on[0])};
      }
      draw(); })
    .each(function(d){ const el=d3.select(this); el.html("");
      el.append("span").attr("class","dot").style("background",color(LATEST[d]));
      el.append("span").text(d); });
  // add dropdown
  const sel=f.append("select").attr("class","add").on("change",function(){
    const c=this.value; if(c){ state.active.set(c,true);
      state.sel={country:c,year:latestYear(c)}; this.value=""; draw(); } });
  sel.append("option").attr("value","").text("+ Add country…");
  sel.selectAll("option.opt").data(COUNTRIES.filter(c=>!state.active.has(c)))
    .join("option").attr("class","opt").attr("value",d=>d).text(d=>d);
}

function drawLine(){
  const svg=d3.select("#line"); svg.selectAll("*").remove();
  const W=svg.node().clientWidth||820, H=380;
  const m={t:8,r:120,b:28,l:34};
  const iw=W-m.l-m.r, ih=H-m.t-m.b;
  svg.attr("height",H);
  const g=svg.append("g").attr("transform",`translate(${m.l},${m.t})`);
  const x=d3.scaleLinear().domain([YMIN,YMAX]).range([0,iw]);
  const yv=d3.scaleLinear().domain([1,8.2]).range([ih,0]);
  // grid + axes
  g.append("g").attr("class","axis grid").call(d3.axisLeft(yv).tickValues(d3.range(1,9))
      .tickSize(-iw).tickFormat(d3.format("d")))
    .call(s=>s.select(".domain").remove());
  g.append("g").attr("class","axis").attr("transform",`translate(0,${ih})`)
    .call(d3.axisBottom(x).tickValues(d3.range(YMIN,YMAX+1,2)).tickFormat(d3.format("d")));
  g.append("text").attr("x",-ih/2).attr("y",-26).attr("transform","rotate(-90)")
    .attr("text-anchor","middle").style("font-size","12px").style("font-weight","600")
    .attr("fill","var(--ink)").text("Life evaluation");

  const on=[...state.active].filter(d=>d[1]).map(d=>d[0]);
  const line=d3.line().x(d=>x(d[0])).y(d=>yv(d[1]));

  // stagger end labels that collide
  const ends=on.map(c=>({c,val:LINE[c][LINE[c].length-1][1]})).sort((a,b)=>b.val-a.val);
  const GAP=(8.2-1)/ih*16; let placed=null;
  ends.forEach(e=>{ e.ly=(placed!==null && placed-e.val<GAP)?placed-GAP:e.val; placed=e.ly; });
  const lyMap=new Map(ends.map(e=>[e.c,e.ly]));

  on.forEach(c=>{
    const pts=LINE[c], col=color(LATEST[c]);
    g.append("path").attr("d",line(pts)).attr("fill","none")
      .attr("stroke",col).attr("stroke-width",c===state.sel.country?3.4:2.2)
      .attr("opacity",c===state.sel.country?1:.9);
    // end label
    const last=pts[pts.length-1];
    g.append("text").attr("class","lbl").attr("x",x(last[0])+7).attr("y",yv(lyMap.get(c))+4)
      .attr("fill",col).text(c);
    // dots
    g.selectAll(null).data(pts.map(p=>({c,year:p[0],le:p[1]}))).join("circle")
      .attr("class","dot-mark").attr("cx",d=>x(d.year)).attr("cy",d=>yv(d.le))
      .attr("r",d=>(d.c===state.sel.country&&d.year===state.sel.year)?7:3.4)
      .attr("fill",d=>color(d.le))
      .attr("stroke",d=>(d.c===state.sel.country&&d.year===state.sel.year)?"var(--ink)":"#fff")
      .attr("stroke-width",d=>(d.c===state.sel.country&&d.year===state.sel.year)?2:1.2)
      .on("click",(e,d)=>{ state.sel={country:d.c,year:d.year}; draw(); })
      .on("mousemove",(e,d)=>{ tip.style("opacity",1)
        .style("left",(e.clientX+12)+"px").style("top",(e.clientY+12)+"px")
        .html(`<b>${d.c}</b><br>${d.year} · life eval ${d.le.toFixed(2)}`); })
      .on("mouseleave",()=>tip.style("opacity",0));
  });
}

function drawBars(){
  const svg=d3.select("#bars"); svg.selectAll("*").remove();
  const W=svg.node().clientWidth||820, H=250;
  const m={t:34,r:64,b:30,l:168};
  const iw=W-m.l-m.r, ih=H-m.t-m.b;
  svg.attr("height",H);
  const data=contribFor(state.sel.country,state.sel.year);
  const g=svg.append("g").attr("transform",`translate(${m.l},${m.t})`);
  // header
  svg.append("text").attr("class","bhead").attr("x",4).attr("y",20)
    .text(data?`${state.sel.country} — ${data.year} · life evaluation ${data.le.toFixed(2)}`:"");
  if(!data){ return; }
  const rows=DRIVERS.map(d=>({driver:d,pct:data.d[d]})).sort((a,b)=>b.pct-a.pct);
  const x=d3.scaleLinear().domain([-20,40]).range([0,iw]);
  const yb=d3.scaleBand().domain(rows.map(r=>r.driver)).range([0,ih]).padding(0.28);
  g.append("g").attr("class","axis").attr("transform",`translate(0,${ih})`)
    .call(d3.axisBottom(x).tickValues(d3.range(-20,41,10)).tickFormat(d=>d+"%"));
  g.append("line").attr("x1",x(0)).attr("x2",x(0)).attr("y1",0).attr("y2",ih)
    .attr("stroke","var(--line)");
  g.append("text").attr("x",iw/2).attr("y",ih+26).attr("text-anchor","middle")
    .style("font-size","12px").style("font-weight","600").attr("fill","var(--ink)")
    .text("Share of life-evaluation score explained (%)");
  const cbar=color(data.le);
  g.selectAll("rect").data(rows).join("rect")
    .attr("y",d=>yb(d.driver)).attr("height",yb.bandwidth())
    .attr("x",d=>x(Math.min(0,d.pct))).attr("width",d=>Math.abs(x(d.pct)-x(0)))
    .attr("rx",3).attr("fill",cbar);
  g.selectAll("text.dl").data(rows).join("text").attr("class","drvlabel")
    .attr("x",-10).attr("y",d=>yb(d.driver)+yb.bandwidth()/2+4).attr("text-anchor","end")
    .text(d=>d.driver);
  g.selectAll("text.bl").data(rows).join("text").attr("class","barlabel")
    .attr("x",d=>x(d.pct)+(d.pct>=0?5:-5)).attr("text-anchor",d=>d.pct>=0?"start":"end")
    .attr("y",d=>yb(d.driver)+yb.bandwidth()/2+4).text(d=>d.pct.toFixed(1)+"%");
}

function postHeight(){ const h=document.body.scrollHeight;
  if(window.parent) window.parent.postMessage({type:"task2-resize",height:h+6},"*"); }

function draw(){ renderFilter(); drawLine(); drawBars(); postHeight(); }
draw();
let rt; window.addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(draw,120);});
</script>
</body>
</html>
"""

html = HTML.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
with open(OUT, "w") as f:
    f.write(html)
print("saved", OUT, f"({len(html)//1024} KB)")
