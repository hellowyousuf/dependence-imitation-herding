#!/usr/bin/env python3
"""P5 step 0 — build the simulation feed files the author's Colab proposal pass reads (plan P5 step 2; A19, A26).

Writes data/analysis/sim/
  feed_core.jsonl   one line per core issue story (The New York Times, The Washington Post, The Guardian, BBC News) from the
                    Media Cloud census D5–D7: {id, date, kind:"core", issue, text}; the outlet is NOT recorded (A26)
  feed_wire.jsonl   the same for AP, Reuters and AFP stories in D5–D7: kind "wire" (agency not recorded)
  feed_events.jsonl GDELT event records rendered as one line each — REQUIRES data/raw/gdelt/g6a_event_attributes.csv
                    (complete; the partial file in data/raw/gdelt is not used) — kind "event"
  outlets.json      the 18 peripheral agents: code P01–P18, country, audience line, n_i (mean daily issue stories in the
                    fitting half, from the census), W_i (V4), C_i (V9); no outlet name
  contamination_sample.json  100 coded stories (outlet, date, issue, headline) drawn with a fixed seed for the recall check
  pilot.json        the one-month pilot window
Titles are stripped of outlet and agency names and of site suffixes ("| Reuters", "- The New York Times", "- BBC News").
Usage: python3 p5_build_feeds.py [--core-cap N]   (default: no cap; the pilot fixes the cap, A26)"""
import os, sys, json, re, random, collections, hashlib, argparse
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf

ap = argparse.ArgumentParser(); ap.add_argument("--core-cap", type=int, default=0); a = ap.parse_args()
OUT = os.path.join(pf.P, "data/analysis/sim"); os.makedirs(OUT, exist_ok=True)
CORE_DOM = {"nytimes.com", "washingtonpost.com", "theguardian.com", "bbc.com"}; WIRE_DOM = {"apnews.com", "reuters.com", "afp.com"}
STRIP = re.compile(r"\s*[|\-–—:]\s*(The New York Times|New York Times|NYT|The Washington Post|Washington Post|The Guardian|Guardian|BBC News|BBC|Reuters|AP News|Associated Press|AP|AFP)\s*$", re.I)
NAMES = re.compile(r"\b(Reuters|Associated Press|AP News|AFP|Agence France-Presse|BBC|The Guardian|The New York Times|The Washington Post|Washington Post|New York Times)\b", re.I)
def clean(t):
    t = STRIP.sub("", (t or "").strip()); t = NAMES.sub("a news organization", t)
    return re.sub(r"\s+", " ", t).strip()
def nurl(u):
    from urllib.parse import urlparse
    p = urlparse(u or ""); h = p.netloc.lower(); h = h[4:] if h.startswith("www.") else h
    return h + p.path.rstrip("/")
seen = set(); core, wire = [], []
for iss in pf.ISSUES:
    for l in open(os.path.join(pf.P, f"data/raw/mediacloud/r1_stories_{iss}.jsonl")):
        r = json.loads(l); dom = r["domain"]
        if dom not in CORE_DOM | WIRE_DOM: continue
        d = (r.get("publish_date") or "")[:10]
        if not (pf.PERIOD[0] <= d <= pf.PERIOD[1]): continue
        key = (dom, nurl(r["url"]))
        if key in seen: continue
        seen.add(key)
        text = clean(r.get("title"))
        if len(text) < 15: continue
        (core if dom in CORE_DOM else wire).append({"date": d, "kind": "core" if dom in CORE_DOM else "wire", "issue": iss, "text": text, "_u": key[1]})
rng = random.Random(pf.SEED)
def finish(items, prefix, cap=0):
    items.sort(key=lambda x: (x["date"], x["issue"], x["_u"]))
    if cap:
        byday = collections.defaultdict(list)
        for x in items: byday[x["date"]].append(x)
        items = []
        for d in sorted(byday):
            xs = byday[d]
            if len(xs) > cap: xs = rng.sample(xs, cap); xs.sort(key=lambda x: (x["issue"], x["_u"]))
            items.extend(xs)
    for i, x in enumerate(items):
        x["id"] = f"{prefix}-{x['date']}-{hashlib.sha1(x['_u'].encode()).hexdigest()[:8]}"; x.pop("_u")
    return items
