#!/usr/bin/env python3
"""P4 — H3: following ~ tier × local_stake + (1|outlet) + (1|country), stake 0/1/2 linear (issue dropped: stake and issue
coincide); robustness with two dummy contrasts and with V10 in place of stake; second T1 falsifier (periphery following at
high stake vs the mismatched-issue benchmark, one-sided, Holm within the three levels). Run last of P2–P4: writes T6 with the
Holm decisions across the nine confirmatory tests (data/analysis/holm_family.json) and F2.
The within-wars check with a country × issue stake code (plan P4 step 4, A28) is dropped under X14 (no hand-coding: the
a-priori stake code would have been human-coded; author, October 6, 2026).
Deviations applied: X1, X7, X10, X11 (framing re-run without the headline-only Post copies), X13, X14."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
from scipy import stats as sps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf, pf_models as pm

started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "data/analysis/p4_stake_interaction.py"; INPUTS = ["data/coded/following_cells.csv", "data/analysis/holm_family.json"]; DEV = ["X1", "X7", "X10", "X11", "X13", "X14"]
run_id = pf.new_run_id("p4")
d = pm.cells_data()
rows, stats, fits = [], [], {}
BENCH = {"V1": "V1_bench", "V2": "V2_bench", "V3a": "V3a_bench"}
for lev, col in pm.LEVELS:
    for variant, ycol, label in (("main", col, ""), ("x11", col + "_x11", " (without headline-only Post copies, X11)")):
        if variant == "x11" and lev != "framing": continue
        dd = d.copy(); dd["y"] = dd[ycol]
        res = pm.fit_mixed("y ~ periphery * stake_lin", dd); f = pm.reported(res); fits[f"{lev}{variant}"] = res
        ti, ts, tp = f["terms"]["periphery:stake_lin"], f["terms"]["stake_lin"], f["terms"]["periphery"]
        rows.append(["H3 tier × stake (linear 0/1/2)", "Periphery × stake", pm.LEVEL_NAME[lev] + label, pf.fmt(ti["b"], 3), pm.ci_str(ti, 3), pf.fmt_p(ti["p"]), str(f["n"]), pm.fit_desc(f)])
        rows.append(["H3 tier × stake (linear 0/1/2)", "Stake (semi-periphery slope)", pm.LEVEL_NAME[lev] + label, pf.fmt(ts["b"], 3), pm.ci_str(ts, 3), pf.fmt_p(ts["p"]), str(f["n"]), ""])
        rows.append(["H3 tier × stake (linear 0/1/2)", "Periphery (at stake 0)", pm.LEVEL_NAME[lev] + label, pf.fmt(tp["b"], 3), pm.ci_str(tp, 3), pf.fmt_p(tp["p"]), str(f["n"]), ""])
        if res["dropped"]:
            m = res["main"]["terms"]["periphery:stake_lin"]
            rows.append(["H3 main fit before dropping the zero-variance component", "Periphery × stake", pm.LEVEL_NAME[lev] + label, pf.fmt(m["b"], 3), pm.ci_str(m, 3), pf.fmt_p(m["p"]), str(res["main"]["n"]), pm.fit_desc(res["main"])])
        if variant == "main":
            pm.family_record(f"H3_{lev}", {"hypothesis": "H3", "level": lev, "term": "periphery:stake_lin", "b": ti["b"], "ci": ti["ci"], "p": ti["p"], "n": f["n"], "run_id": run_id, "sign_ok": ti["b"] > 0})
            stats.append({"name": f"H3_{lev}_interaction", "value": f"b = {pf.fmt(ti['b'], 3)}, 95% CI {pm.ci_str(ti, 3)}, z = {pf.fmt(ti['z'])}, n = {f['n']} cells", "p": pf.fmt_p(ti["p"]), "effect": None})
            stats.append({"name": f"H3_{lev}_stake_slope_semi", "value": f"b = {pf.fmt(ts['b'], 3)} per stake step, 95% CI {pm.ci_str(ts, 3)}", "p": pf.fmt_p(ts["p"]), "effect": None})
        else:
            stats.append({"name": f"H3_{lev}_interaction_x11", "value": f"b = {pf.fmt(ti['b'], 3)}, 95% CI {pm.ci_str(ti, 3)}, n = {f['n']} cells", "p": pf.fmt_p(ti["p"]), "effect": None})
    dd = d.copy(); dd["y"] = dd[col]
    # robustness: dummy contrasts
    res = pm.fit_mixed("y ~ periphery * C(stake)", dd); f = pm.reported(res); fits[f"{lev}_dummies"] = res
    for term, name in (("periphery:C(stake)[T.1]", "Periphery × stake 1 (Gaza vs Ukraine)"), ("periphery:C(stake)[T.2]", "Periphery × stake 2 (COP vs Ukraine)")):
        t = f["terms"][term]
        rows.append(["H3 robustness: two dummy contrasts", name, pm.LEVEL_NAME[lev], pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
        stats.append({"name": f"H3_dummies_{lev}_{term.split('T.')[1][0]}", "value": f"b = {pf.fmt(t['b'], 3)}, 95% CI {pm.ci_str(t, 3)}, n = {f['n']} cells", "p": pf.fmt_p(t["p"]), "effect": None})
    # robustness: V10 in place of stake
    res = pm.fit_mixed("y ~ periphery * V10", dd); f = pm.reported(res); fits[f"{lev}_v10"] = res
    t = f["terms"]["periphery:V10"]; t2 = f["terms"]["V10"]
    rows.append(["H3 robustness: own-country share V10 in place of stake", "Periphery × V10", pm.LEVEL_NAME[lev], pf.fmt(t["b"], 3), pm.ci_str(t, 3), pf.fmt_p(t["p"]), str(f["n"]), pm.fit_desc(f)])
    rows.append(["H3 robustness: own-country share V10 in place of stake", "V10 (semi-periphery slope)", pm.LEVEL_NAME[lev], pf.fmt(t2["b"], 3), pm.ci_str(t2, 3), pf.fmt_p(t2["p"]), str(f["n"]), ""])
    stats.append({"name": f"H3_V10_{lev}_interaction", "value": f"b = {pf.fmt(t['b'], 3)}, 95% CI {pm.ci_str(t, 3)}, n = {f['n']} cells", "p": pf.fmt_p(t["p"]), "effect": None})

# second T1 falsifier: periphery following at stake 2 (COP) vs mismatched-issue benchmark, one-sided (following > benchmark), Holm within levels
fals = []
for lev, col in pm.LEVELS:
    g = d[(d.periphery == 1) & (d.stake == 2)][[col, BENCH[col]]].dropna()
    diff = g[col] - g[BENCH[col]]
    if len(diff) >= 3:
        t, p2 = sps.ttest_rel(g[col], g[BENCH[col]]); p1 = p2 / 2 if t > 0 else 1 - p2 / 2
        fals.append({"level": lev, "n": int(len(g)), "mean_follow": float(g[col].mean()), "mean_bench": float(g[BENCH[col]].mean()), "mean_diff": float(diff.mean()),
                     "sd_diff": float(diff.std(ddof=1)), "t": float(t), "p_one_sided": float(p1)})
    else:
        fals.append({"level": lev, "n": int(len(g)), "mean_follow": float(g[col].mean()) if len(g) else float("nan"), "mean_bench": float(g[BENCH[col]].mean()) if len(g) else float("nan"),
                     "mean_diff": float("nan"), "sd_diff": float("nan"), "t": float("nan"), "p_one_sided": float("nan")})
adj = pf.holm([x["p_one_sided"] for x in fals])
for x, a in zip(fals, adj):
    x["holm_p"] = a
    x["verdict"] = "falsifier does not hold (following above benchmark)" if (not np.isnan(a) and a < 0.05 and x["mean_diff"] > 0) else ("falsifier holds (following not above benchmark)" if not np.isnan(a) else "not testable (too few cells)")
    rows.append(["Second T1 falsifier: periphery following at high stake (COP) vs mismatched-issue benchmark", f"Mean following {pf.fmt(x['mean_follow'])} vs benchmark {pf.fmt(x['mean_bench'])}", pm.LEVEL_NAME[lev := x["level"]],
                 pf.fmt(x["mean_diff"], 3), f"paired t({x['n']-1}) = {pf.fmt(x['t'])}" if x["n"] >= 3 else "—", f"one-sided {pf.fmt_p(x['p_one_sided'])}, Holm {pf.fmt_p(x['holm_p'])}", str(x["n"]), x["verdict"]])
    stats.append({"name": f"falsifier2_{x['level']}", "value": f"periphery COP cells n = {x['n']}: following M = {pf.fmt(x['mean_follow'], 3)}, benchmark M = {pf.fmt(x['mean_bench'], 3)}, difference M = {pf.fmt(x['mean_diff'], 3)}, SD = {pf.fmt(x['sd_diff'], 3)}, paired t = {pf.fmt(x['t'])}", "p": f"one-sided {pf.fmt_p(x['p_one_sided'])}, Holm {pf.fmt_p(x['holm_p'])}", "effect": x["verdict"]})

# within-wars check: not run (stake sheets empty)
sheet = pd.read_csv(os.path.join(pf.P, "data/coded/stake_coding_author.csv"))
empty = sheet.iloc[:, 2].isna().all()
rows.append(["H3 check within the two wars with country × issue stake (A28)", "—", "All levels", "—", "—", "—", "—", "dropped (X14): the country × issue stake code would have been hand-coded; nothing in the study is hand-coded" if empty else "see fits.json"])

# Holm family decisions
fam = pm.family_holm(); fam_rows = []
for key in ["H1_salience", "H1_framing", "H1_timing", "H2_salience", "H2_framing", "H2_timing", "H3_salience", "H3_framing", "H3_timing"]:
    e = fam[key]; supported = e["sign_ok"] and e["holm_p"] < 0.05
    fam_rows.append([e["hypothesis"], {"periphery": "Tier (periphery)", "V4": "Wire reliance", "periphery:stake_lin": "Periphery × stake"}[e["term"]], pm.LEVEL_NAME[e["level"]], pf.fmt(e["b"], 3), f"[{pf.fmt(e['ci'][0], 3)}, {pf.fmt(e['ci'][1], 3)}]", pf.fmt_p(e["holm_p"]), str(e["n"]), "supported" if supported else "not supported"])
    stats.append({"name": f"holm_{key}", "value": f"b = {pf.fmt(e['b'], 3)}, 95% CI [{pf.fmt(e['ci'][0], 3)}, {pf.fmt(e['ci'][1], 3)}], unadjusted p = {pf.fmt_p(e['p'])}, Holm-adjusted p = {pf.fmt_p(e['holm_p'])}, n = {e['n']} cells", "p": pf.fmt_p(e["holm_p"]), "effect": "supported" if supported else "not supported"})
T6 = {"label": "T6", "title": "Mixed Models of Following on Tier × Local Stake (H3), the Second Falsifier, and Holm Decisions Across the Nine Confirmatory Tests", "answers": ["H1", "H2", "H3"],
      "columns": ["Model", "Predictor", "Level", "b", "95% CI", "p", "Cells (n)", "Random effects / decision"],
      "rows": fam_rows + rows,
      "note": ("The first nine rows give the Holm-adjusted decision for each confirmatory test (H1–H3 × salience, framing, timing; estimates from Tables T3 and T5 and this table; "
               "decision = positive coefficient and Holm-adjusted p < .05). H3 models: stake is coded Ukraine 0, Gaza 1, COP 2 and enters linearly with tier (periphery = 1); issue is dropped "
               "because stake and issue coincide; random intercepts for outlet nested in country. A positive periphery × stake coefficient means the decline in following from low to high stake "
               "is smaller among periphery outlets. The dummy-contrast and V10 models are robustness checks; V10 is the share of an outlet's issue stories whose title names its own country. "
               f"The second falsifier compares periphery following at high stake (the {next(x['n'] for x in fals if x['level']=='salience')} periphery COP cells; timing {next(x['n'] for x in fals if x['level']=='timing')} with both a value and a permuted benchmark) with the same cells' following against the core "
               "series or sample of a different issue (salience: Ukraine core series; framing: Ukraine core sample; timing: core first mentions permuted across events), paired t test, "
               "one-sided, Holm-adjusted within the three levels. The within-wars check with a country × issue stake code was dropped under deviation X14 (see the last row)."),
      "stats": stats}

# F2: following by stake and tier (cell means with 95% CIs)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
for ax, (lev, col) in zip(axes, pm.LEVELS):
    for tier, colr, off in (("periphery", "#d95f02", -0.06), ("semi-periphery", "#1b9e77", 0.06)):
        xs, ms, lo, hi = [], [], [], []
        for s in (0, 1, 2):
            g = d[(d.tier == tier) & (d.stake == s)][col].dropna()
            if len(g) < 2: continue
            m = g.mean(); e = sps.t.ppf(0.975, len(g) - 1) * g.std(ddof=1) / np.sqrt(len(g))
            xs.append(s + off); ms.append(m); lo.append(m - e); hi.append(m + e)
        ax.errorbar(xs, ms, yerr=[np.array(ms) - np.array(lo), np.array(hi) - np.array(ms)], fmt="o-", color=colr, capsize=3, label=tier.capitalize())
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["Ukraine (0)", "Gaza (1)", "COP (2)"], fontsize=8); ax.set_title(pm.LEVEL_NAME[lev], loc="left", fontsize=10)
    ax.set_ylabel({"salience": "Salience r", "framing": "Framing similarity", "timing": "Timing (−days)"}[lev], fontsize=9)
axes[0].legend(fontsize=8, frameon=False); fig.tight_layout()
d_out = os.path.join(pf.P, "results", run_id, "figures"); os.makedirs(d_out, exist_ok=True)
fig.savefig(os.path.join(d_out, "f2.svg")); fig.savefig(os.path.join(d_out, "f2.png"), dpi=150)
F2 = {"label": "F2", "title": "Following by Local Stake and Tier", "file": "figures/f2.svg", "note": "Cell means with 95% confidence intervals by issue stake (Ukraine 0, Gaza 1, COP27/COP28 2) and tier; timing over cells with at least 10 matched events."}
json.dump(fits, open(os.path.join(pf.P, "results", run_id, "fits.json"), "w"), indent=1)
json.dump({"falsifier2": fals, "family": fam}, open(os.path.join(pf.P, "results", run_id, "decisions.json"), "w"), indent=1)
summary = f"# {run_id} — P4 H3 stake models, second falsifier, Holm family\n\n## Holm family\n" + "\n".join(f"- {r[0]} {r[1]} {r[2]}: b = {r[3]}, CI {r[4]}, Holm p = {r[5]}, n = {r[6]} → {r[7]}" for r in fam_rows) + "\n\n## H3 and checks\n" + "\n".join(f"- {r[0]} · {r[1]} · {r[2]}: b = {r[3]}, CI {r[4]}, p = {r[5]}, n = {r[6]} — {r[7]}" for r in rows) + "\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T6], [F2], [], summary, started, DEV, notes="Within-wars country × issue stake check dropped (X14, no hand-coding). Holm decisions across the nine tests in T6. Supersedes run_20261006_06 (note corrected: timing cells of the second falsifier computed, not hard-coded) and run_20261006_04 (T6, F2).")
