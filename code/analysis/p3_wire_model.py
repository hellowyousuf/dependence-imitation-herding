#!/usr/bin/env python3
"""P3 — H2: following ~ wire_reliance (V4) + tier + issue + (1|outlet) + (1|country), per level. X12: no V9 term in the
confirmatory model; V9 appears in one separately labelled exploratory model. First T1 falsifier (plan): the tier gap net
of wire reliance against half the H1 estimate (from P2's family entry), computed on the model without V9 (X12), so
correspondent presence sits inside the non-wire remainder. Writes T5; records H2 in the Holm family.
Deviations applied: X1, X4 (V4 = credits only), X7, X11 (framing re-run without the headline-only Post copies), X12, X13."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf, pf_models as pm

started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "data/analysis/p3_wire_model.py"; INPUTS = ["data/coded/following_cells.csv", "data/analysis/holm_family.json"]; DEV = ["X1", "X4", "X7", "X11", "X12", "X13"]
run_id = pf.new_run_id("p3")
d = pm.cells_data(); fam = json.load(open(pm.family_path()))
rows, stats, fits = [], [], {}
for lev, col in pm.LEVELS:
    for variant, ycol, label in (("main", col, ""), ("x11", col + "_x11", " (without headline-only Post copies, X11)")):
        if variant == "x11" and lev != "framing": continue
        dd = d.copy(); dd["y"] = dd[ycol]
        res = pm.fit_mixed("y ~ V4 + periphery + C(issue)", dd); f = pm.reported(res); fits[f"{lev}{variant}"] = res
        tw, tp = f["terms"]["V4"], f["terms"]["periphery"]
        rows.append(["H2 wire reliance (confirmatory, no V9 term, X12)", "Wire reliance V4 (0–1)", pm.LEVEL_NAME[lev] + label, pf.fmt(tw["b"], 3), pm.ci_str(tw, 3), pf.fmt_p(tw["p"]), str(f["n"]), pm.fit_desc(f)])
        rows.append(["Tier gap net of wire reliance (first T1 falsifier)", "Periphery", pm.LEVEL_NAME[lev] + label, pf.fmt(tp["b"], 3), pm.ci_str(tp, 3), pf.fmt_p(tp["p"]), str(f["n"]), pm.fit_desc(f)])
        if res["dropped"]:
            m = res["main"]
            rows.append(["H2 wire reliance, main fit before dropping the zero-variance component", "Wire reliance V4 (0–1)", pm.LEVEL_NAME[lev] + label, pf.fmt(m["terms"]["V4"]["b"], 3), pm.ci_str(m["terms"]["V4"], 3), pf.fmt_p(m["terms"]["V4"]["p"]), str(m["n"]), pm.fit_desc(m)])
        if variant == "main":
            h1 = fam[f"H1_{lev}"]["b"]; half = 0.5 * h1; upper = tp["ci"][1]
            falsifier = "non-wire channels lose support" if (h1 > 0 and upper < half) else "not met"
            pm.family_record(f"H2_{lev}", {"hypothesis": "H2", "level": lev, "term": "V4", "b": tw["b"], "ci": tw["ci"], "p": tw["p"], "n": f["n"], "run_id": run_id, "sign_ok": tw["b"] > 0,
                                           "falsifier1": {"tier_b_net": tp["b"], "tier_ci_net": tp["ci"], "h1_b": h1, "half_h1": half, "verdict": falsifier}})
            stats.append({"name": f"H2_{lev}_wire_reliance", "value": f"b = {pf.fmt(tw['b'], 3)}, 95% CI {pm.ci_str(tw, 3)}, z = {pf.fmt(tw['z'])}, n = {f['n']} cells", "p": pf.fmt_p(tw["p"]), "effect": None})
            stats.append({"name": f"falsifier1_{lev}", "value": f"tier gap net of wire reliance b = {pf.fmt(tp['b'], 3)}, 95% CI {pm.ci_str(tp, 3)}; H1 estimate {pf.fmt(h1, 3)}, half = {pf.fmt(half, 3)}; upper bound below half: {'yes' if (h1 > 0 and upper < half) else 'no'}", "p": None, "effect": None})
            rows.append(["First T1 falsifier read-out", "Upper CI bound of the net tier gap vs half the H1 estimate", pm.LEVEL_NAME[lev], f"{pf.fmt(upper, 3)} vs {pf.fmt(half, 3)}", "—", "—", str(f["n"]), falsifier])
        else:
            stats.append({"name": f"H2_{lev}_wire_reliance_x11", "value": f"b = {pf.fmt(tw['b'], 3)}, 95% CI {pm.ci_str(tw, 3)}, n = {f['n']} cells", "p": pf.fmt_p(tw["p"]), "effect": None})
    # exploratory: with V9 (X12)
    dd = d.copy(); dd["y"] = dd[col]
    res = pm.fit_mixed("y ~ V4 + V9 + periphery + C(issue)", dd); f = pm.reported(res); fits[f"{lev}_v9"] = res
    for term, name in (("V4", "Wire reliance V4"), ("V9", "Correspondent presence V9"), ("periphery", "Periphery")):
        t = f["terms"][term]
        rows.append(["Exploratory: with the V9 term (X12; outside the Holm family)", name, pm.LEVEL_NAME[lev], pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
    stats.append({"name": f"exploratory_V9_{lev}", "value": f"V9 b = {pf.fmt(f['terms']['V9']['b'], 3)}, 95% CI {pm.ci_str(f['terms']['V9'], 3)}; V4 b = {pf.fmt(f['terms']['V4']['b'], 3)}, 95% CI {pm.ci_str(f['terms']['V4'], 3)}; n = {f['n']} cells", "p": pf.fmt_p(f["terms"]["V9"]["p"]), "effect": None})
# V4 descriptives by tier (cell level)
g = d.groupby("tier").V4.agg(["mean", "std", "count"])
stats.append({"name": "V4_tier_cell_means", "value": "; ".join(f"{t}: M = {pf.fmt(g.loc[t,'mean'])}, SD = {pf.fmt(g.loc[t,'std'])}, n = {int(g.loc[t,'count'])}" for t in g.index), "p": None, "effect": None})
stats.append({"name": "V9_tier_cell_means", "value": "; ".join(f"{t}: M = {pf.fmt(x.mean(), 3)}, cells with any staff foreign byline = {int((x > 0).sum())} of {len(x)}" for t, x in d.groupby('tier').V9), "p": None, "effect": None})

T5 = {"label": "T5", "title": "Mixed Models of Following on Wire Reliance (H2) and the First Falsifier of the Structural Account", "answers": ["H2"],
      "columns": ["Model", "Predictor", "Level", "b", "95% CI", "p (unadjusted)", "Cells (n)", "Random effects / read-out"],
      "rows": rows,
      "note": ("Same cells, levels and random structure as Table T3. Wire reliance is the share of a cell's coded foreign stories that credit AP, AFP or Reuters (credits only; no text-reuse "
               "rule, X4), so b is the change in following from a cell with no wire credits to one with wire credits on every foreign story. The confirmatory model carries no correspondent-presence "
               "term because V9 fell below the stability floor (X12); the first falsifier therefore reads the tier gap net of wire reliance alone, with correspondent presence inside the "
               "remainder. The falsifier read-out compares the upper bound of the net tier gap's 95% CI with half the H1 estimate from Table T3: the non-wire channels lose support when the "
               "bound lies below it and the H1 estimate is positive. The exploratory model adds V9 and stands outside the Holm family. Holm-adjusted decisions are in Table T6."),
      "stats": stats}
d_out = os.path.join(pf.P, "results", run_id); os.makedirs(d_out, exist_ok=True)
json.dump(fits, open(os.path.join(d_out, "fits.json"), "w"), indent=1)
summary = f"# {run_id} — P3 H2 wire models\n\n" + "\n".join(f"- {r[0]} · {r[1]} · {r[2]}: b = {r[3]}, CI {r[4]}, p = {r[5]}, n = {r[6]} — {r[7]}" for r in rows) + "\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T5], [], [], summary, started, DEV, notes="Holm family entries H2_salience, H2_framing, H2_timing recorded; decisions in P4's T6.")