core = finish(core, "c", a.core_cap); wire = finish(wire, "w")
with open(os.path.join(OUT, "feed_core.jsonl"), "w") as f:
    for x in core: f.write(json.dumps(x, ensure_ascii=False) + "\n")
with open(os.path.join(OUT, "feed_wire.jsonl"), "w") as f:
    for x in wire: f.write(json.dumps(x, ensure_ascii=False) + "\n")
# events (G6a complete) — rendered when present
g6a = os.path.join(pf.P, "data/raw/gdelt/g6a_event_attributes.csv"); n_ev = 0
CAMEO = {"01": "made a public statement", "02": "appealed", "03": "expressed intent to cooperate", "04": "consulted", "05": "engaged in diplomatic cooperation",
         "06": "engaged in material cooperation", "07": "provided aid", "08": "yielded", "09": "investigated", "10": "demanded", "11": "disapproved",
         "12": "rejected", "13": "threatened", "14": "protested", "15": "exhibited force posture", "16": "reduced relations", "17": "coerced",
         "18": "assaulted", "19": "fought", "20": "used unconventional mass violence"}
EVENTS_PER_DAY = 200   # the file keeps the 200 most-mentioned events per day; the notebook shows the top FEED_CAP['event'] of them (A39)
def event_issue(r):
    """A31 rules: Ukraine = RUS–UKR actor pair or action in Ukraine (UP); Gaza = ISR–PSE pair or action in the Gaza Strip (GZ);
    COP = action at Sharm el-Sheikh or Dubai. Else ''."""
    a1, a2, geo, name = r.Actor1CountryCode, r.Actor2CountryCode, r.ActionGeo_CountryCode, (r.ActionGeo_FullName or "")
    if {a1, a2} == {"RUS", "UKR"} or geo == "UP": return "ukraine"
    if {a1, a2} == {"ISR", "PSE"} or geo == "GZ" or "Gaza" in name: return "gaza"
    if "Sharm" in name or "Dubai" in name: return "cop"
    return ""
if os.path.isfile(g6a):
    ev = pd.read_csv(g6a, dtype=str).fillna("")
    ids = set(pd.read_csv(os.path.join(pf.P, "data/raw/gdelt/g5_story_events.csv"), usecols=["GLOBALEVENTID"]).GLOBALEVENTID.astype(str))
    ev = ev[ev.GLOBALEVENTID.isin(ids)].copy()
    ev["mentions"] = pd.to_numeric(ev.NumMentions, errors="coerce").fillna(0).astype(int)
    ev["date"] = ev.SQLDATE.str[:4] + "-" + ev.SQLDATE.str[4:6] + "-" + ev.SQLDATE.str[6:8]
    ev = ev.sort_values(["date", "mentions", "GLOBALEVENTID"], ascending=[True, False, True])
    ev["rank"] = ev.groupby("date").cumcount() + 1
    ev = ev[ev["rank"] <= EVENTS_PER_DAY]
    with open(os.path.join(OUT, "feed_events.jsonl"), "w") as f:
        for r in ev.itertuples(index=False):
            txt = f"{r.Actor1CountryCode or 'an actor'} {CAMEO.get(r.EventRootCode, 'acted')} {('toward ' + r.Actor2CountryCode) if r.Actor2CountryCode else ''} in {r.ActionGeo_FullName or 'an unstated place'} ({r.mentions} mentions)"
            f.write(json.dumps({"id": f"e-{r.GLOBALEVENTID}", "date": r.date, "kind": "event", "issue": event_issue(r), "rank": int(r.rank), "text": re.sub(r"\s+", " ", txt)}, ensure_ascii=False) + "\n"); n_ev += 1
