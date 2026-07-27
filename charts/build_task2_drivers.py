# Section 2 — "What actually drives a country's happiness?"
# Multi-line life-evaluation chart (top-3 / bottom-3 highlighted, all countries
# shown faintly, color = life evaluation) + a country dropdown filter + clickable
# year-dots that drill into that country-year's driver breakdown.
# Run from the repo root:  python3 charts/build_task2_drivers.py
import math
import pandas as pd, numpy as np, altair as alt
alt.data_transformers.disable_max_rows()

DATA = "charts/data/whr_2006_2025_cleaned.csv"
OUT  = "charts/task2_drivers.html"
WIDTH = 840
df = pd.read_csv(DATA)
y = "life_evaluation"

# ---------- site theme (matches task1.ipynb / styles.css) ----------
SITE_FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
INK, INK_SOFT, LINE = "#2f3542", "#6b7280", "#ece4d4"
def site_theme(chart):
    return (
        chart.configure(font=SITE_FONT, background="white")
        .configure_view(stroke=None)
        .configure_title(anchor="start", color=INK, fontSize=19, fontWeight=700,
                         subtitleColor=INK_SOFT, subtitleFontSize=13, subtitlePadding=6, offset=14)
        .configure_axis(labelColor=INK_SOFT, titleColor=INK, labelFontSize=12, titleFontSize=13,
                        gridColor=LINE, domainColor=LINE, tickColor=LINE)
        .configure_legend(titleColor=INK, labelColor=INK_SOFT, titleFontSize=12, labelFontSize=11,
                          gradientLength=200, gradientThickness=10)
    )

CSCALE = alt.Scale(scheme="redyellowgreen", domain=[2.5, 8])

# ---------- driver decomposition for EVERY country-year (5 buckets) ----------
buckets = {
 "GDP per capita":           ["log_gdp"],
 "Healthy life expectancy":  ["hale"],
 "Social support":           ["social_support"],
 "Government effectiveness":  ["govt_effectv_score"],
 "Everything else":          ["freedom_make_choices", "generosity", "corruption_perception"],
}
df["log_gdp"] = np.log(df["gdp_per_cap_ppp_2021_dollars"])
allvars = [v for vs in buckets.values() for v in vs]
sub = df.dropna(subset=[y] + allvars).copy()

X = sub[allvars].values
Xd = np.column_stack([np.ones(len(X)), X])
beta, *_ = np.linalg.lstsq(Xd, sub[y].values, rcond=None)
bmap = dict(zip(allvars, beta[1:]))
base = {v: sub[v].min() for v in allvars}   # dystopia baseline = world minimum

rows = []
for _, r in sub.iterrows():
    le = r[y]
    for bname, vs in buckets.items():
        contrib = sum(bmap[v] * (r[v] - base[v]) for v in vs)
        rows.append({"country": r["country"], "year": int(r["year"]), "driver": bname,
                     "pct": round(100 * contrib / le, 1), "life_eval": round(le, 2)})
contrib_df = pd.DataFrame(rows)
xlo = math.floor(contrib_df.pct.min() / 5) * 5
xhi = math.ceil(contrib_df.pct.max() / 5) * 5

# ---------- line data: all countries with >=8 yrs of data ----------
line_df = df.dropna(subset=[y])[["country", "year", y]].copy()
counts = line_df.groupby("country")["year"].transform("count")
line_df = line_df[counts >= 8].copy()
line_df[y] = line_df[y].round(3)
last_year = line_df.groupby("country")["year"].transform("max")
line_df["is_last"] = (line_df["year"] == last_year)
latest_val = line_df.loc[line_df["is_last"], ["country", y]].rename(columns={y: "le_latest"})
line_df = line_df.merge(latest_val, on="country", how="left")

# top-3 & bottom-3 by latest life evaluation
final = latest_val.sort_values("le_latest")
top_country = final.tail(1)["country"].iloc[0]
featured = list(final.tail(3)["country"]) + list(final.head(3)["country"])
line_df["featured"] = line_df["country"].isin(featured)
all_countries = sorted(line_df["country"].unique().tolist())

# stagger end-labels down when featured lines end at nearly the same value
GAP = 0.34
label_y_map = {}
placed = None
for _, r in latest_val[latest_val.country.isin(featured)].sort_values(
        "le_latest", ascending=False).iterrows():
    yv = r["le_latest"] if (placed is None or placed - r["le_latest"] >= GAP) else placed - GAP
    label_y_map[r["country"]] = yv
    placed = yv
line_df["label_y"] = line_df["country"].map(label_y_map).fillna(line_df["le_latest"])
YMIN, YMAX = int(line_df.year.min()), int(line_df.year.max())
print("Featured:", featured, "| default:", top_country)

# ---------- selections ----------
# country dropdown (Tableau-style filter)
sel_country = alt.selection_point(
    fields=["country"], value=top_country,
    bind=alt.binding_select(options=all_countries, name="Country:  "))
# clicked year -> drives the breakdown (default = latest year)
sel_year = alt.selection_point(fields=["year"], on="click", empty=False,
                               value=[{"year": YMAX}])

