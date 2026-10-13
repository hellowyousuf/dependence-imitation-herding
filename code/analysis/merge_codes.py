#!/usr/bin/env python3
"""Stage 6b, X10-X12 — final story codes (data/coded/codes_final.jsonl) and the full-sample rule-vs-model check.
Credit variables (V4 wire_credit, V11 national_agency_credit): the rule coder (code_rules.py) decides; the model coder
is the cross-check. foreign_story and V9 staff_foreign_byline: the rule where it decides (dateline / credit), otherwise
the model coder (prompt v2). Frame (V2/V7): the model coder (prompt v2, one pass); text_window flags X11 headline-only
records. V9 is exploratory (X12). Writes data/coded/codes_final.jsonl and data/coded/rule_model_check.json."""
import json, collections, sys
sys.path.insert(0, "data/analysis")
import importlib.util, types
_src = open("data/analysis/stability_alpha.py").read().split("import sys")[0]  # the alpha() helper only
_mod = types.ModuleType("sa"); exec(_src, _mod.__dict__); alpha = _mod.alpha
T = {r["sample_id"]: r for r in map(json.loads, open("data/coded/coding_texts.jsonl"))}
R = {r["sample_id"]: r for r in map(json.loads, open("data/coded/rule_codes.jsonl"))}
M = {r["sample_id"]: r for r in map(json.loads, open("data/coded/model_codes_all.jsonl"))}
rel = set(json.load(open("data/coded/reliability_sample.json"))["sample_ids"])
assert set(R) == set(M), (len(R), len(M))
out, chk = [], {}
for i in sorted(M):
    t, r, m = T[i], R[i], M[i]
    rec = {"sample_id": i, "outlet": t["outlet"], "country": t["country"], "tier": t["tier"], "issue": t["issue"], "date": t["date"],
           "frame": m["frame"], "text_window": t.get("text_window", "headline_lead"),
           "wire_credit": r["wire_credit"], "wire_rule": r["wire_rule"], "national_agency_credit": r["national_agency_credit"],
           "foreign_story": r["foreign_story"] if r["foreign_story"] is not None else m["foreign_story"],
           "foreign_method": r["foreign_method"],
           "staff_foreign_byline": r["staff_foreign_byline"] if r["staff_foreign_byline"] is not None else m["staff_foreign_byline"],
           "staff_method": r["staff_method"], "v9_status": "exploratory (X12)",
           "model": m["model"], "prompt_sha256": m["prompt_sha256"], "in_reliability_sample": i in rel}
    out.append(rec)
with open("data/coded/codes_final.jsonl", "w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
for scope, ids in (("all", sorted(M)), ("outside_reliability_sample", sorted(set(M) - rel))):
    chk[scope] = {}
    for v in ("wire_credit", "national_agency_credit", "foreign_story", "staff_foreign_byline"):
        dec = [i for i in ids if R[i][v] is not None and not (v == "wire_credit" and R[i]["wire_rule"] == "syndication_url")]  # X11: by design
        dis = [i for i in dec if R[i][v] != M[i][v]]
        chk[scope][v] = {"rule_decides": len(dec), "agree": len(dec) - len(dis), "alpha": alpha([[R[i][v], M[i][v]] for i in dec]),
                         "disagreements_sample": dis[:25]}
v2 = {r["sample_id"]: r for r in map(json.loads, open("data/coded/model_codes_reliability_v2_p1.jsonl"))}
chk["frame_all_pass_vs_reliability_v2_p1"] = {"n": len(rel), "agree": sum(M[i]["frame"] == v2[i]["frame"] for i in rel),
                                              "alpha": alpha([[M[i]["frame"], v2[i]["frame"]] for i in rel])}
chk["x11_syndication_url_rows"] = sum(1 for i in M if R[i]["wire_rule"] == "syndication_url")
json.dump(chk, open("data/coded/rule_model_check.json", "w"), indent=1)
print(json.dumps({k: (v if not isinstance(v, dict) or k.startswith("frame") else {x: {y: z for y, z in w.items() if y != "disagreements_sample"} for x, w in v.items()}) for k, v in chk.items()}, indent=1))
c = collections.Counter((r["tier"], r["frame"]) for r in out)
print("frames by tier:", {t: dict(sorted({f: n for (tt, f), n in c.items() if tt == t}.items())) for t in sorted({r["tier"] for r in out})})
