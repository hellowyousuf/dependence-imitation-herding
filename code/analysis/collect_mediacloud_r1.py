#!/usr/bin/env python3
"""Stage 6a, author step M1 — Media Cloud round 1 (run on the author's Mac with his own Media Cloud key).

What it collects (story METADATA only — id, url, title, publish date, outlet, language; no article text):
  1. the six '<Country> - National' collections (ids recorded);
  2. per country, the top 25 sources by English story count in the national collection over the period
     (candidates for the A30 rule: three general-interest national outlets with the most stories, >= 80% of weeks);
  3. for the top 6 English candidates per country + the four core outlets + AP, Reuters, AFP:
     daily counts of each issue's stories and of all the source's stories (count-over-time);
  4. the census of issue stories for those sources (three codebook-C1 queries, verbatim);
  5. a text-access pilot: does this account receive article text (story endpoint / expanded list)? — 5 stories, the
     text itself is NOT saved, only whether it is present and its length.

Run:
  cd "<...>/Research Assistant/projects/periphery_follows_v5"
  python3 -m pip install --user mediacloud==5.1.0
  export MC_API_KEY="<your key from search.mediacloud.org → Your Profile>"
  python3 data/analysis/collect_mediacloud_r1.py
Resumable: re-run the same command after any interruption; finished parts are skipped.
The key is read from the environment only and never written to disk.
Output: data/raw/mediacloud/r1_*.json|jsonl  (see r1_meta.json when it finishes: "complete": true)
"""
import datetime as dt, json, os, sys, time
import mediacloud, mediacloud.api

OUT = os.path.join("data", "raw", "mediacloud"); os.makedirs(OUT, exist_ok=True)
START, END = dt.date(2022, 2, 24), dt.date(2024, 12, 31)
COUNTRIES = ["Bangladesh", "Kenya", "Nigeria", "India", "South Africa", "Malaysia"]
LANG = "language:en"
ISSUES = {  # codebook C1, verbatim terms
    "ukraine": "(Ukraine OR Ukrainian OR Kyiv OR Kiev OR Zelensky OR (Russia AND invasion))",
    "gaza": "(Gaza OR Hamas OR (Israel AND (war OR strike OR ceasefire OR hostages)))",
    "cop": "(COP27 OR COP28 OR (climate AND (summit OR conference) AND (Sharm OR Dubai OR UNFCCC)))",
}
CORE = ["nytimes.com", "washingtonpost.com", "theguardian.com", "bbc.com", "bbc.co.uk"]
WIRES = ["apnews.com", "reuters.com", "afp.com"]
N_CAND, N_DEEP = 25, 6

key = os.environ.get("MC_API_KEY") or sys.exit("set MC_API_KEY first")
class ServerError(Exception):
    def __init__(self, code, body): self.code = code; super().__init__(f"HTTP {code}: {body[:160]!r}")
def _query(self, endpoint, params=None, method="GET"):
    r = self._session.get(self.BASE_API_URL + endpoint, params=params, timeout=self.TIMEOUT_SECS)
    try: data = r.json()
    except ValueError: raise ServerError(r.status_code, r.text)
    if r.status_code // 100 != 2: raise ServerError(r.status_code, str(data.get("note", data)))
    return data
mediacloud.api.BaseApi._query = _query
D, S = mediacloud.api.DirectoryApi(key), mediacloud.api.SearchApi(key)
D.TIMEOUT_SECS = S.TIMEOUT_SECS = 600
def chunks(a, b, days=91):  # long ranges time out on the server: query in quarters
    out, x = [], a
    while x <= b:
        y = min(b, x + dt.timedelta(days=days - 1)); out.append((x, y)); x = y + dt.timedelta(days=1)
    return out
state_p = os.path.join(OUT, "_state.json")
state = json.load(open(state_p)) if os.path.exists(state_p) else {}
def save_state(): json.dump(state, open(state_p, "w"), indent=1)
def call(f, *a, **k):
    for i in range(8):
        try:
            r = f(*a, **k); time.sleep(0.4); return r
        except Exception as e:
            code = getattr(e, "code", 0)
            if 400 <= code < 500 and code != 429:  # a request error will not fix itself: stop, do not retry
                raise SystemExit(f"Media Cloud refused the request ({code}): {str(e)[:300]}\nSend this message to the chat.")
            w = min(300, 5 * 2 ** i); print(f"  retry in {w}s ({type(e).__name__}): {str(e)[:200]}"); time.sleep(w)
    raise SystemExit("Media Cloud kept failing — re-run later; progress is saved.")
def dump(name, obj): json.dump(obj, open(os.path.join(OUT, name), "w"), indent=1, default=str)

# 1 collections
if "collections" not in state:
    cols = {}
    for c in COUNTRIES:
        res = call(D.collection_list, platform="online_news", name=c, limit=100)["results"]
        cols[c] = {"matches": [{k: r.get(k) for k in ("id", "name", "notes", "public", "featured", "monitored")} for r in res]}
        nat = [r for r in res if r["name"].strip().lower() == f"{c} - national".lower()] or \
              [r for r in res if "national" in r["name"].lower() and c.lower() in r["name"].lower()]
        cols[c]["national_id"] = nat[0]["id"] if nat else None
        print(c, "→", cols[c]["national_id"], nat[0]["name"] if nat else "NOT FOUND")
    state["collections"] = cols; dump("r1_collections.json", cols); save_state()

