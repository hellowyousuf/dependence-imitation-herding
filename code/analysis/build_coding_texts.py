#!/usr/bin/env python3
"""Stage 6b, step 1 — the text each coder sees (codebook C2: headline + lead; C4/C8/C10: byline, dateline, end note).
Reads data/raw/pages/peripheral_texts*.jsonl (D24, D25, D32) and the core texts: data/raw/core/core_texts_manual.jsonl
(D30, ProQuest: NYT, WaPo), data/raw/core/core_texts.jsonl (D27: Guardian API, BBC pages, WaPo Wayback; NYT API records
are metadata only under X9 and are not used as text) and data/raw/core/core_headline_only.jsonl (D31, X11: WaPo syndicated
copies, text_window = headline_only). Per story:
  headline; lead = first paragraph that is not the headline (if under 25 words, the next paragraph is added);
  credit_lines = byline metadata + last paragraph (end-note credits).
Duplicate check (plan exclusion, A32): a story whose normalized lead equals another story's lead in the same outlet is
flagged dup_of (kept in the file, excluded from coding counts). Validity: the page headline must share >= 50% of content words with the sampled title, and a lead must survive the
boilerplate filter; otherwise the story is marked invalid and listed in data/raw/pages/invalid_pages.json, which the fetch
script treats as unretrievable (plan: replaced by the next draw).
Writes data/coded/coding_texts.jsonl.
"""
import json, glob, re, csv, sys, os
P = sys.argv[1] if len(sys.argv) > 1 else "."
meta = {r["sample_id"]: r for r in csv.DictReader(open(os.path.join(P, "data/sampling/sample_ranked.csv")))}
tiers = {r["country"]: r["tier"] for r in csv.DictReader(open(os.path.join(P, "data/coded/v5_tier.csv")))}
norm = lambda s: re.sub(r"\W+", " ", (s or "").lower()).strip()
BOILER = re.compile(r"(don.t miss out|pay attention|what you need to know|join .{0,40}(channel|whatsapp)|subscribe|sign up|"
                    r"this page doesn.t seem to exist|page not found|latest news|breaking news|read more|follow us|"
                    r"advertisement|premium|coverage: live across|continue to follow our live coverage|^\w{3}, \w{3} \d+, 20\d\d)", re.I)
STOP = set("the a an of to in on for and or with at by from as is are was were be its it that this".split())
def fix(t):  # pages decoded as Latin-1 instead of UTF-8 (e.g. "Â£", "â€™")
    if t and ("Â" in t or "â€" in t or "Ã" in t):
        try: return t.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            try: return t.encode("cp1252").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError): return t
    return t
def toks(s): return {w for w in norm(s).split() if w not in STOP and len(w) > 2}
def same_story(page_head, sample_title):
    a, b = toks(page_head), toks(sample_title)
    if not a or not b: return False
    return len(a & b) / min(len(a), len(b)) >= 0.5
out, seen, leads = [], set(), {}
files = sorted(glob.glob(os.path.join(P, "data/raw/pages/peripheral_texts*.jsonl")), key=lambda f: "_refetch" not in f)
CORE = [os.path.join(P, "data/raw/core", f) for f in ("core_texts_manual.jsonl", "core_texts.jsonl", "core_headline_only.jsonl")]
files += [f for f in CORE if os.path.exists(f)]
nyt_summary = {}  # X9: the NYT API summary (dek) is dropped when ProQuest repeats it as the first line of the full text
if os.path.exists(CORE[1]):
    for l in open(CORE[1]):
        r = json.loads(l)
        if r["outlet"] == "nytimes.com" and r.get("lead"): nyt_summary[r["sample_id"]] = r["lead"][0]
def is_summary(sid, p):
    s = nyt_summary.get(sid)
    return bool(s) and len(toks(s) & toks(p)) / max(1, len(toks(s))) >= 0.8
