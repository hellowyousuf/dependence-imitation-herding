#!/usr/bin/env python3
"""Stage 6b — model-assisted coding (plan: reliability.coders; codebook C2, C4, C8, C10).

The model coder is a Claude model run through the author's subscription: the build's model in fresh contexts that see
only data/analysis/model_coder_prompt.md and one batch file (no coder sees another's codes). This script prepares the
batches and records the answers; it records the model id, the prompt's sha256 and the date of every code.

  prepare <set> [--batch 25] [--prompt FILE] [--shuffle SEED]
                               set = reliability | reliability_p2 | reliability_p3 | reliability_variant | all;
                               writes data/coded/model/<set>/batch_NNN.json (X10 stability passes: same 300 stories in a
                               seeded random order, fresh contexts; the variant pass uses the reworded prompt)
  record  <set> <batch_NNN.out.json> --model <exact model id>   validates and appends to data/coded/model_codes_<set>.jsonl
  status  <set>
"""
import json, os, sys, hashlib, glob, datetime as dt, argparse
P = "."
PROMPT = os.path.join(P, "data/analysis/model_coder_prompt.md")
if "--prompt" in sys.argv: PROMPT = sys.argv[sys.argv.index("--prompt") + 1]
FR = {"episodic", "thematic", "conflict", "human_interest", "responsibility", "economic", "other"}
BIN = ("foreign_story", "wire_credit", "national_agency_credit", "staff_foreign_byline")
def texts():
    return {r["sample_id"]: r for r in map(json.loads, open(os.path.join(P, "data/coded/coding_texts.jsonl")))
            if not any(k in r for k in ("invalid", "needs_refetch", "dup_of", "surplus"))}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("set"); ap.add_argument("file", nargs="?")
ap.add_argument("--batch", type=int, default=25); ap.add_argument("--model", default="")
ap.add_argument("--prompt", default=PROMPT); ap.add_argument("--shuffle", default="")
a = ap.parse_args(); D = os.path.join(P, "data/coded/model", a.set); os.makedirs(D, exist_ok=True)
OUTF = os.path.join(P, f"data/coded/model_codes_{a.set}.jsonl")
if a.cmd == "prepare":
    T = texts()
    ids = (json.load(open(os.path.join(P, "data/coded/reliability_sample.json")))["sample_ids"] if a.set.startswith("reliability") else sorted(T))
    if a.shuffle:
        ids = sorted(ids, key=lambda i: hashlib.sha256(f"{a.shuffle}|{i}".encode()).hexdigest())
    items = [{k: T[i][k] for k in ("sample_id", "outlet", "country", "headline", "lead", "byline", "last_paragraph")} for i in ids if i in T]
    for n in range(0, len(items), a.batch):
        json.dump({"prompt_sha256": sha(PROMPT), "prompt_file": os.path.relpath(PROMPT, P), "items": items[n:n + a.batch]},
                  open(os.path.join(D, f"batch_{n // a.batch + 1:03d}.json"), "w"), indent=1, ensure_ascii=False)
    print(len(items), "items in", (len(items) + a.batch - 1) // a.batch, "batches →", D)
elif a.cmd == "record":
    if not a.model: sys.exit("--model <exact model id> is required")
    bf = a.file.replace(".out.json", ".json"); batch = json.load(open(bf)); want = [x["sample_id"] for x in batch["items"]]
    out = json.load(open(a.file)); got = {o["sample_id"]: o for o in out}
    errs = [i for i in want if i not in got] + [o["sample_id"] for o in out if o.get("frame") not in FR or any(o.get(b) not in (0, 1) for b in BIN)]
    if errs: sys.exit(f"REFUSED {a.file}: missing or invalid codes for {errs[:5]} …")
    if batch["prompt_sha256"] != sha(PROMPT): sys.exit("REFUSED: prompt changed since the batch was prepared")
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(OUTF, "a") as g:
        for i in want:
            g.write(json.dumps({**{k: got[i][k] for k in ("sample_id", "frame") + BIN}, "note": got[i].get("note", ""),
                                "model": a.model, "prompt_sha256": batch["prompt_sha256"], "coded_at": ts,
                                "batch": os.path.basename(bf)}, ensure_ascii=False) + "\n")
    with open(os.path.join(P, "runs.log.jsonl"), "a") as g:
        g.write(json.dumps({"ts": ts, "action": "model_coder", "project": "periphery_follows_v5", "args": [a.set, os.path.basename(bf)],
                            "result": {"items": len(want), "model": a.model, "prompt_sha256": batch["prompt_sha256"]}}) + "\n")
    print("recorded", len(want))
elif a.cmd == "status":
    b = sorted(glob.glob(os.path.join(D, "batch_[0-9][0-9][0-9].json")))
    done = {json.loads(l)["batch"] for l in open(OUTF)} if os.path.exists(OUTF) else set()
    print(len(b), "batches;", len(done & {os.path.basename(x) for x in b}), "recorded")
