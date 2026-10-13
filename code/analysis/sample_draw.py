#!/usr/bin/env python3
"""Stage 6a — census cleaning and the coded-sample draw (plan: sampling.procedure; codebook C1; A17, A30; X4–X7).

Census = Media Cloud issue stories (D5–D7) of the selected outlets, period Feb 24, 2022–Dec 31, 2024.
  dedupe: same normalized URL (scheme, www., query, fragment, trailing slash removed); then same normalized title on
          the same day within an outlet (stand-in for the plan's >= 90% text overlap: no text is held at this point).
Coded sample per outlet x issue:
  exclude opinion pieces by section label in the URL path (opinion, op-ed, oped, editorial(s), column(s), letters, blog(s));
  cells with < 20 census stories are dropped (A17); cells with 20-49 are taken whole; else a simple random sample of 50.
  Each cell is a seeded random permutation (seed = first 8 bytes of sha256("periphery_follows_v5|<outlet>|<issue>")), so
  draws do not depend on order or on other cells; rows after rank 50 are the replacement queue (plan: an unretrievable
  text is replaced by the next draw, logged).
Bangladesh (X5) is added from GDELT later with the same rules (--extra file).
Writes data/sampling/cells.csv, data/sampling/census_urls.csv (deduplicated census, for the BigQuery upload), data/sampling/sample_ranked.csv (rank <= 50 + up to 50 reserves), data/sampling/sample_log.json.
"""
import json, csv, hashlib, random, re, sys, os, collections
from urllib.parse import urlparse
P = sys.argv[1] if len(sys.argv) > 1 else "."
OUTLETS = {  # outlet: (country, group, Media Cloud domain, host filter or None)
 "the-star.co.ke": ("Kenya", "periphery", "the-star.co.ke", None), "nation.africa": ("Kenya", "periphery", "nation.africa", None),
 "tuko.co.ke": ("Kenya", "periphery", "tuko.co.ke", None),
 "iol.co.za": ("South Africa", "periphery", "iol.co.za", None), "citizen.co.za": ("South Africa", "periphery", "citizen.co.za", None),
 "timeslive.co.za": ("South Africa", "periphery", "timeslive.co.za", None),
 "punchng.com": ("Nigeria", "semi-periphery", "punchng.com", None), "dailypost.ng": ("Nigeria", "semi-periphery", "dailypost.ng", None),
 "tribuneonlineng.com": ("Nigeria", "semi-periphery", "tribuneonlineng.com", None),
 "timesofindia": ("India", "semi-periphery", "indiatimes.com", "timesofindia.indiatimes.com"),
 "hindustantimes.com": ("India", "semi-periphery", "hindustantimes.com", None), "thehindu.com": ("India", "semi-periphery", "thehindu.com", None),
 "malaymail.com": ("Malaysia", "semi-periphery", "malaymail.com", None),
 "newsarawaktribune.com.my": ("Malaysia", "semi-periphery", "newsarawaktribune.com.my", None),
 "malaysiakini.com": ("Malaysia", "semi-periphery", "malaysiakini.com", None),
 "nytimes.com": ("core", "core", "nytimes.com", None), "washingtonpost.com": ("core", "core", "washingtonpost.com", None),
 "theguardian.com": ("core", "core", "theguardian.com", None), "bbc": ("core", "core", "bbc.com", None),
}
OPINION = re.compile(r"/(opinion|opinions|op-ed|oped|editorial|editorials|column|columns|columnists|letters|blogs?|commentisfree)(/|$|-)", re.I)
def nurl(u):
    p = urlparse(u or ""); h = p.netloc.lower()
    h = h[4:] if h.startswith("www.") else h
    return h + p.path.rstrip("/")
def ntitle(t): return re.sub(r"\W+", " ", (t or "").lower()).strip()
def seed(o, i): return int.from_bytes(hashlib.sha256(f"periphery_follows_v5|{o}|{i}".encode()).digest()[:8], "big")
by_dom = collections.defaultdict(list)
for o, v in OUTLETS.items(): by_dom[v[2]].append(o)
cells = collections.defaultdict(list); log = collections.Counter()
files = [f"data/raw/mediacloud/r1_stories_{i}.jsonl" for i in ("ukraine", "gaza", "cop")]
extra = sys.argv[2:]  # optional GDELT-derived census files with the same fields + "outlet", "country", "group"
for f in files + extra:
    for l in open(os.path.join(P, f)):
        r = json.loads(l)
        outs = [r["outlet"]] if "outlet" in r else by_dom.get(r.get("domain"), [])
        for o in outs:
            if "outlet" not in r:
                hf = OUTLETS[o][3]
                if hf and urlparse(r["url"]).netloc.lower() != hf: log["host_filtered"] += 1; continue
            d = (r.get("publish_date") or "")[:10]
            if not ("2022-02-24" <= d <= "2024-12-31"): log["out_of_period"] += 1; continue
            cells[(o, r["issue"])].append(r)
rows_c, rows_s, census = [], [], []
for (o, i), rs in sorted(cells.items()):
    seen_u, seen_t, uniq = set(), set(), []
    for r in sorted(rs, key=lambda r: (r.get("publish_date") or "", r["url"])):
        u = nurl(r["url"]); t = (ntitle(r.get("title")), (r.get("publish_date") or "")[:10])
        if u in seen_u: log["dup_url"] += 1; continue
        if t[0] and t in seen_t: log["dup_title_day"] += 1; continue
        seen_u.add(u); seen_t.add(t); uniq.append(r)
    census += [[o, i, (r.get("publish_date") or "")[:10], nurl(r["url"]).lower()] for r in uniq]
    elig = [r for r in uniq if not OPINION.search(urlparse(r["url"]).path)]
    country, group = (OUTLETS[o][0], OUTLETS[o][1]) if o in OUTLETS else (rs[0]["country"], rs[0]["group"])
    status = "dropped (<20 stories, A17)" if len(uniq) < 20 else ("whole cell" if len(elig) < 50 else "random 50")
    rows_c.append([country, group, o, i, len(rs), len(uniq), len(uniq) - len(elig), len(elig), status])
    if len(uniq) < 20: continue
    random.Random(seed(o, i)).shuffle(elig)
    for k, r in enumerate(elig[:100], 1):
        rows_s.append([f"{o}|{i}|{k:03d}", country, group, o, i, k, "sample" if k <= 50 else "reserve",
                       (r.get("publish_date") or "")[:10], r.get("title", ""), r["url"], r.get("id", "")])
os.makedirs(os.path.join(P, "data/sampling"), exist_ok=True)
with open(os.path.join(P, "data/sampling/cells.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["country", "group", "outlet", "issue", "census_raw", "census_dedup", "opinion_excluded", "eligible", "status"]); w.writerows(rows_c)
with open(os.path.join(P, "data/sampling/sample_ranked.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["sample_id", "country", "group", "outlet", "issue", "rank", "role", "date", "title", "url", "mc_id"]); w.writerows(rows_s)
with open(os.path.join(P, "data/sampling/census_urls.csv"), "w", newline="") as f:  # BigQuery upload (GDELT step G2)
    w = csv.writer(f); w.writerow(["outlet", "issue", "date", "url_norm"]); w.writerows(census)
summ = {"cells": len(rows_c), "cells_dropped": sum(r[8].startswith("dropped") for r in rows_c),
        "census_dedup": sum(r[5] for r in rows_c), "sampled": sum(r[6] == "sample" for r in rows_s), "log": dict(log)}
json.dump(summ, open(os.path.join(P, "data/sampling/sample_log.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
