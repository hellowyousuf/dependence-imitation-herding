#!/usr/bin/env python3
"""Stage 6a, author step T2-manual (X9). Builds the UNM Nexis Uni / ProQuest list for the core stories that need text by hand.
NYT: the 146 stories whose API record matched the sampled URL (+ the next reserves for the 4 headline-only matches),
because the lead must be the article's own first paragraphs. Washington Post: the 50 per cell still missing, in rank order.
Spares (next reserves) are listed for misses. Batched searches: 10 stories per query. ProQuest (primary): 3 distinctive headline words + publication date +/- 1 day.
Nexis Uni (fallback): 4 headline words; set the batch date range in the date filter.
Outputs: data/sampling/core_manual_list.csv (one row per story), data/sampling/core_manual_batches.csv (one row per search).
Downloads go to data/raw/core/manual/ (any of .docx .rtf .txt .pdf; one file per article; names do not matter)."""
import csv, json, re, collections, datetime as dt
STOP = set("that this with from have will after over into their about says said amid more than what when where which while been were they them news live latest updates update world year years".split())
R = [json.loads(l) for l in open("data/raw/core/core_texts.jsonl")]
ok = {r["sample_id"]: r for r in R}
rows = [r for r in csv.DictReader(open("data/sampling/sample_ranked.csv")) if r["outlet"] in ("nytimes.com", "washingtonpost.com")]
cells = collections.defaultdict(list)
for r in rows: cells[(r["outlet"], r["issue"])].append(r)
def words(t):
    ws = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", t) if len(w) > 3 and w.lower() not in STOP]
    ws = sorted(dict.fromkeys(ws), key=lambda w: (-(w[0].isupper()), -len(w)))[:4]
    return ws
def pd(d):
    d = dt.date.fromisoformat(d[:10]); f = lambda x: x.strftime("%Y%m%d")
    return f(d - dt.timedelta(days=1)) + "-" + f(d + dt.timedelta(days=1))
out = []
for (o, i), rs in sorted(cells.items()):
    rs = sorted(rs, key=lambda r: int(r["rank"]))
    if o == "nytimes.com":
        need = [r for r in rs if r["sample_id"] in ok and ok[r["sample_id"]].get("matched_by") == "url"]
        rest = [r for r in rs if r["sample_id"] not in ok and int(r["rank"]) > max(int(x["rank"]) for x in need)]
        fill = rest[:max(0, 50 - len(need))]; need += fill; spare = rest[len(fill):len(fill) + 5]
    else:
        have = sum(r["sample_id"] in ok for r in rs); miss = [r for r in rs if r["sample_id"] not in ok]
        need = miss[:max(0, 50 - have)]; spare = miss[len(need):len(need) + 10]
    for role, grp in (("needed", need), ("spare", spare)):
        for r in grp:
            w = words(r["title"])
            out.append({"sample_id": r["sample_id"], "role": role, "publication": "The New York Times" if o == "nytimes.com" else "The Washington Post",
                        "issue": i, "date": r["date"][:10], "headline": r["title"], "url": r["url"],
                        "nexis_search": "hlead(" + " AND ".join(w) + ")", "proquest_search": "(TI(" + " AND ".join(w[:3]) + ") AND PD(" + pd(r["date"]) + "))"})
with open("data/sampling/core_manual_list.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()) + ["found (y/n)"]); w.writeheader(); [w.writerow(x) for x in out]
B = []
for (pub, role), grp in collections.OrderedDict((k, None) for k in [(x["publication"], x["role"]) for x in out]).items():
    xs = sorted([x for x in out if x["publication"] == pub and x["role"] == role], key=lambda x: x["date"])
    for k in range(0, len(xs), 10):
        b = xs[k:k + 10]
        B.append({"batch": f'{"NYT" if "York" in pub else "WaPo"}-{role}-{k // 10 + 1:02d}', "publication": pub, "role": role,
                  "date_from": b[0]["date"], "date_to": b[-1]["date"], "n": len(b),
                  "nexis_query": " OR ".join(x["nexis_search"] for x in b), "proquest_query": 'PUB("' + pub.replace("The ", "") + '") AND (' + " OR ".join(x["proquest_search"] for x in b) + ")",
                  "sample_ids": " ".join(x["sample_id"] for x in b)})
with open("data/sampling/core_manual_batches.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(B[0].keys())); w.writeheader(); [w.writerow(x) for x in B]
c = collections.Counter((x["publication"], x["role"]) for x in out)
for k, v in sorted(c.items()): print(k, v)
print("batches", collections.Counter((b["publication"], b["role"]) for b in B))
