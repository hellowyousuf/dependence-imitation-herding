#!/usr/bin/env python3
"""Stage 6a, author step T2 (X3, X4b) — headline, lead and credit lines of the sampled CORE stories.

Routes, tried in this order per outlet (author: "try API first and then other methods before I download any manually"):
  nyt       The New York Times Article Search API (free key, env NYT_API_KEY): headline, lead_paragraph, abstract, byline
  guardian  The Guardian Open Platform Content API (free key, env GUARDIAN_API_KEY): headline, byline, body paragraphs
  pages     Washington Post and BBC public pages, the author's research crawler, robots.txt for all crawlers obeyed
  wayback   Washington Post and BBC: the Wayback Machine copy nearest the story date, for pages the live site refused
Whatever is still missing after these goes to data/sampling/core_manual_list.csv for the UNM database (by hand).
Same cell rules as the peripheral sample: per outlet x issue, walk the ranked list (rank <= 50 first, then reserves)
until the target is met; transient errors are retried on the next run. Only headline, byline, the first six paragraphs
and the last paragraph are kept. Output: data/raw/core/core_texts.jsonl, data/raw/core/core_fetch_log.jsonl. Resumable.

Run:  python3 data/analysis/fetch_core_texts.py nyt | guardian | pages | wayback | manual-list
"""
import csv, json, os, re, sys, time, collections, datetime as dt, urllib.robotparser
from urllib.parse import urlparse
import requests
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
OUT = os.path.join("data", "raw", "core"); os.makedirs(OUT, exist_ok=True)
TP, LP = os.path.join(OUT, "core_texts.jsonl"), os.path.join(OUT, "core_fetch_log.jsonl")
UA = "PeripheryFollowsStudy/1.0 (academic news-content research, University of New Mexico; analysis only)"
ROUTE = {"nyt": ["nytimes.com"], "guardian": ["theguardian.com"], "pages": ["washingtonpost.com", "bbc"], "wayback": ["washingtonpost.com", "bbc"]}
done = {}
for p in (TP, LP):
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l); st = r.get("status", "ok")
            if st == "http_429" or st.startswith("error:") or st.startswith("http_5"): continue  # transient: retry
            if MODE == "wayback" and st != "ok" and r.get("route") == "pages": continue        # live failure: try Wayback
            if MODE == "wayback" and st == "http_403" and r.get("route") == "wayback" and r.get("try", 1) < 2: continue  # one slower retry
            if MODE == "nyt" and st == "not_found" and r.get("route") == "nyt" and not r.get("v2"): continue  # v1 fq lookup failed: retry by search
            done[r["sample_id"]] = st
tried = set()
if os.path.exists(LP):
    for l in open(LP):
        x = json.loads(l)
        if x.get("route") == "wayback": tried.add(x["sample_id"])
rows = [r for r in csv.DictReader(open("data/sampling/sample_ranked.csv")) if r["group"] == "core"]
cells = collections.defaultdict(list)
for r in rows: cells[(r["outlet"], r["issue"])].append(r)
def paras_from_html(html):
    ps = [re.sub(r"<[^>]+>", "", p) for p in re.findall(r"<p[^>]*>(.*?)</p>", html or "", flags=re.S)]
    return [re.sub(r"\s+", " ", p).strip() for p in ps if p.strip()]
last = collections.defaultdict(float)
def wait(host, gap):
    w = gap - (time.time() - last[host])
    if w > 0: time.sleep(w)
    last[host] = time.time()
robots = {}
def allowed(url):
    h = urlparse(url); base = f"{h.scheme}://{h.netloc}"
    if base not in robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            t = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=30); rp.parse(t.text.splitlines() if t.status_code == 200 else [])
        except Exception: rp.parse([])
        robots[base] = rp
    return robots[base].can_fetch(UA, url)
def _norm(u): return re.sub(r"^https?://(www\\.)?", "", (u or "").split("?")[0].split("#")[0]).rstrip("/").lower()
def _words(t): return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 3}
def get_nyt(r):
    # v2 (2026-10-04): the fq web_url lookup returned no hits for all 300 stories, so search the headline within
    # +/- 1 day of the story date and keep the doc whose web_url equals the sampled URL (or, failing that, whose
    # headline shares >= 80% of the sampled title's content words). One request per story.
    key = os.environ.get("NYT_API_KEY") or sys.exit("set NYT_API_KEY first")
    d0 = dt.date.fromisoformat(r["date"][:10])
    q = " ".join(r["title"].replace('"', " ").split()[:10])
    wait("nyt", 13)  # 5 requests per minute
    resp = requests.get("https://api.nytimes.com/svc/search/v2/articlesearch.json",
                        params={"q": q, "begin_date": (d0 - dt.timedelta(days=1)).strftime("%Y%m%d"),
                                "end_date": (d0 + dt.timedelta(days=1)).strftime("%Y%m%d"), "api-key": key}, timeout=40)
    if resp.status_code != 200: return {"status": f"http_{resp.status_code}", "v2": True}
    docs = (resp.json().get("response") or {}).get("docs") or []
    want, tw = _norm(r["url"]), _words(r["title"])
    hit = next((d for d in docs if _norm(d.get("web_url")) == want), None); how = "url"
    if hit is None:
        hit = next((d for d in docs if tw and len(tw & _words((d.get("headline") or {}).get("main"))) / len(tw) >= 0.8), None); how = "headline"
    if hit is None: return {"status": "not_found", "v2": True, "n_hits": len(docs)}
    lead = [x for x in (hit.get("lead_paragraph"), hit.get("abstract"), hit.get("snippet")) if x]
    lead = list(dict.fromkeys(lead))
    if not lead: return {"status": "no_text", "v2": True}
    return {"status": "ok", "v2": True, "matched_by": how, "nyt_url": hit.get("web_url"),
            "headline": (hit.get("headline") or {}).get("main"), "author": (hit.get("byline") or {}).get("original"),
            "lead": lead[:2], "last": "", "n_paragraphs": len(lead), "date_meta": hit.get("pub_date")}
