#!/usr/bin/env python3
"""P2 — H1: following ~ tier + issue + (1|outlet) + (1|country), per level (salience V1, framing V2, timing V3a);
check with the continuous Gunaratne index score in place of tier (A28). Writes T3; records the three H1 tests in the Holm
family (data/analysis/holm_family.json; the nine-test Holm decisions are reported by P4, run last).
Deviations applied: X1 (tiers by index), X7, X11 (framing re-run without the headline-only Post copies), X13."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf, pf_models as pm

started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "data/analysis/p2_tier_model.py"; INPUTS = ["data/coded/following_cells.csv"]; DEV = ["X1", "X7", "X11", "X13"]
run_id = pf.new_run_id("p2")
d = pm.cells_data()
rows, stats, fits = [], [], {}
for lev, col in pm.LEVELS:
    for variant, ycol, label in (("main", col, ""), ("x11", col + "_x11", " (without headline-only Post copies, X11)")):
        if variant == "x11" and lev != "framing": continue
        dd = d.copy(); dd["y"] = dd[ycol]
        res = pm.fit_mixed("y ~ periphery + C(issue)", dd); f = pm.reported(res); t = f["terms"]["periphery"]
        fits[f"{lev}{variant}"] = res
        both = f" Main fit dropped {' and '.join(res['dropped'])} at zero variance; refit reported, main fit b = {pf.fmt(res['main']['terms']['periphery']['b'], 3)}." if res["dropped"] else ""
        rows.append(["H1 tier (periphery vs semi-periphery)", "Periphery", pm.LEVEL_NAME[lev] + label, pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
        if variant == "main":
            pm.family_record(f"H1_{lev}", {"hypothesis": "H1", "level": lev, "term": "periphery", "b": t["b"], "ci": t["ci"], "p": t["p"], "n": f["n"], "run_id": run_id, "sign_ok": t["b"] > 0})
            stats.append({"name": f"H1_{lev}_periphery", "value": f"b = {pf.fmt(t['b'], 3)}, 95% CI {pm.ci_str(t, 3)}, z = {pf.fmt(t['z'])}, n = {f['n']} cells", "p": pf.fmt_p(t["p"]), "effect": None})
        else:
            stats.append({"name": f"H1_{lev}_periphery_x11", "value": f"b = {pf.fmt(t['b'], 3)}, 95% CI {pm.ci_str(t, 3)}, n = {f['n']} cells", "p": pf.fmt_p(t["p"]), "effect": None})
        if res["dropped"]:
            m = res["main"]["terms"]["periphery"]
            rows.append(["H1 tier, main fit before dropping the zero-variance component", "Periphery", pm.LEVEL_NAME[lev] + label, pf.fmt(m["b"], 3), pm.ci_str(m, 3), pf.fmt_p(m["p"]), str(res["main"]["n"]), pm.fit_desc(res["main"])])
    # continuous index check (A28): H1 predicts closer following at lower scores → negative coefficient
    dd = d.copy(); dd["y"] = dd[col]
    res = pm.fit_mixed("y ~ index + C(issue)", dd); f = pm.reported(res); t = f["terms"]["index"]; fits[f"{lev}index"] = res
    rows.append(["H1 check: continuous index score (A28)", "Index score (per point)", pm.LEVEL_NAME[lev], pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
    stats.append({"name": f"H1_check_index_{lev}", "value": f"b = {pf.fmt(t['b'], 3)} per index point, 95% CI {pm.ci_str(t, 3)}, n = {f['n']} cells", "p": pf.fmt_p(t["p"]), "effect": None})
    if res["dropped"]:
        m = res["main"]["terms"]["index"]
        rows.append(["H1 check: continuous index, main fit before dropping the zero-variance component", "Index score (per point)", pm.LEVEL_NAME[lev], pf.fmt(m["b"], 3), pm.ci_str(m, 3), pf.fmt_p(m["p"]), str(res["main"]["n"]), pm.fit_desc(res["main"])])
# tier means for the record
for lev, col in pm.LEVELS:
    g = d.groupby("tier")[col].agg(["mean", "std", "count"])
    stats.append({"name": f"{lev}_tier_means", "value": "; ".join(f"{t}: M = {pf.fmt(g.loc[t,'mean'])}, SD = {pf.fmt(g.loc[t,'std'])}, n = {int(g.loc[t,'count'])}" for t in g.index), "p": None, "effect": None})

T3 = {"label": "T3", "title": "Mixed Models of Following on Tier (H1)", "answers": ["H1"],
      "columns": ["Model", "Predictor", "Level", "b", "95% CI", "p (unadjusted)", "Cells (n)", "Random effects"],
      "rows": rows,
      "note": ("Following per outlet × issue cell (periphery 26 cells, semi-periphery 26; timing 37 cells with at least 10 matched events). Fixed effects: tier (periphery = 1, semi-periphery = 0) "
               "and issue (two dummies, Ukraine and Gaza against COP); random intercepts for outlet nested in country (restricted maximum likelihood). Salience is the event-adjusted correlation, "
               "framing the bias-corrected similarity, timing the negative median lag in days, so a positive b means closer following in the periphery. p values are two-sided Wald tests before "
               "Holm correction; the Holm-adjusted decisions across the nine confirmatory tests are in Table T6. A random-effect variance estimated at zero was dropped and the model refitted; "
               "both fits are listed. The index check enters Gunaratne's 2022 score (India 2.83, Malaysia 0.66, Nigeria 0.44, South Africa 0.41, Bangladesh 0.34, Kenya 0.09) in place of tier; "
               "H1 predicts a negative coefficient."),
      "stats": stats}
d_out = os.path.join(pf.P, "results", run_id); os.makedirs(d_out, exist_ok=True)
json.dump(fits, open(os.path.join(d_out, "fits.json"), "w"), indent=1)
summary = f"# {run_id} — P2 H1 tier models\n\n" + "\n".join(f"- {r[0]} · {r[2]}: b = {r[3]}, CI {r[4]}, p = {r[5]}, n = {r[6]}" for r in rows) + "\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T3], [], [], summary, started, DEV, notes="Holm family entries H1_salience, H1_framing, H1_timing recorded; decisions in P4's T6.")
