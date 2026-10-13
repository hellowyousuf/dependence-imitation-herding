#!/usr/bin/env python3
"""P5 step 6 — agent frame labels vs the model coder on 300 written-out proposals (plan: reliability.sample; A26; floor .80).
Reads data/raw/sim/written_out_proposals.jsonl (agent_frame) and data/coded/model/agent_labels/all_coded.json (the model
coder's frame for the written-out headline + lead, coded in fresh contexts from data/analysis/model_coder_prompt.md).
Writes data/coded/agent_label_check.json: Krippendorff's alpha (nominal), agreement, confusion; if alpha < .80 the plan's
fallback applies (simulated framing from coder codes on written-out proposals is not available for every proposal, so
the simulation keeps the agents' labels and the fallback is reported as a limit — see the report)."""
import json, collections, itertools, hashlib, datetime as dt, sys
sys.path.insert(0, "data/analysis")
from stability_alpha import alpha  # noqa
W = [json.loads(l) for l in open("data/raw/sim/written_out_proposals.jsonl")]
C = {x["sample_id"]: x for x in json.load(open("data/coded/model/agent_labels/all_coded.json"))}
pairs = []
for r in W:
    sid = f"agent|{r['code']}|{r['date']}|{r['feed']}|{r['sample']}|{r['id']}"
    if sid in C: pairs.append((r["agent_frame"], C[sid]["frame"]))
a = alpha([[x, y] for x, y in pairs]); agree = sum(x == y for x, y in pairs) / len(pairs)
conf = collections.Counter(pairs)
by_agent = collections.Counter(x for x, y in pairs); by_coder = collections.Counter(y for x, y in pairs)
rep = {"n": len(pairs), "alpha": a, "agreement": round(agree, 3), "floor": 0.8, "meets_floor": bool(a is not None and a >= 0.8),
       "agent_label_counts": dict(by_agent), "coder_counts": dict(by_coder),
       "confusion_agent_vs_coder": {f"{x}->{y}": n for (x, y), n in sorted(conf.items(), key=lambda kv: -kv[1])},
       "coder_model": "claude-opus-5-5", "prompt_sha256": hashlib.sha256(open("data/analysis/model_coder_prompt.md", "rb").read()).hexdigest(),
       "agent_model": "Qwen/Qwen3-14B", "coded": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
       "note": "Agent labels are the frame each agent gave its proposal at proposal time; the coder saw only the headline and lead the agent later wrote for it, plus the agent's country."}
json.dump(rep, open("data/coded/agent_label_check.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "confusion_agent_vs_coder"}, indent=1)); print(rep["confusion_agent_vs_coder"])