def get_guardian(r):
    key = os.environ.get("GUARDIAN_API_KEY") or sys.exit("set GUARDIAN_API_KEY first")
    path = urlparse(r["url"]).path
    wait("guardian", 1.2)
    resp = requests.get("https://content.guardianapis.com" + path,
                        params={"show-fields": "headline,byline,body,trailText", "api-key": key}, timeout=40)
    if resp.status_code != 200: return {"status": f"http_{resp.status_code}"}
    f = ((resp.json().get("response") or {}).get("content") or {}).get("fields") or {}
    ps = paras_from_html(f.get("body"))
    if not ps: return {"status": "no_text"}
    return {"status": "ok", "headline": f.get("headline"), "author": f.get("byline"), "lead": ps[:6], "last": ps[-1], "n_paragraphs": len(ps)}
def get_page(r, wb=False):
    import trafilatura
    src = f"https://web.archive.org/web/{r['date'].replace('-', '')}id_/{r['url']}" if wb else r["url"]
    if not allowed(src): return {"status": "robots_disallow", "fetched_from": src}
    wait(urlparse(src).netloc, 20 if wb else 4)
    resp = requests.get(src, headers={"User-Agent": UA}, timeout=60)
    if resp.status_code == 429 and wb: time.sleep(120)  # archive.org asks us to slow down
    if resp.status_code != 200: return {"status": f"http_{resp.status_code}", "fetched_from": src, "try": 2 if wb and r["sample_id"] in tried else 1}
    ex = trafilatura.bare_extraction(resp.text, url=r["url"], with_metadata=True); ex = ex.as_dict() if hasattr(ex, "as_dict") else (ex or {})
    ps = [p.strip() for p in (ex.get("text") or "").split("\n") if p.strip()]
    if not ps: return {"status": "no_text", "fetched_from": src}
    return {"status": "ok", "headline": ex.get("title") or r["title"], "author": ex.get("author"), "lead": ps[:6], "last": ps[-1],
            "n_paragraphs": len(ps), "fetched_from": src}
if MODE == "manual-list":
    ok = collections.Counter(); have = {k for k, v in done.items() if v == "ok"}
    with open("data/sampling/core_manual_list.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["sample_id", "publication", "date", "headline", "url", "nexis_search", "save_as"])
        for (o, i), rs in sorted(cells.items()):
            got = sum(r["sample_id"] in have for r in rs); need = min(50, len(rs)) - got
            for r in sorted(rs, key=lambda r: int(r["rank"])):
                if need <= 0: break
                if r["sample_id"] in have: continue
                short = " ".join(r["title"].replace('"', "'").split()[:8])
                w.writerow([r["sample_id"], o, r["date"], r["title"], r["url"], f'hlead("{short}")', r["sample_id"].replace("|", "_") + ".txt"]); need -= 1
    print("wrote data/sampling/core_manual_list.csv"); sys.exit()
if MODE not in ROUTE: sys.exit(__doc__)
fn = {"nyt": get_nyt, "guardian": get_guardian, "pages": get_page, "wayback": lambda r: get_page(r, True)}[MODE]
tf, lf = open(TP, "a"), open(LP, "a")
for (o, issue), rs in sorted(cells.items()):
    if o not in ROUTE[MODE]: continue
    target = min(50, len(rs)); got = sum(1 for r in rs if done.get(r["sample_id"]) == "ok")
    for r in sorted(rs, key=lambda r: int(r["rank"])):
        if got >= target: break
        if r["sample_id"] in done: continue
        rec = {"sample_id": r["sample_id"], "outlet": o, "issue": issue, "rank": int(r["rank"]), "url": r["url"], "route": MODE,
               "retrieved": dt.date.today().isoformat()}
        try: rec.update(fn(r))
        except SystemExit: raise
        except Exception as e: rec["status"] = "error:" + type(e).__name__
        (tf if rec["status"] == "ok" else lf).write(json.dumps(rec, ensure_ascii=False) + "\n"); tf.flush(); lf.flush()
        done[r["sample_id"]] = rec["status"]; got += rec["status"] == "ok"
    print(f"{o:20s} {issue:8s} {got}/{target}")
print("DONE — reply 'data ready T2' in the chat.")
