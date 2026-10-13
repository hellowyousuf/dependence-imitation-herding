#!/usr/bin/env python3
"""Stage 6b, X10 — rule coder for the credit and dateline variables (codebook C4 wire credit, C10 national-agency credit,
foreign_story, C8 staff foreign byline). Deterministic, no model. Reads data/coded/coding_texts.jsonl (valid stories only);
writes data/coded/rule_codes.jsonl. Needs geonamescache (pip install geonamescache) for the dateline gazetteer.

Where a credit counts (codebook C4): the byline field, the dateline (agency in brackets or after the place, e.g.
"(Reuters) -", "KYIV (AP) —", or a short agency line at the start of the lead), and the end note (agency named in the
last 200 characters of the last paragraph, unless it is the object of a verb of reporting: "told Reuters",
"according to AFP", "Reuters reported"). Mentions elsewhere in the text do not count.
Second fix after the full-sample check: photo credits ("…/REUTERS)", "Photo: AFP") do not count; "Australian Associated
Press" is AAP, not AP; added Press Trust, Sputnik, RIA Novosti, Petra, AAP; hyphen-joined credits ("Bernama-Wafa") match.
Agency names match in any case ("REUTERS" in a byline), acronyms in capitals only (fix after the full-sample check).
Rules fixed on October 6, 2026 after the rule-vs-model pilot on the 300 (3 disagreements, then 1: an author bio "AFP course"):
  * "Thomson Reuters Foundation" is not a Reuters wire credit (separate foundation news service);
  * Agence de Presse Africaine (APA) is a non-Western agency (C10);
  * the end-note window is the last 200 characters of the last paragraph.
X11: Washington Post syndicated copies (headline only) take wire_credit = 1 from their URL (wire_rule = syndication_url).
foreign_story: 1 if a dateline place lies outside the outlet's country, or the story credits a foreign wire or a foreign
agency (AP/Bloomberg count as domestic for US outlets, Reuters/PA for UK outlets); 0 if the dateline is in the outlet's
country and no foreign credit; otherwise undetermined (None) and the model coder's code is used (method = model).
staff_foreign_byline: 1 if a named byline that is not a wire/agency credit and a dateline outside the outlet's country;
0 if a wire/agency credit or a home dateline; otherwise None (model coder)."""
import json, re, sys, collections
import geonamescache
WIRE = {"Reuters": "UK", "AFP": "FR", "Agence France-Presse": "FR", "Agence France Presse": "FR", "AP": "US", "Associated Press": "US"}
NAT = {"BSS": "BD", "Bangladesh Sangbad Sangstha": "BD", "UNB": "BD", "United News of Bangladesh": "BD", "PTI": "IN",
       "Press Trust of India": "IN", "ANI": "IN", "IANS": "IN", "Bernama": "MY", "NAN": "NG", "News Agency of Nigeria": "NG",
       "KNA": "KE", "Kenya News Agency": "KE", "SAnews": "ZA", "SAPA": "ZA", "ANA": "ZA", "African News Agency": "ZA",
       "APA": "SN", "Agence de Presse Africaine": "SN", "Xinhua": "CN", "Anadolu": "TR", "TASS": "RU", "WAFA": "PS",
       "IRNA": "IR", "Kyodo": "JP", "Yonhap": "KR", "dpa": "DE", "Bloomberg": "US", "PA Media": "UK", "Press Association": "UK",
       "Press Trust": "IN", "Sputnik": "RU", "RIA Novosti": "RU", "Petra": "JO", "AAP": "AU", "Australian Associated Press": "AU"}
WESTERN_NOT_C10 = {"Bloomberg", "PA Media", "Press Association", "dpa", "AAP", "Australian Associated Press"}  # foreign-source credits, but not C10 agencies
HOME = {"Bangladesh": "BD", "India": "IN", "Malaysia": "MY", "Nigeria": "NG", "Kenya": "KE", "South Africa": "ZA",
        "United States": "US", "United Kingdom": "UK"}