# 2 candidates per country
if "candidates" not in state:
    cand = {}
    for c, v in state["collections"].items():
        if not v["national_id"]: cand[c] = []; continue
        top = call(S.sources, LANG, START, END, collection_ids=[v["national_id"]])[:N_CAND]  # server rejects a limit argument (Sept 29, 2026)
        rows = []
        for t in top:
            m = call(D.source_list, name=t["source"], platform="online_news", limit=10)["results"]
            m = [x for x in m if x["name"] == t["source"]] or m
            src = m[0] if m else {}
            rows.append({"domain": t["source"], "en_stories": t["count"], "source_id": src.get("id"),
                         "label": src.get("label"), "homepage": src.get("homepage"), "media_type": src.get("media_type"),
                         "pub_country": src.get("pub_country"), "primary_language": src.get("primary_language")})
        cand[c] = rows; print(c, [r["domain"] for r in rows[:N_DEEP]])
    ref = {}
    for d in CORE + WIRES:
        m = call(D.source_list, name=d, platform="online_news", limit=10)["results"]
        m = [x for x in m if x["name"] == d]
        ref[d] = {"source_id": m[0]["id"] if m else None, "label": m[0].get("label") if m else None}
    state["candidates"] = cand; state["reference"] = ref
    dump("r1_candidates.json", {"period": [str(START), str(END)], "query": LANG, "countries": cand, "core_and_wires": ref})
    save_state()

deep = []
for c, rows in state["candidates"].items():
    deep += [(c, r["domain"], r["source_id"]) for r in [r for r in rows if r["source_id"] and r["domain"] not in CORE + WIRES][:N_DEEP]]
deep += [("core" if d in CORE else "wire", d, v["source_id"]) for d, v in state["reference"].items() if v["source_id"]]

# 3 daily counts per deep source: matching stories and the source's total that day (summed to weeks in 6a)
wk = os.path.join(OUT, "r1_source_weeks.jsonl"); done = set(state.get("weeks_done", []))
with open(wk, "a") as g:
    for grp, d, sid in deep:
        for q_name, q in [("all", LANG)] + [(k, f"{v} AND {LANG}") for k, v in ISSUES.items()]:
            tag = f"{sid}:{q_name}"
            if tag in done: continue
            for a, b in chunks(START, END):
                for row in call(S.story_count_over_time, q, a, b, source_ids=[sid]):
                    g.write(json.dumps({"group": grp, "domain": d, "source_id": sid, "query": q_name,
                                        **row}, default=str) + "\n")
            done.add(tag); state["weeks_done"] = sorted(done); save_state(); g.flush()
        print("weeks", d)

# 4 census of issue stories (metadata), one quarter at a time
for issue, q in ISSUES.items():
    p = os.path.join(OUT, f"r1_stories_{issue}.jsonl")
    with open(p, "a") as g:
        for grp, d, sid in deep:
            for a, b in chunks(START, END):
                tag = f"{issue}:{sid}:{a}"; st = state.setdefault("stories", {}).get(tag)
                if st == "done": continue
                token = st; n = 0
                while True:
                    page, token = call(S.story_list, f"{q} AND {LANG}", a, b, source_ids=[sid],
                                       pagination_token=token, page_size=1000)
                    for s in page:
                        g.write(json.dumps({"group": grp, "source_id": sid, "domain": d, "issue": issue,
                                            **{k: s.get(k) for k in ("id", "url", "title", "publish_date", "indexed_date",
                                                                     "language", "media_name", "media_url")}}, default=str) + "\n")
                    n += len(page); g.flush()
                    state["stories"][tag] = token if token else "done"; save_state()
                    if not token: break
                print(f"stories {issue} {d} {a}: +{n}")

# 5 text-access pilot (text itself not saved)
if "pilot" not in state:
    first = [json.loads(l) for l in open(os.path.join(OUT, "r1_stories_ukraine.jsonl")) ][:5]
    res = []
    for s in first:
        try:
            full = call(S.story, s["id"]); res.append({"id": s["id"], "domain": s["domain"], "story_has_text": bool(full.get("text")),
                                                     "text_chars": len(full.get("text") or "")})
        except SystemExit: res.append({"id": s["id"], "error": "failed"})
    try:
        pg, _ = S.story_list(f"{ISSUES['ukraine']} AND {LANG}", START, START + dt.timedelta(days=7),
                             source_ids=[deep[0][2]], expanded=True, page_size=5)
        exp = {"expanded_has_text": any(bool(x.get("text")) for x in pg), "n": len(pg)}
    except Exception as e:
        exp = {"expanded_error": str(e)[:300]}
    state["pilot"] = {"story_endpoint": res, "expanded_list": exp}; dump("r1_text_pilot.json", state["pilot"]); save_state()

dump("r1_meta.json", {"complete": True, "finished": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                      "client": f"mediacloud {getattr(mediacloud, '__version__', '5.1.0')}", "api_version": call(S.version),
                      "period": [str(START), str(END)], "language": LANG, "issues": ISSUES,
                      "deep_sources": [{"group": a, "domain": b, "source_id": c} for a, b, c in deep]})
print("DONE — reply 'data ready' in the chat.")