for f in files:  # refetched records (6 paragraphs) take precedence over first-pass records (2 paragraphs); ProQuest before API/pages for core
    core = "/data/raw/core/" in f.replace(os.sep, "/")
    for l in open(f):
        r = json.loads(l)
        if r["sample_id"] in seen or r.get("status") != "ok": continue
        if core and r.get("route") == "nyt": continue  # X9: NYT API record is metadata only
        seen.add(r["sample_id"]); m = meta[r["sample_id"]]
        r = {k: (fix(v) if isinstance(v, str) else [fix(x) for x in v] if isinstance(v, list) else v) for k, v in r.items()}
        head = (r.get("headline") or m["title"]).strip()
        paras = [p for p in (r.get("lead") or []) if norm(p) and norm(p) != norm(head)
                 and len(p.split()) >= 12 and not BOILER.search(p) and not is_summary(r["sample_id"], p)]
        lead = paras[0] if paras else ""
        if lead and len(lead.split()) < 25 and len(paras) > 1: lead = lead + " " + paras[1]
        rec = {"sample_id": r["sample_id"], "outlet": m["outlet"], "country": m["country"],
               "tier": tiers.get(m["country"], "core"), "issue": m["issue"], "date": m["date"], "headline": head,
               "lead": lead.strip(), "byline": r.get("author") or "", "last_paragraph": r.get("last") or "",
               "source_file": os.path.basename(f), "wayback": bool(r.get("wayback") or r.get("route") == "wayback")}
        if core:
            rec["route"] = r.get("route"); rec["text_window"] = r.get("text_window", "headline_lead")
            if r.get("wire_rule"): rec["wire_rule"] = r["wire_rule"]
        exact = core and r.get("route") in ("guardian", "proquest", "headline_only", "pages")  # exact path / URL (BBC updates headlines), or title + date
        if not exact and not same_story(head, m["title"]): rec["invalid"] = "page headline does not match the sampled story (soft 404, home page or other page)"
        elif rec.get("text_window") == "headline_only": pass
        elif not lead: rec["needs_refetch" if not core else "invalid"] = "no lead paragraph after removing site boilerplate"
        k = (m["outlet"], norm(lead))
        if "invalid" in rec or "needs_refetch" in rec or rec.get("text_window") == "headline_only": pass
        elif k in leads: rec["dup_of"] = leads[k]
        else: leads[k] = r["sample_id"]
        out.append(rec)
# per cell, keep the lowest-ranked valid stories up to the cell target (50 or the whole cell); later valid ones are surplus
import collections
rank = lambda x: int(meta[x["sample_id"]]["rank"])
cells = collections.defaultdict(list)
for x in out:
    if not any(k in x for k in ("invalid", "needs_refetch", "dup_of")): cells[(x["outlet"], x["issue"])].append(x)
for (o, i), xs in cells.items():
    n_cell = sum(1 for m in meta.values() if m["outlet"] == o and m["issue"] == i)
    for x in sorted(xs, key=rank)[min(50, n_cell):]: x["surplus"] = "beyond the cell target (lower-ranked valid stories fill it)"
os.makedirs(os.path.join(P, "data/coded"), exist_ok=True)
with open(os.path.join(P, "data/coded/coding_texts.jsonl"), "w") as g:  # written after surplus marking (fix 2026-10-06)
    for rec in sorted(out, key=lambda x: x["sample_id"]): g.write(json.dumps(rec, ensure_ascii=False) + "\n")
per = [x for x in out if x["tier"] != "core"]
inv = [x["sample_id"] for x in per if "invalid" in x or "dup_of" in x
       or ("needs_refetch" in x and "_refetch" in x["source_file"])]  # duplicates and leadless pages also go to the next draw
ref = [x["sample_id"] for x in per if "needs_refetch" in x and "_refetch" not in x["source_file"]]
json.dump(sorted(ref), open(os.path.join(P, "data/raw/pages/refetch_ids.json"), "w"), indent=0)
json.dump(sorted(inv), open(os.path.join(P, "data/raw/pages/invalid_pages.json"), "w"), indent=0)
cc = collections.Counter((x["outlet"], x["issue"]) for x in out if x["tier"] == "core" and not any(k in x for k in ("invalid", "dup_of", "surplus")))
print("core cells:", dict(sorted(cc.items())), "| core invalid:", [x["sample_id"] for x in out if x["tier"] == "core" and "invalid" in x])
print(len(ref), "to refetch with more paragraphs;", len(out), "texts;", len(inv), "invalid pages (replaced by the next reserve on the next fetch run);", sum("dup_of" in x for x in out), "duplicate leads flagged;", sum(not x["lead"] for x in out), "without lead")
