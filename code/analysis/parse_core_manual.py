#!/usr/bin/env python3
"""Stage 6a, T2-manual (X9). Parses the ProQuest full-text exports in data/raw/core/manual/proquest_*/ (records separated
by a line of underscores), matches each record to the core manual list (data/sampling/core_manual_list.csv, needed +
spare) by publication, date (+/- 1 day) and title (>= 60% of the sampled headline's content words; exact URL slug or
ProQuest title equality also accepted), and writes the matched stories in the core_texts format:
  data/raw/core/core_texts_manual.jsonl   (route "proquest": headline, author, first 6 paragraphs, last paragraph)
  data/raw/core/core_manual_match.json    (per record: matched sample_id or why not; per list row: found or not)
Records that match no listed story (other search hits) are kept in the raw files only."""
import csv, glob, json, os, re, collections, datetime as dt
KEYS = ("Title:", "Subject:", "Location:", "Company / organization:", "People:", "Identifier / keyword:", "Business indexing term:",
        "Publication title:", "Credit:", "Section:", "Publication date:")
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
STOP = set("the a an of to in on for and or with at by from as is are was were be its it's that this after over into says said amid".split())
def words(t): return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower().replace("’", "'")) if w not in STOP and len(w) > 2}
def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    for block in re.split(r"\n_{20,}\n", "\n" + txt):
        lines = [l.rstrip() for l in block.split("\n")]
        if not any(l.startswith("Full text:") for l in lines): continue
        rec = {"source_file": os.path.relpath(path, "data/raw/core/manual")}
        first = next((l.strip() for l in lines if l.strip()), "")
        rec["title"] = first
        for l in lines:
            for k in ("Title", "Author", "Publication title", "Publication date", "ProQuest document ID", "Document URL", "Section", "Source type"):
                if l.startswith(k + ": ") and k.lower().replace(" ", "_") not in rec: rec[k.lower().replace(" ", "_")] = l[len(k) + 2:].strip()
        if rec.get("title_") is None and rec.get("title"): pass
        i = next(n for n, l in enumerate(lines) if l.startswith("Full text:"))
        body = [lines[i][len("Full text:"):].strip()]
        for l in lines[i + 1:]:
            if l.startswith(KEYS): break
            body.append(l.strip())
        rec["paras"] = [p for p in body if p]
        d = rec.get("publication_date", "")
        m = re.match(r"([A-Z][a-z]{2})\w* (\d{1,2}), (\d{4})", d)
        rec["date"] = dt.date(int(m.group(3)), MON[m.group(1)], int(m.group(2))).isoformat() if m else None
        yield rec
recs = [r for p in sorted(glob.glob("data/raw/core/manual/proquest_*/*.txt")) for r in parse(p)]
L = list(csv.DictReader(open("data/sampling/core_manual_list.csv")))
by_id = {r["sample_id"]: r for r in L}
def pubkey(p): return "nyt" if "york" in (p or "").lower() else "wapo" if "washington post" in (p or "").lower() else "other"
match, used, log = {}, set(), []
for k, r in enumerate(recs):
    best, score = None, 0.0
    r["title"] = re.sub(r":\s*\[[^\]]*\]\s*$", "", r["title"])          # print edition desk tag, e.g. ": [Foreign Desk]"
    rt = words(r["title"])
    pk = pubkey(r.get("publication_title"))
    if pk == "other" and not r.get("publication_title"):                  # text-only export: no metadata block
        pk = "wapo" if os.path.basename(r["source_file"]).startswith("WaPo_") else "nyt"
    for x in L:
        if pubkey(x["publication"]) != pk: continue
        gap = abs((dt.date.fromisoformat(x["date"]) - dt.date.fromisoformat(r["date"])).days) if r["date"] else None
        if gap is not None and gap > 3: continue
        tw = words(x["headline"]); s = len(tw & rt) / max(1, len(tw))
        if gap is not None and gap > 1 and s < 0.9: continue                # +/- 2-3 days only for near-identical titles
        if gap is None and s < 0.9: continue                                # no date in export: near-identical title only
        if s > score: best, score = x, s
    ok = best is not None and score >= 0.6
    log.append({"record": k, "source_file": r["source_file"], "title": r.get("title"), "publication": r.get("publication_title"), "date": r["date"],
                "proquest_id": r.get("proquest_document_id"), "matched": best["sample_id"] if ok else None, "score": round(score, 2)})
    if ok:
        sid = best["sample_id"]
        if sid in match and len(match[sid]["paras"]) >= len(r["paras"]): continue
        match[sid] = r
