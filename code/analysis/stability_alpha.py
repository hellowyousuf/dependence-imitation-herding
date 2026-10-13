#!/usr/bin/env python3
"""Stage 6b, X10 — stability and rule checks for the model coder on the 300-story reliability sample (floor .80).
  frame stability   Krippendorff's alpha (nominal) across passes 1-3 (frozen prompt, fresh contexts, shuffled order)
  prompt variation  alpha between pass 1 and the reworded-prompt pass
  credit variables  rule coder (code_rules.py) vs model pass 1 agreement and alpha, where the rule decides
  binary variables  alpha across passes 1-3
Writes data/coded/stability_report.json; unstable stories (passes disagree) listed for the record."""
import json, collections, itertools
P = "."
def load(s): return {r["sample_id"]: r for r in map(json.loads, open(f"{P}/data/coded/model_codes_{s}.jsonl"))}
def alpha(units):  # units: list of lists of values (missing excluded); nominal Krippendorff's alpha
    units = [[v for v in u if v is not None] for u in units]; units = [u for u in units if len(u) >= 2]
    o = collections.Counter()
    for u in units:
        m = len(u)
        for a, b in itertools.permutations(range(m), 2): o[(u[a], u[b])] += 1 / (m - 1)
    n_c = collections.Counter()
    for (a, b), w in o.items(): n_c[a] += w
    n = sum(n_c.values())
    if n <= 1: return None
    Do = sum(w for (a, b), w in o.items() if a != b) / n
    De = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n * (n - 1))
    return None if De == 0 else round(1 - Do / De, 3)
import sys
PASSES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["reliability_v2_p1", "reliability_v2_p2", "reliability_v2_p3"]
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/coded/stability_report.json"
p = [load(s) for s in PASSES]; v = load("reliability_variant")  # variant prompt: frame wording only is compared
R = {r["sample_id"]: r for r in map(json.loads, open(f"{P}/data/coded/rule_codes.jsonl"))}
ids = sorted(p[0])
rep = {"passes": PASSES, "floor": 0.8, "n": len(ids), "model": "claude-opus-5-5", "frame": {}, "binary": {}, "rules_vs_model": {}}
fr = [[x[i]["frame"] for x in p] for i in ids]
rep["frame"]["alpha_passes_1_3"] = alpha(fr)
rep["frame"]["all_three_agree"] = sum(len(set(u)) == 1 for u in fr)
rep["frame"]["alpha_pass1_vs_variant"] = alpha([[p[0][i]["frame"], v[i]["frame"]] for i in ids])
rep["frame"]["agree_pass1_vs_variant"] = sum(p[0][i]["frame"] == v[i]["frame"] for i in ids)
per = {}
for c in sorted({f for u in fr for f in u}):
    us = [u for u in fr if c in u]
    per[c] = {"stories_with_code": len(us), "all_three_agree": sum(len(set(u)) == 1 for u in us)}
rep["frame"]["per_code"] = per
rep["frame"]["majority_counts"] = dict(collections.Counter(collections.Counter(u).most_common(1)[0][0] for u in fr))
conf = collections.Counter()
for u in fr:
    if len(set(u)) > 1: conf[" / ".join(sorted(set(u)))] += 1
rep["frame"]["unstable_pairs"] = dict(conf.most_common(10))
rep["frame"]["unstable_ids"] = [i for i, u in zip(ids, fr) if len(set(u)) > 1]
for b in ("foreign_story", "wire_credit", "national_agency_credit", "staff_foreign_byline"):
    rep["binary"][b] = {"alpha_passes_1_3": alpha([[x[i][b] for x in p] for i in ids]),
                        "alpha_pass1_vs_variant": alpha([[p[0][i][b], v[i][b]] for i in ids]),
                        "prevalence_pass1": sum(p[0][i][b] for i in ids)}
    dec = [i for i in ids if R.get(i, {}).get(b) is not None]
    rep["rules_vs_model"][b] = {"rule_decides": len(dec), "agree": sum(R[i][b] == p[0][i][b] for i in dec),
                                "alpha": alpha([[R[i][b], p[0][i][b]] for i in dec])}
json.dump(rep, open(OUT, "w"), indent=1)
show = {k: v for k, v in rep["frame"].items() if k != "unstable_ids"}
print(json.dumps(show, indent=1)); print(json.dumps(rep["binary"], indent=1)); print(json.dumps(rep["rules_vs_model"], indent=1))
