#!/usr/bin/env python3
"""Stage 6a, author step M2 — Media Cloud round 2: one extra outlet (X5: daily-sun.com).
Same queries, period and output shapes as round 1 (collect_mediacloud_r1.py); appends to r2_* files. Resumable.
Run (same venv and key as round 1):  python3 data/analysis/collect_mediacloud_r2.py
"""
import os, sys, json, importlib.util, datetime as dt
ARGS = sys.argv[1:]; sys.argv = [sys.argv[0]]
spec = importlib.util.spec_from_file_location("r1", os.path.join("data", "analysis", "collect_mediacloud_r1.py"))
src = open(spec.origin).read().split("# 1 collections")[0]   # reuse settings, client, helpers only
exec(compile(src, "r1_head", "exec"))
# usage: collect_mediacloud_r2.py [TAG COUNTRY:domain ...]   (default: r2 Bangladesh:daily-sun.com)
import sys as _s
TAG = ARGS[0] if ARGS else "r2"
EXTRA = [tuple(a.split(":", 1)) for a in ARGS[1:]] or [("Bangladesh", "daily-sun.com")]
sp = os.path.join(OUT, f"_state_{TAG}.json"); st = json.load(open(sp)) if os.path.exists(sp) else {}
def save(): json.dump(st, open(sp, "w"), indent=1)
deep = []
for grp, d in EXTRA:
    res = call(D.source_list, name=d.split(".")[0], platform="online_news", limit=50)["results"]
    m = [x for x in res if x["name"] in (d, "www." + d)]
    print(d, "→", [x["id"] for x in m] or "NOT FOUND", "| similar:", [x["name"] for x in res][:8])
    for x in m:  # a site can sit under two Media Cloud sources (with and without www.): collect both
        deep.append((grp, d, x["id"]))
with open(os.path.join(OUT, f"{TAG}_source_weeks.jsonl"), "a") as g:
    for grp, d, sid in deep:
        for q_name, q in [("all", LANG)] + [(k, f"{v} AND {LANG}") for k, v in ISSUES.items()]:
            tag = f"{sid}:{q_name}"
            if tag in st.get("weeks_done", []): continue
            for a, b in chunks(START, END):
                for row in call(S.story_count_over_time, q, a, b, source_ids=[sid]):
                    g.write(json.dumps({"group": grp, "domain": d, "source_id": sid, "query": q_name, **row}, default=str) + "\n")
            st.setdefault("weeks_done", []).append(tag); save()
        print("weeks", d)
for issue, q in ISSUES.items():
    with open(os.path.join(OUT, f"{TAG}_stories_{issue}.jsonl"), "a") as g:
        for grp, d, sid in deep:
            for a, b in chunks(START, END):
                tag = f"{issue}:{sid}:{a}"; s0 = st.setdefault("stories", {}).get(tag)
                if s0 == "done": continue
                token = s0
                while True:
                    page, token = call(S.story_list, f"{q} AND {LANG}", a, b, source_ids=[sid], pagination_token=token, page_size=1000)
                    for s in page:
                        g.write(json.dumps({"group": grp, "source_id": sid, "domain": d, "issue": issue,
                            **{k: s.get(k) for k in ("id", "url", "title", "publish_date", "indexed_date", "language", "media_name", "media_url")}}, default=str) + "\n")
                    g.flush(); st["stories"][tag] = token if token else "done"; save()
                    if not token: break
            print("stories", issue, d)
json.dump({"complete": True, "requested": EXTRA, "finished": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "sources": deep},
          open(os.path.join(OUT, f"{TAG}_meta.json"), "w"), indent=1)
print("DONE — reply 'data ready' in the chat.")
