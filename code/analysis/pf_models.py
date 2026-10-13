#!/usr/bin/env python3
"""Mixed models for P2–P4 and P6 (plan: following ~ fixed effects + (1|outlet) + (1|country)); outlets nest in countries,
so the model is fitted with country as the grouping factor and outlet as a variance component (statsmodels MixedLM, REML).
A random-effect variance estimated at (or numerically at) zero is dropped and the model refitted; both fits are returned
(plan decision rule). Wald z tests, two-sided p, 95% CIs. The Holm family (nine confirmatory tests) is kept in
data/analysis/holm_family.json so that P4, run last, can report the family decisions."""
import json, os, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import ConvergenceWarning
import pf_common as pf

ZERO = 1e-6
LEVELS = [("salience", "V1"), ("framing", "V2"), ("timing", "V3a")]
LEVEL_NAME = {"salience": "Salience", "framing": "Framing", "timing": "Timing"}


def _fit(formula, data, groups, vc):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning); warnings.simplefilter("ignore", RuntimeWarning); warnings.simplefilter("ignore", UserWarning)
        kw = {"groups": data[groups], "re_formula": "1"}
        if vc: kw["vc_formula"] = {vc: f"0 + C({vc})"}
        m = smf.mixedlm(formula, data, **kw)
        r = None; err = None
        for meth in (["lbfgs", "powell"], ["nm"], ["cg"], ["bfgs"], ["powell"]):
            try:
                rr = m.fit(reml=True, method=meth, maxiter=5000)
                if np.all(np.isfinite(rr.bse[rr.fe_params.index].values)) and np.all(np.isfinite(rr.pvalues[rr.fe_params.index].values)):
                    r = rr; break
                err = "non-finite standard errors"
            except Exception as e:
                err = str(e)
        if r is None: return {"error": err}
    out = {"formula": formula, "groups": groups, "vc": vc, "n": int(r.nobs), "converged": bool(r.converged),
           "terms": {}, "var_country": None, "var_outlet": None, "var_resid": float(r.scale), "llf": float(r.llf)}
    names = list(r.params.index); ci = r.conf_int()
    for t in r.fe_params.index:
        out["terms"][t] = {"b": float(r.fe_params[t]), "se": float(r.bse[t]), "ci": [float(ci.loc[t, 0]), float(ci.loc[t, 1])],
                           "z": float(r.tvalues[t]), "p": float(r.pvalues[t])}
    # variance components
    cov = r.cov_re
    if groups == "country":
        out["var_country"] = float(cov.iloc[0, 0]) if cov.shape[0] else None
        if vc: out["var_outlet"] = float(r.vcomp[0])
    elif groups == "outlet":
        out["var_outlet"] = float(cov.iloc[0, 0]) if cov.shape[0] else None
    return out


def fit_mixed(formula, data, want=None):
    """→ {"main": fit, "refit": fit|None, "dropped": [...]} — refit drops any random effect at zero variance."""
    d = data.dropna(subset=[formula.split("~")[0].strip()]).copy()
    main = _fit(formula, d, "country", "outlet")
    res = {"main": main, "refit": None, "dropped": []}
    if "error" in main: return res
    zero_c = main["var_country"] is not None and main["var_country"] < ZERO
    zero_o = main["var_outlet"] is not None and main["var_outlet"] < ZERO
    if zero_c and zero_o:
        res["dropped"] = ["country", "outlet"]; res["refit"] = _ols(formula, d)
    elif zero_c:
        res["dropped"] = ["country"]; res["refit"] = _fit(formula, d, "outlet", None)
    elif zero_o:
        res["dropped"] = ["outlet"]; res["refit"] = _fit(formula, d, "country", None)
    if res["refit"] is not None and "error" in res["refit"]:
        # the reduced model did not fit; fall back to OLS (the remaining component was itself near zero) and say so
        res["refit"] = _ols(formula, d); res["dropped"] = res["dropped"] + ["(reduced mixed fit failed: OLS)"]
    return res


def _ols(formula, d):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = smf.ols(formula, d).fit()
    ci = r.conf_int()
    return {"formula": formula, "groups": None, "vc": None, "n": int(r.nobs), "converged": True,
            "terms": {t: {"b": float(r.params[t]), "se": float(r.bse[t]), "ci": [float(ci.loc[t, 0]), float(ci.loc[t, 1])], "z": float(r.tvalues[t]), "p": float(r.pvalues[t])} for t in r.params.index},
            "var_country": None, "var_outlet": None, "var_resid": float(r.scale), "llf": float(r.llf)}


def reported(res):
    """The fit the decision reads: the refit when a component was dropped, else the main fit."""
    return res["refit"] if res["refit"] else res["main"]


def term_row(fit, term):
    t = fit["terms"].get(term)
    if not t: return None
    return t


def ci_str(t, nd=2):
    return f"[{pf.fmt(t['ci'][0], nd)}, {pf.fmt(t['ci'][1], nd)}]"


def family_path():
    return os.path.join(pf.P, "data/analysis/holm_family.json")


def family_record(key, entry):
    """Store a confirmatory test's raw p and estimate under key (e.g. 'H1_salience')."""
    p = family_path(); fam = json.load(open(p)) if os.path.exists(p) else {}
    fam[key] = entry; json.dump(fam, open(p, "w"), indent=1)


def family_holm():
    p = family_path(); fam = json.load(open(p)) if os.path.exists(p) else {}
    keys = sorted(fam); adj = pf.holm([fam[k]["p"] for k in keys])
    return {k: dict(fam[k], holm_p=a) for k, a in zip(keys, adj)}


def cells_data():
    c = pd.read_csv(os.path.join(pf.P, "data/coded/following_cells.csv"))
    c = c[(c.tier != "core") & c.cell_kept].copy()
    c["periphery"] = (c.tier == "periphery").astype(int)
    c["stake_lin"] = c.stake.astype(float)
    return c


def fit_desc(fit):
    if not fit or "error" in fit: return "did not fit"
    parts = [f"n = {fit['n']}"]
    if fit["var_country"] is not None: parts.append(f"var(country) = {fit['var_country']:.4f}")
    if fit["var_outlet"] is not None: parts.append(f"var(outlet) = {fit['var_outlet']:.4f}")
    parts.append(f"residual = {fit['var_resid']:.4f}")
    return ", ".join(parts)
