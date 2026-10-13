#!/usr/bin/env python3
"""P6 — observational tests of the rivals (A27). T2 (isomorphism): framing following (V2) on non-wire stories only, both
samples; intercept-only mixed model with random intercepts for outlet and country; supported if the intercept is
positive (plan: "exceeds the bias-corrected chance level"). T3 (herding): within each war, event-level timing following
(negative first-story lag, censored at 14 days) regressed on event uncertainty; supported if the coefficient is
negative. Uncertainty proxy (A36): the number of core outlets whose first mention falls on the event's first core day
(1–4), the closest available measure of "core stories on the event's first day" (D22 holds first mentions and totals per
outlet, not per day). Both decided by Holm-adjusted p < .05 across the pair. X11: the framing test is re-run without the
headline-only Post copies. Writes T7. Deviations applied: X1, X7, X10, X11, X13."""
import os, sys, json, datetime as dt, warnings
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf, pf_models as pm

started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "data/analysis/p6_rival_tests.py"; INPUTS = ["data/coded/following_cells.csv", "data/raw/gdelt/g5_story_events.csv", "data/coded/v5_tier.csv"]; DEV = ["X1", "X7", "X10", "X11", "X13"]
run_id = pf.new_run_id("p6")
d = pm.cells_data(); rows, stats, fits = [], [], {}
pair = {}
# ---- T2: non-wire framing, intercept-only
for variant, ycol, label in (("main", "V2_nonwire", ""), ("x11", "V2_nonwire_x11", " (without headline-only Post copies, X11)")):
    dd = d.copy(); dd["y"] = dd[ycol]; dd = dd.dropna(subset=["y"])
    res = pm.fit_mixed("y ~ 1", dd); f = pm.reported(res); fits[f"T2_{variant}"] = res; t = f["terms"]["Intercept"]
    rows.append(["T2 isomorphism: non-wire framing following, intercept-only", "Intercept (mean V2 on non-wire stories)", "Framing" + label, pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
    if res["dropped"]:
        m = res["main"]["terms"]["Intercept"]
        rows.append(["T2 main fit before dropping the zero-variance component", "Intercept", "Framing" + label, pf.fmt(m["b"], 3), pm.ci_str(m, 3), pf.fmt_p(m["p"]), str(res["main"]["n"]), pm.fit_desc(res["main"])])
    if variant == "main": pair["T2"] = {"b": t["b"], "ci": t["ci"], "p": t["p"], "n": f["n"], "sign_ok": t["b"] > 0}
    stats.append({"name": f"T2_nonwire_intercept{'' if variant=='main' else '_x11'}", "value": f"b = {pf.fmt(t['b'], 3)}, 95% CI {pm.ci_str(t, 3)}, n = {f['n']} cells (non-wire stories n = {int(dd.V2_nonwire_n.sum()):,})", "p": pf.fmt_p(t["p"]), "effect": None})
# descriptive comparison: all-story V2 vs non-wire V2 in the same cells (reported, no test; exploratory context)
both = d.dropna(subset=["V2", "V2_nonwire"])
stats.append({"name": "T2_context_all_vs_nonwire", "value": f"same {len(both)} cells: V2 all stories M = {pf.fmt(both.V2.mean(), 3)}, non-wire stories M = {pf.fmt(both.V2_nonwire.mean(), 3)}, mean within-cell difference = {pf.fmt((both.V2_nonwire - both.V2).mean(), 3)}", "p": None, "effect": None})
rows.append(["Context (no test): all-story vs non-wire framing similarity in the same cells", f"M all = {pf.fmt(both.V2.mean(), 3)}; M non-wire = {pf.fmt(both.V2_nonwire.mean(), 3)}", "Framing", pf.fmt((both.V2_nonwire - both.V2).mean(), 3), "—", "—", str(len(both)), "mean within-cell difference (non-wire minus all)"])

# ---- T3: event-level timing within each war
g = pf.story_events(); tiers, _ = pf.tiers()
g = g[~g.outlet.isin(pf.CORE)].copy(); g["country"] = g.outlet.map(lambda o: pf.OUTLETS[o][0]); g["tier"] = g.country.map(tiers)
g["y"] = -g.lag_days; g["uncert"] = g.core_first_day_outlets.astype(float)
for war in ("ukraine", "gaza"):
    e = g[g.issue == war]
    if war == "gaza": e = e[e.core_first_date >= "2023-10-07"]
    e = e[e.outlet.isin([o for o, i in pf.kept_cells() if i == war])]
    res = pm.fit_mixed("y ~ uncert", e); f = pm.reported(res); fits[f"T3_{war}"] = res; t = f["terms"]["uncert"]
    rows.append(["T3 herding: event-level timing following on uncertainty", "Core outlets on the event's first day (1–4)", f"Timing, {pf.ISSUE_NAMES[war]}", pf.fmt(t["b"], 4), pm.ci_str(t, 4), pf.fmt_p(t["p"]), f"{f['n']:,} events", pm.fit_desc(f)])
    if res["dropped"]:
        m = res["main"]["terms"]["uncert"]
        rows.append(["T3 main fit before dropping the zero-variance component", "Core outlets on the event's first day (1–4)", f"Timing, {pf.ISSUE_NAMES[war]}", pf.fmt(m["b"], 4), pm.ci_str(m, 4), pf.fmt_p(m["p"]), f"{res['main']['n']:,} events", pm.fit_desc(res["main"])])
    pair[f"T3_{war}"] = {"b": t["b"], "ci": t["ci"], "p": t["p"], "n": f["n"], "sign_ok": t["b"] < 0}
    vc = e.uncert.value_counts().sort_index()
    stats.append({"name": f"T3_uncertainty_{war}", "value": f"b = {pf.fmt(t['b'], 4)} days per additional core outlet on the first day, 95% CI {pm.ci_str(t, 4)}, events n = {f['n']:,} ({', '.join(f'{int(k)} outlet(s): {int(v):,}' for k, v in vc.items())})", "p": pf.fmt_p(t["p"]), "effect": None})
    stats.append({"name": f"T3_lag_by_uncertainty_{war}", "value": "; ".join(f"{int(k)} core outlet(s) on day 1: Mdn lag {pf.fmt(-v, 3)} days" for k, v in e.groupby('uncert').y.median().items()), "p": None, "effect": None})
# Holm across the pair: T2 and T3 (the T3 p entered is the larger of the two wars, the conservative reading)
t3p = max(pair["T3_ukraine"]["p"], pair["T3_gaza"]["p"]); t3_sign = pair["T3_ukraine"]["sign_ok"] and pair["T3_gaza"]["sign_ok"]
adj = pf.holm([pair["T2"]["p"], t3p])
dec_T2 = "supported" if (pair["T2"]["sign_ok"] and adj[0] < 0.05) else "not supported"
dec_T3 = "supported" if (t3_sign and adj[1] < 0.05) else "not supported"
rows.append(["Decision (Holm across the pair)", "T2: non-wire framing intercept > 0", "Framing", pf.fmt(pair["T2"]["b"], 3), pm.ci_str(pair["T2"], 3), f"Holm {pf.fmt_p(adj[0])}", str(pair["T2"]["n"]), dec_T2])
rows.append(["Decision (Holm across the pair)", "T3: uncertainty coefficient < 0 in both wars", "Timing", f"{pf.fmt(pair['T3_ukraine']['b'], 4)} / {pf.fmt(pair['T3_gaza']['b'], 4)}", "—", f"Holm {pf.fmt_p(adj[1])} (larger of the two wars)", f"{pair['T3_ukraine']['n']:,} / {pair['T3_gaza']['n']:,}", dec_T3])
stats.append({"name": "decision_T2", "value": f"non-wire framing intercept b = {pf.fmt(pair['T2']['b'], 3)}, 95% CI {pm.ci_str(pair['T2'], 3)}", "p": f"Holm {pf.fmt_p(adj[0])}", "effect": dec_T2})
stats.append({"name": "decision_T3", "value": f"uncertainty b = {pf.fmt(pair['T3_ukraine']['b'], 4)} (Ukraine), {pf.fmt(pair['T3_gaza']['b'], 4)} (Gaza)", "p": f"Holm {pf.fmt_p(adj[1])}", "effect": dec_T3})
T7 = {"label": "T7", "title": "Observational Tests of Prestige Imitation (T2) and Herding (T3)", "answers": ["H2", "RQ2"],
      "columns": ["Model", "Predictor", "Level", "b", "95% CI", "p", "n", "Random effects / decision"], "rows": rows,
      "note": ("T2: framing similarity recomputed with wire-credited stories removed from both the outlet's and the core sample (bias-corrected as in Table T2, so 0 means indistinguishable "
               "from the core's non-wire frames); intercept-only mixed model over the 52 kept cells with random intercepts for outlet nested in country; the plan's decision rule reads a positive "
               "intercept as support. T3: for every GDELT event an outlet covered within one of the two wars (Gaza from October 7, 2023), the negative lag in days from the first core mention "
               "to the outlet's first mention (censored at 14 days) regressed on the number of core outlets that mentioned the event on its first core day, the available proxy for the "
               "number of core stories that day; random intercepts for outlet nested in country; the plan reads a negative coefficient (closer following for less-covered, more uncertain "
               "events) as support. Decisions by Holm-adjusted p < .05 across the pair, the T3 p being the larger of the two wars."),
      "stats": stats}
d_out = os.path.join(pf.P, "results", run_id); os.makedirs(d_out, exist_ok=True)
json.dump(fits, open(os.path.join(d_out, "fits.json"), "w"), indent=1)
summary = f"# {run_id} — P6 rival tests\n\n" + "\n".join(f"- {r[0]} · {r[1]} · {r[2]}: b = {r[3]}, CI {r[4]}, p = {r[5]}, n = {r[6]} — {r[7]}" for r in rows) + "\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T7], [], [], summary, started, DEV, notes="Uncertainty proxy = core outlets on the event's first day (A36); T3 Holm p = larger of the two wars.")
