#!/usr/bin/env python3
"""Validate a data file and register it in data/manifest.json (BUILD.md stage 6a; SCHEMA §8).

usage: register_data.py <project> <path-under-project> --id D<n> --title "..." --kind table|text|code|symbols|archive
         --origin url|api|file|generated --url URL --licence "..." --terms-ok yes|no --retrieved YYYY-MM-DD
         [--items N] [--collected-by build|author] [--notes "..."]

Validation (exit 1 on any failure; nothing is written):
  file exists and is non-empty; sha256 and bytes computed here; retrieved is an ISO date not after today;
  licence non-empty; terms_ok must be 'yes' (a file whose terms are not ok is never registered);
  the id is new, or re-registration of the same path (sha256 updated, old hash kept in `history`).
Appends {"action":"register_data",...} to runs.log.jsonl.
"""
import argparse, datetime as dt, hashlib, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("path")
    for k in ("id", "title", "kind", "origin", "url", "licence", "terms_ok", "retrieved"):
        ap.add_argument("--" + k.replace("_", "-"), required=True, dest=k)
    ap.add_argument("--items", type=int); ap.add_argument("--collected-by", default="build", dest="by")
    ap.add_argument("--notes", default="")
    a = ap.parse_args()
    P = a.project; f = os.path.join(P, a.path)
    errs = []
    if not a.path.startswith("data/raw/"): errs.append("path must be under data/raw/")
    if not os.path.isfile(f) or os.path.getsize(f) == 0: errs.append(f"missing or empty: {f}")
    try:
        d = dt.date.fromisoformat(a.retrieved)
        if d > dt.date.today(): errs.append("retrieved date is in the future")
    except ValueError: errs.append("retrieved is not YYYY-MM-DD")
    if not a.licence.strip(): errs.append("licence empty")
    if a.terms_ok != "yes": errs.append("terms_ok is not 'yes' — not registered")
    if a.kind not in ("text", "code", "symbols", "table", "archive"): errs.append("bad kind")
    if a.origin not in ("url", "api", "file", "generated"): errs.append("bad origin")
    if errs:
        print("REFUSED:", *errs, sep="\n  "); sys.exit(1)
    h = hashlib.sha256(open(f, "rb").read()).hexdigest()
    mp = os.path.join(P, "data/manifest.json"); m = json.load(open(mp))
    item = {"id": a.id, "kind": a.kind, "title": a.title, "origin": a.origin, "url": a.url, "path": a.path,
            "sha256": h, "bytes": os.path.getsize(f), "retrieved": a.retrieved, "licence": a.licence,
            "terms_ok": True, "human_subjects": False, "personal_data": "none", "collected_by": a.by,
            "items": a.items, "notes": a.notes,
            "registered": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    old = [x for x in m["items"] if x["id"] == a.id]
    if old:
        if old[0]["path"] != a.path: print(f"REFUSED: {a.id} already registered for {old[0]['path']}"); sys.exit(1)
        item["history"] = old[0].get("history", []) + [{"sha256": old[0]["sha256"], "registered": old[0].get("registered")}]
        m["items"] = [x if x["id"] != a.id else item for x in m["items"]]
    else:
        m["items"].append(item)
    m["items"].sort(key=lambda x: int(x["id"][1:]))
    json.dump(m, open(mp, "w"), indent=1, ensure_ascii=False)
    with open(os.path.join(P, "runs.log.jsonl"), "a") as g:
        g.write(json.dumps({"ts": item["registered"], "action": "register_data", "project": os.path.basename(os.path.normpath(P)),
                            "args": [a.id, a.path], "result": {"sha256": h, "bytes": item["bytes"], "items": a.items,
                            "origin": a.origin, "collected_by": a.by}}) + "\n")
    print(f"registered {a.id} {a.path} sha256={h[:12]}… items={a.items}")

if __name__ == "__main__":
    main()
