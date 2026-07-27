# Section 2 — "What actually drives a country's happiness?"
# Multi-line life-evaluation chart (top-3 / bottom-3 auto-selected, all countries
# shown faintly, color = latest life evaluation) + click-to-drill driver breakdown.
# Run from the repo root:  python3 charts/build_task2_drivers.py
import pandas as pd, numpy as np, altair as alt
alt.data_transformers.disable_max_rows()

DATA = "charts/data/whr_2006_2025_cleaned.csv"
OUT  = "charts/task2_drivers.html"
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
        .configure_axis(labelColor=INK_SOFT, titleColor=INK, labelFontSize=11, titleFontSize=12,
                        gridColor=LINE, domainColor=LINE, tickColor=LINE)
        .configure_legend(titleColor=INK, labelColor=INK_SOFT, titleFontSize=12, labelFontSize=11,
                          gradientLength=200, gradientThickness=10)
    )

# ---------- driver decomposition (5 buckets, dystopia-baselined) ----------
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
base = {v: sub[v].min() for v in allvars}

latest = sub.sort_values("year").groupby("country").tail(1)
rows = []
for _, r in latest.iterrows():
    le = r[y]
    for bname, vs in buckets.items():
        contrib = sum(bmap[v] * (r[v] - base[v]) for v in vs)
        rows.append({"country": r["country"], "driver": bname,
                     "pct": round(100 * contrib / le, 1),
                     "life_eval": round(le, 2), "year": int(r["year"])})
contrib_df = pd.DataFrame(rows)

# ---------- line data: all countries with >=8 yrs of data ----------
line_df = df.dropna(subset=[y])[["country", "year", y, "region"]].copy()
counts = line_df.groupby("country")["year"].transform("count")
line_df = line_df[counts >= 8].copy()
line_df[y] = line_df[y].round(3)

# per-country latest value (for color) and last-point flag (for labels)
last_year = line_df.groupby("country")["year"].transform("max")
line_df["is_last"] = (line_df["year"] == last_year)
latest_val = line_df.loc[line_df["is_last"], ["country", y]].rename(columns={y: "le_latest"})
line_df = line_df.merge(latest_val, on="country", how="left")

# top-3 & bottom-3 by latest life evaluation (default selection)
final = latest_val.sort_values("le_latest")
featured = list(final.tail(3)["country"]) + list(final.head(3)["country"])
featured = [c for c in featured if c in set(contrib_df.country)]
print("Featured (top3+bottom3):", featured)

# ---------- selections ----------
# spotlight: multi (shift-click toggles), default = top3+bottom3  -> controls line highlight+labels
spotlight = alt.selection_point(fields=["country"], on="click", toggle="event.shiftKey",
                                empty=False, value=[{"country": c} for c in featured])
# focus: single click, default = happiest country -> drives bottom breakdown
top_country = final.tail(1)["country"].iloc[0]
focus = alt.selection_point(fields=["country"], on="click", toggle=False,
                            empty=False, value=[{"country": top_country}])

color_scale = alt.Scale(scheme="redyellowgreen", domain=[2.5, 8])
YMIN, YMAX = int(line_df.year.min()), int(line_df.year.max())

x_enc = alt.X("year:O", title="Year",
             axis=alt.Axis(values=list(range(YMIN, YMAX + 1, 2)), labelAngle=0))
y_enc = alt.Y(f"{y}:Q", title="Life evaluation",
              scale=alt.Scale(domain=[1, 8.2]), axis=alt.Axis(values=[1,2,3,4,5,6,7,8]))

base_lines = alt.Chart(line_df).mark_line(color="#d9dde3", strokeWidth=1, opacity=0.5).encode(
    x=x_enc, y=y_enc, detail="country:N")

hi_lines = alt.Chart(line_df).mark_line(strokeWidth=2.6).encode(
    x=x_enc, y=y_enc, detail="country:N",
    color=alt.Color("le_latest:Q", scale=color_scale,
                    legend=alt.Legend(title="Life evaluation (latest)", orient="top", direction="horizontal")),
    opacity=alt.condition(focus, alt.value(1.0), alt.value(0.85)),
    tooltip=[alt.Tooltip("country:N", title="Country"),
             alt.Tooltip("year:O", title="Year"),
             alt.Tooltip(f"{y}:Q", title="Life evaluation", format=".2f")],
).transform_filter(spotlight)

labels = alt.Chart(line_df).mark_text(align="left", dx=6, fontSize=11, fontWeight=600).encode(
    x=x_enc, y=y_enc, text="country:N",
    color=alt.Color("le_latest:Q", scale=color_scale, legend=None),
).transform_filter(spotlight).transform_filter("datum.is_last")

top = (base_lines + hi_lines + labels).add_params(spotlight, focus).properties(
    width="container", height=420,
    title={"text": "Life evaluation over time, 2006–2025",
           "subtitle": "Top 3 and bottom 3 shown by default · click a line to see its drivers · shift-click to add lines"})

# ---------- bottom: driver breakdown for the focused country ----------
bar_color = alt.Scale(scheme="redyellowgreen", domain=[2.5, 8])
bars = alt.Chart(contrib_df).mark_bar(cornerRadiusEnd=3, height=22).encode(
    x=alt.X("pct:Q", title="Share of life-evaluation score explained (%)",
            scale=alt.Scale(domain=[-15, 30])),
    y=alt.Y("driver:N", sort="-x", title=None,
            axis=alt.Axis(labelFontSize=12, labelColor=INK)),
    color=alt.Color("life_eval:Q", scale=bar_color, legend=None),
    tooltip=[alt.Tooltip("driver:N", title="Driver"),
             alt.Tooltip("pct:Q", title="Explains", format=".1f")],
).transform_filter(focus)

bar_text = alt.Chart(contrib_df).transform_filter(focus).transform_calculate(
    lbl="format(datum.pct, '.1f') + '%'").mark_text(
    align="left", dx=4, fontSize=11, fontWeight=700, color=INK).encode(
    x=alt.X("pct:Q"), y=alt.Y("driver:N", sort="-x"),
    text="lbl:N",
    tooltip=alt.value(None))

# dynamic header naming the focused country + its score
focus_label = alt.Chart(contrib_df).transform_filter(focus).transform_aggregate(
    le="max(life_eval)", yr="max(year)", groupby=["country"]).transform_calculate(
    t="datum.country + '  —  life evaluation ' + format(datum.le, '.2f') + '  (' + datum.yr + ')'"
).mark_text(align="left", fontSize=16, fontWeight=700, color=INK).encode(
    text="t:N", x=alt.value(4)).properties(width="container", height=26)

bars_panel = (bars + bar_text).properties(width="container", height=200)

bottom = alt.vconcat(focus_label, bars_panel, spacing=2).properties(
    title={"text": "What explains this country's happiness?",
           "subtitle": "Each driver's contribution to the score, relative to the world's lowest values (dystopia baseline)"})

chart = site_theme(alt.vconcat(top, bottom, spacing=36).resolve_scale(color="independent"))
chart.save(OUT)
print("saved", OUT)
