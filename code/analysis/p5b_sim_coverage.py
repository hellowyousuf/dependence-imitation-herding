"""P5 read-out (no simulation): from the cached records of run_20261008_01, the number of outlet × issue cells with a simulated value
per level and configuration, stories published per seed, and the effective dependence cap B_i at the fitted w for every outlet.
Written after the critic's pass 2 (X15): the T4 errors are means over the cells that hold a value, which differs by configuration."""
import os, sys, json, math, collections, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf
SCRIPT = "data/analysis/p5b_sim_coverage.py"; DEV = ["X15"]
INPUTS = ["data/analysis/sim/_cache/p5_cache.json", "data/analysis/sim/outlets.json", "results/run_20261008_01/fits.json", "data/coded/following_cells.csv"]
started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); run_id = pf.new_run_id("p5b")
C = json.load(open(os.path.join(pf.P, "data/analysis/sim/_cache/p5_cache.json")))
outlets = json.load(open(os.path.join(pf.P, "data/analysis/sim/outlets.json")))
codes = {o["code"]: o["outlet"] for o in outlets}  # release: outlet names from outlets.json
_fc = pd.read_csv(os.path.join(pf.P, "data/coded/following_cells.csv")); _dom2name = dict(zip(_fc.outlet, _fc.name))
code2name = {k: _dom2name.get(v, v) for k, v in codes.items()}
fits = json.load(open(os.path.join(pf.P, "results/run_20261008_01/fits.json")))["params"]
NAMES = {"baseline": "Baseline (no rule)", "D": "Dependence", "I": "Imitation", "H": "Herding", "DI": "Dependence + imitation", "DH": "Dependence + herding", "IH": "Imitation + herding", "DIH": "All three"}
cov = collections.defaultdict(lambda: collections.defaultdict(list)); pub = collections.defaultdict(list)
for k, v in C.items():
    if not k.startswith("sim:"): continue
    parts = k[4:].split("|"); cfg, order = parts[0], parts[-1]
    if order != "DIH": continue
    recs = v["records"]
    for lev in ("V1", "V2", "V3a"):
        cov[cfg][lev].append(sum(1 for r in recs if r.get(lev) is not None and not (isinstance(r[lev], float) and math.isnan(r[lev]))))
    pub[cfg].append(sum(r["n_pub"] for r in recs))
rows = []
for cfg in NAMES:
    rows.append([NAMES[cfg], pf.fmt(np.mean(cov[cfg]["V1"]), 1), pf.fmt(np.mean(cov[cfg]["V2"]), 1), pf.fmt(np.mean(cov[cfg]["V3a"]), 1), f"{int(round(np.mean(pub[cfg]))):,}", str(len(pub[cfg]))])
T10 = {"label": "T10", "title": "Cells With a Simulated Value and Stories Published, by Configuration (Read-Out of the P5 Run)", "answers": ["RQ2"],
       "columns": ["Configuration", "Cells with a salience value (of 52)", "Cells with a framing value (of 52)", "Cells with a timing value (of 52)", "Stories published per seed (M)", "Seeds"],
       "rows": rows,
       "note": ("Read from the records of run_20261008_01 (no new simulation). A cell has a simulated salience value when at least 8 weeks hold at least 5 simulated stories, a framing value when at least 5 published items carry a coder frame, "
                "and a timing value when at least 3 published core or event items carry a first-core-mention lag; wire items carry no lag. The standardized errors in Table T4 are means over the cells that hold a value, so the timing error of a dependence configuration rests on the cells listed here. "
                "Means over the 20 seeds of the planned order (dependence, imitation, herding)."),
       "stats": [{"name": f"cells_timing_{cfg}", "value": f"{NAMES[cfg]}: timing value in {pf.fmt(np.mean(cov[cfg]['V3a']), 1)} of 52 cells per seed (M over {len(pub[cfg])} seeds); stories published per seed M = {int(round(np.mean(pub[cfg]))):,}", "p": None, "effect": None} for cfg in NAMES]}
# effective cap at the fitted w
w = fits["D"]["w"]; rows2 = []; zero = 0
for o in outlets:
    caps = {iss: int(round(o["n_i_daily_fitting_half"].get(iss, 0.0) * (1 - (o["W_i"] or 0.0)) * (w * (o["C_i"] or 0.0) + 1 - w))) for iss in ("ukraine", "gaza", "cop")}
    caps0 = {iss: int(round(o["n_i_daily_fitting_half"].get(iss, 0.0) * (1 - (o["W_i"] or 0.0)))) for iss in ("ukraine", "gaza", "cop")}
    allzero = all(v == 0 for v in caps.values()); zero += allzero
    rows2.append([code2name.get(o["code"], o["code"]), pf.fmt(o["W_i"] or 0.0), pf.fmt(o["C_i"] or 0.0), f"{caps['ukraine']} / {caps['gaza']} / {caps['cop']}", f"{caps0['ukraine']} / {caps0['gaza']} / {caps0['cop']}", "yes" if allzero else "no"])
T11 = {"label": "T11", "title": "Effective Daily Cap on Own Stories Under the Fitted Dependence Rule, by Outlet", "answers": ["RQ2"],
       "columns": ["Outlet", "Wire reliance W", "Correspondent presence C", f"Cap B at the fitted w = {pf.fmt(w)} (Ukraine / Gaza / COP)", "Cap B at w = 0 (Ukraine / Gaza / COP)", "Keeps no own story at the fitted w"],
       "rows": rows2,
       "note": (f"B = round(n × (1 − W) × (w × C + 1 − w)), with n the outlet's mean daily count of issue stories in the fitting half. At the fitted w = {pf.fmt(w)} the cap is n × (1 − W) × C, so an outlet with no staff foreign byline (C = 0.00) keeps no own proposal and publishes wire copy only. "
                f"{zero} of {len(outlets)} outlets keep no own story at the fitted w. Correspondent presence (V9) is exploratory (X12); the plan fixed it as the rule's C before the data."),
       "stats": [{"name": "outlets_cap_zero", "value": f"{zero} of {len(outlets)} outlets keep no own story at the fitted w = {pf.fmt(w)}", "p": None, "effect": None},
                 {"name": "fitted_w", "value": f"w = {pf.fmt(w)} (grid 0 to 1, 11 points); v = {pf.fmt(fits['I']['v'])} (grid 0 to 1); c = {pf.fmt(fits['H']['c'])} (grid 0.5 to 5)", "p": None, "effect": None}]}
summary = f"# {run_id} — P5 read-out: cell coverage and effective cap\n\n" + "\n".join(f"- {r[0]}: timing cells {r[3]}, published {r[4]}" for r in rows) + f"\n- outlets with cap 0 at fitted w: {zero} of {len(outlets)}\n"
pf.finish_run(run_id, SCRIPT, INPUTS, [T10, T11], [], [], summary, started, DEV, notes="Read-out of run_20261008_01's cached records and fitted parameters (X15); no simulation run. Grids from p5_simulation.py: w, v linspace(0, 1, 11); c linspace(0.5, 5, 11).")
print("run", run_id, "written")