else:
    print("WARNING: data/raw/gdelt/g6a_event_attributes.csv not found — feed_events.jsonl NOT written (prompt B: register the complete G6a export)")
# outlets (personas without names) and the dependence-rule inputs
cells = pd.read_csv(os.path.join(pf.P, "data/coded/following_cells.csv")); cen = pd.read_csv(os.path.join(pf.P, "data/sampling/census_urls.csv"))
AUD = {"Bangladesh": "a national English-language daily read by Bangladesh's urban professionals and diaspora", "Kenya": "a national English-language outlet read across Kenya",
       "South Africa": "a national English-language outlet read across South Africa", "Nigeria": "a national English-language outlet read across Nigeria",
       "India": "a national English-language outlet read across India", "Malaysia": "a national English-language outlet read across Malaysia"}
outlets = []; codes_map = {}
for k, o in enumerate(sorted(o for o in pf.OUTLETS if pf.OUTLETS[o][0] != "core"), 1):
    country = pf.OUTLETS[o][0]; code = f"P{k:02d}"; codes_map[code] = o
    n_i = {}
    for iss in pf.ISSUES:
        s, m, e = pf.halves()[iss]; c = cen[(cen.outlet == o) & (cen.issue == iss) & (cen.date >= s) & (cen.date < m)]
        days = (pd.Timestamp(m) - pd.Timestamp(s)).days
        n_i[iss] = round(len(c) / days, 4)
    if o in ("thedailystar.net", "bdnews24.com", "newagebd.net"):
        g3 = pd.read_csv(os.path.join(pf.P, "data/raw/gdelt/g3_bangladesh_census.csv")); g3 = g3[(g3.domain == o) & (g3.host == pf.OUTLETS[o][2])]
        for iss in pf.ISSUES:
            s, m, e = pf.halves()[iss]; c = g3[(g3[iss] == True) & (g3.day >= s) & (g3.day < m)]
            n_i[iss] = round(len(c) / (pd.Timestamp(m) - pd.Timestamp(s)).days, 4)
    oc = cells[(cells.outlet == o) & cells.cell_kept]
    outlets.append({"code": code, "country": country, "audience": AUD[country], "n_i_daily_fitting_half": n_i,
                    "W_i": round(float(oc.V4.mean()), 4) if len(oc) else None, "C_i": round(float(oc.V9.mean()), 4) if len(oc) else None,
                    "cells_kept": [i for i in oc.issue]})
json.dump(outlets, open(os.path.join(OUT, "outlets.json"), "w"), indent=1)
json.dump(codes_map, open(os.path.join(OUT, "outlet_codes_PRIVATE.json"), "w"), indent=1)   # stays out of the Colab upload
# contamination sample: 100 coded peripheral stories
codes = pf.codes(); texts = {r["sample_id"]: r for r in map(json.loads, open(os.path.join(pf.P, "data/coded/coding_texts.jsonl")))}
per = codes[codes.tier != "core"].sample(n=100, random_state=pf.SEED)
contam = [{"sample_id": i, "outlet": pf.OUTLET_NAMES[o], "date": d, "issue": pf.ISSUE_NAMES[iss], "headline": texts[i]["headline"]} for i, o, d, iss in zip(per.sample_id, per.outlet, per.date, per.issue) if i in texts]
json.dump(contam, open(os.path.join(OUT, "contamination_sample.json"), "w"), indent=1, ensure_ascii=False)
json.dump({"pilot_start": "2022-03-01", "pilot_end": "2022-03-31", "note": "one-month pilot (A26): fixes the feed cap, prompt length and throughput before the full pass"}, open(os.path.join(OUT, "pilot.json"), "w"), indent=1)
print(f"feed_core {len(core):,} · feed_wire {len(wire):,} · feed_events {n_ev:,} · outlets {len(outlets)} · contamination sample {len(contam)}")