CORE_HOME = {"nytimes.com": "US", "washingtonpost.com": "US", "theguardian.com": "UK", "bbc": "UK"}
def rx(names):  # acronyms (all caps, e.g. AP, AFP, PTI) match in capitals only; names (Reuters, Xinhua) in any case
    acr = [n for n in names if n.isupper()]; nam = [n for n in names if not n.isupper()]
    alt = lambda xs: "|".join(sorted(map(re.escape, xs), key=len, reverse=True))
    return re.compile(r"(?<!\w)(" + alt(acr) + r"|(?i:" + alt(nam) + r"))(?!\w)")  # hyphen joins allowed: "Bernama-Wafa"
def canon(name, table):
    return next((k for k in table if k.lower() == name.lower()), name)
RW, RN = rx(WIRE), rx(NAT)
NOT_CREDIT = re.compile(r"(told|tells|to|according to|said to|interview with|speaking to)\s+(the\s+)?$", re.I)
NOT_CREDIT_AFTER = re.compile(r"^\s*(reported|reports|said|says|news agency reported|cited|quoted|that|course|training|fellowship|programme|program)", re.I)
PHOTO = re.compile(r"(photograph|photo|image|picture)s?\s*(by|:|credit)?[^.]{0,30}$", re.I)
TRF = re.compile(r"Thomson Reuters Foundation", re.I)
gc = geonamescache.GeonamesCache(min_city_population=15000)
CC = {c["iso"]: c["name"] for c in gc.get_countries().values()}
COUNTRY_BY_NAME = {v.lower(): k for k, v in CC.items()}
COUNTRY_BY_NAME.update({"u.s.": "US", "us": "US", "usa": "US", "uk": "GB", "britain": "GB", "england": "GB", "scotland": "GB",
                        "gaza": "PS", "west bank": "PS", "gaza strip": "PS", "the hague": "NL", "russia": "RU", "iran": "IR",
                        "syria": "SY", "south korea": "KR", "north korea": "KP", "vietnam": "VN", "taiwan": "TW", "egypt": "EG"})
CITY = collections.defaultdict(set)
for c in gc.get_cities().values():
    CITY[c["name"].lower()].add(c["countrycode"])
    for a in (c.get("alternatenames") or [])[:0]: pass
EXTRA = {"kyiv": "UA", "kiev": "UA", "washington": "US", "new delhi": "IN", "delhi": "IN", "gurgaon": "IN", "mumbai": "IN",
         "sharm el-sheikh": "EG", "sharm el sheikh": "EG", "dubai": "AE", "jerusalem": "IL", "tel aviv": "IL", "united nations": None,
         "kuching": "MY", "kota samarahan": "MY", "sibu": "MY", "miri": "MY", "kuala lumpur": "MY", "putrajaya": "MY",
         "abuja": "NG", "lagos": "NG", "nairobi": "KE", "johannesburg": "ZA", "cape town": "ZA", "pretoria": "ZA", "dhaka": "BD",
         "bali": "ID", "moscow": "RU", "beijing": "CN", "london": "GB", "brussels": "BE", "geneva": "CH", "cairo": "EG", "beirut": "LB",
         "doha": "QA", "rafah": "PS", "khan younis": "PS", "gaza city": "PS", "kharkiv": "UA", "odesa": "UA", "odessa": "UA"}
GB = {"UK": "GB"}
DATELINE = re.compile(r"^\s*([A-Z][A-Z\.\'’\- ]{2,40}|[A-Z][A-Za-z\.\'’\- ]{2,30},\s*[A-Z][A-Za-z\.\- ]{2,30})\s*(\([^)]{1,40}\))?\s*(:|—|–|--|-)\s")
def place_country(p):
    p = p.strip().strip(".").lower()
    if "," in p:
        city, ctry = [x.strip() for x in p.split(",", 1)]
        if ctry in COUNTRY_BY_NAME: return COUNTRY_BY_NAME[ctry]
        p = city
    if p in EXTRA: return EXTRA[p]
    if p in COUNTRY_BY_NAME: return COUNTRY_BY_NAME[p]
    cs = CITY.get(p)
    return next(iter(cs)) if cs and len(cs) == 1 else None
