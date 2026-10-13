#!/usr/bin/env python3
"""Stage 6a, author step T1 (X4) — headline, lead and credit lines of the sampled PERIPHERAL stories from public pages.

Runs on the author's computer. For each outlet x issue cell it walks the ranked list (data/sampling/sample_ranked.csv)
until 50 stories (or the whole cell) are retrieved: an unretrievable page is logged and replaced by the next reserve
(plan: sampling.exclusion). Rules: robots.txt is read for every host and obeyed for this crawler's name (and so for '*');
one request every 4 s per host; nothing behind a login; no paywall bypass. Only what coding needs is kept: headline,
byline/author metadata, the first six paragraphs (lead + dateline; sites put headers before the lead), the last paragraph (end-note credits) and the
number of paragraphs. Full text is not stored and nothing is redistributed.
X4a: the author runs it with --only bdnews24.com,timeslive.co.za,thehindu.com; the build runs the other 15 with --agent claude.
Run:
  source ~/.venvs/mediacloud/bin/activate && pip install trafilatura==2.0.0
  cd ".../periphery_follows_v5" && python3 data/analysis/fetch_public_pages.py
Resumable. Output: data/raw/pages/peripheral_texts.jsonl, data/raw/pages/fetch_log.jsonl
"""
import csv, json, os, time, collections, datetime as dt, urllib.robotparser
from urllib.parse import urlparse
import argparse, requests, trafilatura
ap = argparse.ArgumentParser()
ap.add_argument("--only", default="", help="comma-separated outlets to fetch (default: all peripheral)")
ap.add_argument("--exclude", default="", help="comma-separated outlets to skip")
ap.add_argument("--wayback", default="", help="X8: comma-separated outlets read from the Wayback Machine copy nearest the story date")
ap.add_argument("--ids", default="", help="6b: JSON list of sample_ids to fetch again (all kept paragraphs); writes *_refetch files")
ap.add_argument("--agent", default="author", choices=["author", "claude"], help="X4a: who runs this")
ARGS = ap.parse_args()
ONLY = {x for x in ARGS.only.split(",") if x}; WB = {x for x in ARGS.wayback.split(",") if x}; EXCL = {x for x in ARGS.exclude.split(",") if x}
UA = ("Claude-User/1.0 (fetch on behalf of a university researcher; analysis only)" if ARGS.agent == "claude" else
      "PeripheryFollowsStudy/1.0 (academic news-content research, University of New Mexico; analysis only)")
OUT = os.path.join("data", "raw", "pages"); os.makedirs(OUT, exist_ok=True)
SUF = ("_claude" if ARGS.agent == "claude" else "") + ("_refetch" if ARGS.ids else "")
IDS = set(json.load(open(ARGS.ids))) if ARGS.ids else set()
TP, LP = os.path.join(OUT, f"peripheral_texts{SUF}.jsonl"), os.path.join(OUT, f"fetch_log{SUF}.jsonl")
done = {}
import glob
SEEN_FILES = [TP] if IDS else sorted(set(glob.glob(os.path.join(OUT, "peripheral_texts*.jsonl")) + glob.glob(os.path.join(OUT, "fetch_log*.jsonl"))) - {os.path.join(OUT, "fetch_log_refetch.jsonl")})
for p in SEEN_FILES:  # every earlier run counts (author's, build's, refetch), so nothing is fetched twice
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            st0 = r.get("status", "ok")
            if st0 == "http_429" or st0.startswith("error:") or st0.startswith("http_5"):
                continue  # transient (lost connection, rate limit, server error): try again, never burns a reserve
            if r["outlet"] in WB and st0 != "ok" and not r.get("wayback"):
                continue  # X8: retry live-site failures via Wayback
            done[r["sample_id"]] = r.get("status", "ok")
INVALID = set(json.load(open(os.path.join(OUT, "invalid_pages.json")))) if os.path.exists(os.path.join(OUT, "invalid_pages.json")) else set()
for sid in (INVALID if not IDS else []): done[sid] = "invalid_page"  # 6b validity check: counts as unretrievable, next reserve is fetched
rows = [r for r in csv.DictReader(open("data/sampling/sample_ranked.csv")) if r["group"] != "core"
        and (not ONLY or r["outlet"] in ONLY) and r["outlet"] not in EXCL and (not IDS or r["sample_id"] in IDS)]
cells = collections.defaultdict(list)
for r in rows: cells[(r["outlet"], r["issue"])].append(r)
robots, last = {}, collections.defaultdict(float)
def allowed(url):
    h = urlparse(url); base = f"{h.scheme}://{h.netloc}"
    if base not in robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            t = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=30)
            rp.parse(t.text.splitlines() if t.status_code == 200 else [])
        except Exception: rp.parse([])
        robots[base] = rp
    return robots[base].can_fetch(UA, url)
def fetch(url):
    host = urlparse(url).netloc; gap = 10 if host == "web.archive.org" else 4; wait = gap - (time.time() - last[host])
    if wait > 0: time.sleep(wait)
    last[host] = time.time()
    return requests.get(url, headers={"User-Agent": UA}, timeout=40)
tf, lf = open(TP, "a"), open(LP, "a")
for (o, issue), rs in sorted(cells.items()):
    target = len(rs) if IDS else min(50, len(rs)); got = sum(1 for r in rs if done.get(r["sample_id"]) == "ok")
    for r in sorted(rs, key=lambda r: int(r["rank"])):
        if got >= target: break
        sid = r["sample_id"]
        if sid in done: continue
        src = r["url"]
        if o in WB: src = f"https://web.archive.org/web/{r['date'].replace('-', '')}id_/{r['url']}"
        rec = {"sample_id": sid, "outlet": o, "issue": issue, "rank": int(r["rank"]), "url": r["url"], "fetched_from": src, "wayback": o in WB,
               "retrieved": dt.date.today().isoformat()}
        try:
            if not allowed(src): rec["status"] = "robots_disallow"
            else:
                resp = fetch(src)
                if resp.status_code != 200: rec["status"] = f"http_{resp.status_code}"
                else:
                    ex = trafilatura.bare_extraction(resp.text, url=r["url"], with_metadata=True, include_comments=False)
                    ex = ex.as_dict() if hasattr(ex, "as_dict") else (ex or {})
                    paras = [p.strip() for p in (ex.get("text") or "").split("\n") if p.strip()]
                    if len(paras) < 1: rec["status"] = "no_text"
                    else:
                        rec.update({"status": "ok", "headline": ex.get("title") or r["title"], "author": ex.get("author"),
                                    "date_meta": ex.get("date"), "lead": paras[:6], "last": paras[-1], "n_paragraphs": len(paras)})
        except Exception as e:
            rec["status"] = "error:" + type(e).__name__
        (tf if rec["status"] == "ok" else lf).write(json.dumps(rec, ensure_ascii=False) + "\n"); tf.flush(); lf.flush()
        done[sid] = rec["status"]; got += rec["status"] == "ok"
    print(f"{o:26s} {issue:8s} {got}/{target}")
print("DONE — reply 'data ready' in the chat.")