x_enc = alt.X("year:O", title="Year",
             axis=alt.Axis(values=list(range(YMIN, YMAX + 1, 2)), labelAngle=0))
y_enc = alt.Y(f"{y}:Q", title="Life evaluation",
              scale=alt.Scale(domain=[1, 8.3]), axis=alt.Axis(values=[1,2,3,4,5,6,7,8]))
color_le = alt.Color("le_latest:Q", scale=CSCALE,
                     legend=alt.Legend(title="Life evaluation", orient="top",
                                       direction="horizontal", titleLimit=180))

# 1) faint context: every country
ctx = alt.Chart(line_df).mark_line(color="#d9dde3", strokeWidth=1, opacity=0.45).encode(
    x=x_enc, y=y_enc, detail="country:N")

# 2) featured top-3 / bottom-3, always highlighted + labeled
feat = alt.Chart(line_df).transform_filter("datum.featured").mark_line(
    strokeWidth=2.4).encode(x=x_enc, y=y_enc, detail="country:N", color=color_le)
feat_lbl = alt.Chart(line_df).transform_filter("datum.featured").transform_filter(
    "datum.is_last").mark_text(align="left", dx=6, fontSize=11, fontWeight=600).encode(
    x=x_enc, y=alt.Y("label_y:Q"), text="country:N",
    color=alt.Color("le_latest:Q", scale=CSCALE, legend=None))

# 3) the dropdown-selected country: emphasized line + clickable year dots
sel_line = alt.Chart(line_df).transform_filter(sel_country).mark_line(
    strokeWidth=3.4).encode(x=x_enc, y=y_enc, detail="country:N",
    color=alt.Color("le_latest:Q", scale=CSCALE, legend=None))
sel_lbl = alt.Chart(line_df).transform_filter(sel_country).transform_filter(
    "datum.is_last").transform_filter("datum.featured == false").mark_text(
    align="left", dx=6, fontSize=12.5, fontWeight=700, color=INK).encode(
    x=x_enc, y=alt.Y("label_y:Q"), text="country:N")
sel_dots = alt.Chart(line_df).transform_filter(sel_country).mark_point(
    filled=True, stroke="white", strokeWidth=1).encode(
    x=x_enc, y=y_enc,
    color=alt.Color(f"{y}:Q", scale=CSCALE, legend=None),
    size=alt.condition(sel_year, alt.value(190), alt.value(60)),
    tooltip=[alt.Tooltip("country:N", title="Country"),
             alt.Tooltip("year:O", title="Year"),
             alt.Tooltip(f"{y}:Q", title="Life evaluation", format=".2f")]).add_params(sel_year)

top = (ctx + feat + feat_lbl + sel_line + sel_lbl + sel_dots).add_params(sel_country).properties(
    width=WIDTH, height=460,
    title={"text": "Life evaluation over time, 2006–2025",
           "subtitle": "Top 3 and bottom 3 highlighted · use the Country dropdown to pick any country, then click a year-dot to break down that year"})

# ---------- bottom: driver breakdown for selected country + clicked year ----------
bd = alt.Chart(contrib_df).transform_filter(sel_country).transform_filter(sel_year)
bars = bd.mark_bar(cornerRadiusEnd=3).encode(
    x=alt.X("pct:Q", title="Share of life-evaluation score explained (%)",
            scale=alt.Scale(domain=[max(xlo, -20), 40], clamp=True)),
    y=alt.Y("driver:N", sort="-x", title=None,
            axis=alt.Axis(labelFontSize=13, labelColor=INK, labelLimit=200)),
    color=alt.Color("life_eval:Q", scale=CSCALE, legend=None),
    tooltip=[alt.Tooltip("driver:N", title="Driver"),
             alt.Tooltip("pct:Q", title="Explains", format=".1f")])
bar_text = bd.transform_calculate(lbl="format(datum.pct, '.1f') + '%'").mark_text(
    align="left", dx=5, fontSize=12.5, fontWeight=700, color=INK).encode(
    x=alt.X("pct:Q"), y=alt.Y("driver:N", sort="-x"), text="lbl:N")

focus_label = alt.Chart(contrib_df).transform_filter(sel_country).transform_filter(
    sel_year).transform_aggregate(le="max(life_eval)", groupby=["country", "year"]).transform_calculate(
    t="datum.country + '  —  ' + datum.year + '  ·  life evaluation ' + format(datum.le, '.2f')"
).mark_text(align="left", fontSize=16, fontWeight=700, color=INK).encode(
    text="t:N", x=alt.value(4)).properties(width=WIDTH, height=26)

bars_panel = (bars + bar_text).properties(width=WIDTH, height=260)
bottom = alt.vconcat(focus_label, bars_panel, spacing=2).properties(
    title={"text": "What explains this country's happiness?",
           "subtitle": "Each driver's contribution to the score, vs. the world's lowest values (dystopia baseline). Click a year-dot above to change the year."})

chart = site_theme(alt.vconcat(top, bottom, spacing=36).resolve_scale(color="independent"))
chart.save(OUT)
print("saved", OUT)
