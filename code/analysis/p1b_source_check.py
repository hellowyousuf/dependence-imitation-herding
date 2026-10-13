"""P1 check promised in deviation X5 (amended October 2, 2026): the GDELT title-based weekly issue shares (D21, g4_host_weeks) are
computed for every outlet that the main series draws from Media Cloud, and compared with the Media Cloud series:
(a) the correlation of weekly issue shares over the weeks both sources hold, (b) the event-adjusted salience following (V1)
recomputed from the GDELT shares for the peripheral outlets, against the main V1. Written after the critic's pass 2 (round 2).
No model; a read-out of data already registered."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf
SCRIPT = "data/analysis/p1b_source_check.py"; DEV = ["X5", "X13", "X7"]
INPUTS = ["data/raw/gdelt/g4_host_weeks.csv", "data/raw/mediacloud/r1_source_weeks.jsonl", "data/sampling/census_urls.csv", "data/coded/following_cells.csv", "data/raw/gdelt/g6b_issue_event_weeks.csv"]
started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); run_id = pf.new_run_id("p1b")
g = pd.read_csv(os.path.join(pf.P, "data/raw/gdelt/g4_host_weeks.csv"))
HOSTMAP = {"bbc": ["bbc.com", "bbc.co.uk"], "timesofindia": ["indiatimes.com"]}
s = pf.weekly_series(); ev = pf.events_weekly(); W = set(pf.weeks())
# GDELT shares per outlet × issue × week
rows = []
for o, (country, dom, host) in pf.OUTLETS.items():
    hosts = HOSTMAP.get(o, [dom or host])
    gg = g[g.domain.isin(hosts)].groupby("week_start").sum(numeric_only=True).reset_index()
    for _, r in gg.iterrows():
        if r.week_start not in W or r.articles < pf.MIN_WEEK_STORIES: continue
        for iss in pf.ISSUES: rows.append((o, iss, r.week_start, float(r[f"{iss}_title"]) / float(r.articles), int(r.articles)))
gs = pd.DataFrame(rows, columns=["outlet", "issue", "week", "g_share", "g_n"])
core_g = gs[gs.outlet.isin(pf.CORE)].groupby(["issue", "week"]).agg(core_g=("g_share", "mean")).reset_index()
cells = pd.read_csv(os.path.join(pf.P, "data/coded/following_cells.csv")); kept = cells[(cells.tier != "core") & cells.cell_kept]
out = []
for _, c in kept.iterrows():
    o, iss = c.outlet, c.issue; src = "GDELT (main series)" if pf.OUTLETS[o][2] else "Media Cloud"
    m = s[(s.outlet == o) & (s.issue == iss)][["week", "share"]].merge(gs[(gs.outlet == o) & (gs.issue == iss)][["week", "g_share"]], on="week")
    r_src = float(np.corrcoef(m.share, m.g_share)[0, 1]) if len(m) >= pf.MIN_WEEKS and m.share.std() > 0 and m.g_share.std() > 0 else np.nan
    # V1 from GDELT shares (outlet and core both from GDELT), event-adjusted as in pf.v1_salience
    mg = gs[(gs.outlet == o) & (gs.issue == iss)][["week", "g_share"]].merge(core_g[core_g.issue == iss][["week", "core_g"]], on="week"); mg = mg[mg.week.isin(ev[iss].keys())]
    if len(mg) >= pf.MIN_WEEKS and mg.g_share.std() > 0 and mg.core_g.std() > 0:
        x = np.array([ev[iss][w] for w in mg.week], float); v1g = float(np.corrcoef(pf._resid(mg.g_share.values, x), pf._resid(mg.core_g.values, x))[0, 1])
    else: v1g = np.nan
    out.append({"outlet": pf.OUTLET_NAMES[o], "tier": c.tier, "issue": iss, "source": src, "r_sources": r_src, "n_weeks": int(len(m)), "V1_main": float(c.V1), "V1_gdelt": v1g})
D = pd.DataFrame(out)
def msd(x): x = pd.Series(x).dropna(); return f"{pf.fmt(x.mean())} ({pf.fmt(x.std(ddof=1))})" if len(x) > 1 else "—"
rows = []
for tier in ("periphery", "semi-periphery"):
    d = D[D.tier == tier]; mc = d[d.source == "Media Cloud"]
    rows.append([tier.capitalize(), str(len(d)), str(len(mc)), msd(mc.r_sources), msd(mc.V1_main), msd(mc.V1_gdelt), pf.fmt(float(np.corrcoef(mc.dropna(subset=["V1_gdelt"]).V1_main, mc.dropna(subset=["V1_gdelt"]).V1_gdelt)[0, 1])) if mc.V1_gdelt.notna().sum() > 2 else "—"])
for _, r in D.sort_values(["tier", "outlet", "issue"]).iterrows():
    rows.append([f"{r.outlet} · {pf.ISSUE_NAMES[r.issue]}", r.tier, r.source, pf.fmt(r.r_sources) if not np.isnan(r.r_sources) else "—", pf.fmt(r.V1_main), pf.fmt(r.V1_gdelt) if not np.isnan(r.V1_gdelt) else "—", str(r.n_weeks)])
T12 = {"label": "T12", "title": "Source Check (X5): Media Cloud Series Against GDELT Title-Based Series, by Tier and Cell", "answers": ["RQ1"],
       "columns": ["Tier / cell", "Cells (n) / tier", "Media Cloud cells (n) / source", "r between the two sources' weekly issue shares, M (SD) / cell r", "Salience following V1, main series, M (SD) / cell", "Salience following V1 from GDELT shares, M (SD) / cell", "r of main vs GDELT V1 across cells / weeks (n)"],
       "rows": rows,
       "note": ("The two tier rows summarize the Media Cloud cells (Bangladesh's three outlets draw their main series from GDELT under X5 and are listed with the cells only). For every outlet, GDELT's Global Knowledge Graph host rows give weekly article totals and the number of page titles matching the codebook C1 terms for each issue (D21), the same measure the Bangladesh outlets use; weeks with fewer than 5 articles are dropped. "
                "r between sources is the Pearson correlation of the weekly issue shares from Media Cloud (census stories over the source's story count) and from GDELT titles over the weeks both hold. V1 from GDELT shares recomputes the event-adjusted salience correlation with both the outlet and the core set measured from GDELT titles (core = mean of the core hosts present; The Washington Post included, X7). "
                "Columns read per tier row as: cells, Media Cloud cells, mean r between sources, mean main V1, mean GDELT V1, correlation of the two V1 values across cells; per cell row as: tier, source of the main series, r between sources, main V1, GDELT V1, weeks."),
       "stats": [{"name": f"source_check_{t.split()[0].lower()}", "value": f"{t}: r between sources M = {rows[i][3].split(' ')[0]}, main V1 M = {rows[i][4].split(' ')[0]}, GDELT V1 M = {rows[i][5].split(' ')[0]}, r(main V1, GDELT V1) across cells = {rows[i][6]} (Media Cloud cells n = {rows[i][2]})", "p": None, "effect": None} for i, t in enumerate(("Periphery", "Semi-periphery"))]}
summary = f"# {run_id} — P1 source check (X5)\n\n" + "\n".join(f"- {r[0]}: r sources {r[3]}, V1 main {r[4]}, V1 GDELT {r[5]}, r(V1,V1g) {r[6]}" for r in rows[:2]) + "\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T12], [], [], summary, started, DEV, notes="Source check promised in X5 (amended_2): GDELT title-based shares for every outlet against the Media Cloud series; descriptive, no model.")
print("run", run_id, "written"); print(summary)