out = []
for sid, r in match.items():
    x = by_id[sid]; o, issue, rank = sid.split("|")
    ps = r["paras"]
    out.append({"sample_id": sid, "outlet": o, "issue": issue, "rank": int(rank), "url": x["url"], "route": "proquest",
                "retrieved": "2026-10-06", "status": "ok" if ps else "no_text", "headline": r.get("title"), "author": r.get("author"),
                "lead": ps[:6], "last": ps[-1] if ps else "", "n_paragraphs": len(ps), "proquest_id": r.get("proquest_document_id"),
                "publication_title": r.get("publication_title"), "source_type": r.get("source_type"), "source_file": r["source_file"], "role": x["role"]})
with open("data/raw/core/core_texts_manual.jsonl", "w") as f:
    for x in sorted(out, key=lambda x: x["sample_id"]): f.write(json.dumps(x, ensure_ascii=False) + "\n")
rows = [{"sample_id": x["sample_id"], "role": x["role"], "publication": x["publication"], "found": x["sample_id"] in match} for x in L]
json.dump({"records": log, "list": rows}, open("data/raw/core/core_manual_match.json", "w"), indent=1, ensure_ascii=False)
c = collections.Counter((x["publication"], x["role"], x["found"]) for x in rows)
for k in sorted(c): print(k, c[k])
print("records", len(recs), "matched", sum(1 for l in log if l["matched"]), "unmatched", sum(1 for l in log if not l["matched"]))
print("pubs", collections.Counter(pubkey(r.get("publication_title")) for r in recs), collections.Counter(r.get("publication_title") for r in recs).most_common(8))

# X11 (2026-10-06): Washington Post syndicated copies (URL with a /<uuid> path) that ProQuest does not carry are kept as
# headline-only records, in rank order, until each WaPo cell reaches 50 with the stories that have text.
UUID = re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-")
have = collections.Counter(s.split("|")[1] for s in match if s.startswith("washingtonpost"))
for l in open("data/raw/core/core_texts.jsonl"):
    x = json.loads(l)
    if x["outlet"] == "washingtonpost.com" and x["status"] == "ok": have[x["issue"]] += 1
H = []
for x in sorted(L, key=lambda x: (x["issue"], int(x["sample_id"].split("|")[2]))):
    if not x["publication"].startswith("The Washington") or x["sample_id"] in match or not UUID.search(x["url"]): continue
    if have[x["issue"]] >= 50: continue
    o, issue, rank = x["sample_id"].split("|"); have[issue] += 1
    H.append({"sample_id": x["sample_id"], "outlet": o, "issue": issue, "rank": int(rank), "url": x["url"], "route": "headline_only",
              "retrieved": "2026-10-06", "status": "ok", "headline": x["headline"], "author": None, "lead": [], "last": "",
              "n_paragraphs": 0, "text_window": "headline_only", "wire_rule": "syndication_url", "role": x["role"]})
with open("data/raw/core/core_headline_only.jsonl", "w") as f:
    for h in H: f.write(json.dumps(h, ensure_ascii=False) + "\n")
print("headline-only WaPo records:", len(H), dict(collections.Counter(h["issue"] for h in H)), "cells now", dict(have))