def credits(rgx, text, endnote=False):
    found = set()
    for m in rgx.finditer(text or ""):
        name = canon(m.group(1), WIRE if rgx is RW else NAT)
        if endnote and (NOT_CREDIT.search(text[max(0, m.start() - 25):m.start()]) or NOT_CREDIT_AFTER.search(text[m.end():m.end() + 25])): continue
        if name == "Reuters" and TRF.search(text[max(0, m.start() - 10):m.end() + 15]): continue
        if text[max(0, m.start() - 1):m.start()] == "/" or PHOTO.search(text[max(0, m.start() - 40):m.start()]): continue  # photo credit
        if name == "Associated Press" and re.search(r"Australian\s+$", text[max(0, m.start() - 12):m.start()]): continue  # AAP, not AP
        if name == "ANA" and not endnote and False: pass
        found.add(name)
    return found
def code(x):
    home = HOME.get(x["country"]) or CORE_HOME.get(x["outlet"]); home = GB.get(home, home)
    lead, last, byl = x.get("lead") or "", x.get("last_paragraph") or "", x.get("byline") or ""
    dm = DATELINE.match(lead)
    zones = {"byline": byl, "dateline": (dm.group(0) if dm else ""), "endnote": last[-200:]}
    w, n = set(), set()
    for z, t in zones.items():
        w |= credits(RW, t, endnote=(z == "endnote")); n |= credits(RN, t, endnote=(z == "endnote"))
    n_c10 = {a for a in n if a not in WESTERN_NOT_C10}
    rec = {"sample_id": x["sample_id"], "wire_credit": int(bool(w)), "national_agency_credit": int(bool(n_c10)),
           "wire_names": sorted(w), "agency_names": sorted(n), "wire_rule": "credit_line" if w else "none"}
    if x.get("wire_rule") == "syndication_url": rec.update(wire_credit=1, wire_rule="syndication_url")
    dl_country = place_country(dm.group(1)) if dm else None
    rec["dateline"] = dm.group(1).strip() if dm else None; rec["dateline_country"] = dl_country
    def foreign_src(name, table):
        c = table.get(name); c = GB.get(c, c)
        return c is not None and c != home
    foreign_credit = any(foreign_src(a, WIRE) for a in w) or any(foreign_src(a, NAT) for a in n)
    if dl_country and dl_country != home: rec["foreign_story"], rec["foreign_method"] = 1, "dateline"
    elif foreign_credit: rec["foreign_story"], rec["foreign_method"] = 1, "credit"
    elif dl_country == home: rec["foreign_story"], rec["foreign_method"] = 0, "dateline"
    else: rec["foreign_story"], rec["foreign_method"] = None, "model"
    named = bool(byl.strip()) and not (w or n) and not re.search(r"agenc|wire|desk|staff|correspondent$|reporter$|online|news service", byl, re.I)
    if w or n_c10: rec["staff_foreign_byline"], rec["staff_method"] = 0, "credit"
    elif dl_country == home: rec["staff_foreign_byline"], rec["staff_method"] = 0, "dateline"
    elif dl_country and dl_country != home and named: rec["staff_foreign_byline"], rec["staff_method"] = 1, "dateline+byline"
    else: rec["staff_foreign_byline"], rec["staff_method"] = None, "model"
    return rec
if __name__ == "__main__":
    P = sys.argv[1] if len(sys.argv) > 1 else "."
    X = [json.loads(l) for l in open(P + "/data/coded/coding_texts.jsonl")]
    X = [x for x in X if not any(k in x for k in ("invalid", "dup_of", "surplus", "needs_refetch"))]
    out = [code(x) for x in X]
    with open(P + "/data/coded/rule_codes.jsonl", "w") as f:
        for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(out), "stories;", "wire", sum(r["wire_credit"] for r in out), "agency", sum(r["national_agency_credit"] for r in out),
          "| foreign by", dict(collections.Counter(r["foreign_method"] for r in out)), "| staff by", dict(collections.Counter(r["staff_method"] for r in out)))
