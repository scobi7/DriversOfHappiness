# Drivers of Happiness

DATASCI 209 final project — a site exploring the drivers of happiness using World Happiness Report data.

This is a plain static site (HTML + CSS, no framework, no build step). `index.html` contains a labeled `[placeholder]` box for every text block, chart, and interactive component from the project plan — replace each box with real content as it's ready.

## Running locally

No install needed. Either open `index.html` directly in a browser, or serve the folder (needed once you load data files with D3, since `fetch` doesn't work over `file://`):

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Project structure

```
index.html    — the whole page: intro + Task 1–6 sections with placeholders
styles.css    — theme (warm/sunny palette), placeholder + viz container styles
charts/       — put D3 scripts, exported Altair HTML files, and data here
```

## How to embed each visualization type

Replace a `[placeholder]` div in `index.html` with one of these patterns.

### D3

Give the chart a container div, load D3, and load your chart script (which selects the div and draws into it):

```html
<div id="happiness-map" class="viz"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="charts/happiness-map.js"></script>
```

And in `charts/happiness-map.js`:

```js
const svg = d3.select("#happiness-map")
  .append("svg")
  .attr("viewBox", "0 0 900 500");
// ...draw the chart...
```

Put CSVs/JSON in `charts/data/` and load them with `d3.csv("charts/data/whr.csv")`. Script tags load in order, so keep the D3 CDN tag above your chart scripts (or load them once near the end of `<body>`).

### Altair

Easiest route: export each chart as a standalone HTML file from Python, commit it to `charts/`, and iframe it in:

```python
chart.save("charts/gdp-vs-happiness.html")
```

```html
<iframe src="charts/gdp-vs-happiness.html" class="viz-frame"
        loading="lazy" title="GDP vs happiness"></iframe>
```

Interactivity (tooltips, selections, dropdowns bound to the chart) survives the export. If an iframe shows scrollbars, bump its height with an inline style: `style="min-height: 620px"`.

### Tableau

Publish the workbook to Tableau Public, then click **Share → Embed Code** and paste the entire snippet (the `<div class='tableauPlaceholder'>...` plus `<script>`) where the placeholder was. Or use the share link in an iframe:

```html
<iframe src="https://public.tableau.com/views/YourWorkbook/YourSheet?:embed=y&:showVizHome=no"
        class="viz-frame" loading="lazy" style="min-height: 640px"
        title="My Tableau viz"></iframe>
```

Note: viewers load Tableau embeds from Tableau's servers, so the workbook must stay published on Tableau Public.

## Deploying to Vercel

Static sites need zero configuration. Two options:

**Option A — GitHub integration (recommended for a team):** push this repo to GitHub, then at [vercel.com/new](https://vercel.com/new) import the repo. Framework preset: **Other**; leave build command and output directory empty. Every push to `main` auto-deploys, and PRs get preview URLs.

**Option B — CLI:**

```bash
npm i -g vercel
vercel          # preview deploy
vercel --prod   # production deploy
```

## Placeholder key

- `[text — ...]` written description/prose
- `[map — ...]`, `[chart — ...]`, `[list — ...]`, `[slopegraph — ...]`, `[bar charts — ...]` visualizations
- `[component — ...]` interactive controls (selectors, toggles, click behavior)
