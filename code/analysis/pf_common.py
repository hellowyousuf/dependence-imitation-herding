#!/usr/bin/env python3
"""Shared inputs and measures for the stage-6c scripts (plan revision 5; deviations X1, X5, X6, X7, X11, X12, X13).

Everything a procedure script needs: the outlet frame, tiers (X1), weeks, the weekly issue-share series (Media Cloud for
15 outlets and the core; GDELT GKG host rows for the three Bangladesh outlets, X5; Times of India denominator scaled by
the GDELT host share, X13), the core series as the weekly mean of the core outlets present (X7), the event-adjusted
salience correlation V1 (A25, A31), the peak cross-correlation lag V3b, the event-level first-story lag V3a (C3), the
bias-corrected framing similarity V2 (A25), the credit shares V4 / V9 / V11, the own-country share V10 (C9) and the
run bookkeeping (results/<run_id>/, data/runs.jsonl). Seeds are fixed (SEED). No interpretation lives here.
"""
import csv, hashlib, json, os, sys, datetime as dt, collections, platform, subprocess
import numpy as np, pandas as pd

P = os.environ.get("PF_PROJECT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SEED = 20261006
PLAN_REVISION = 5
PERIOD = ("2022-02-24", "2024-12-31")
ISSUES = ["ukraine", "gaza", "cop"]
STAKE = {"ukraine": 0, "gaza": 1, "cop": 2}            # C6, fixed a priori
CORE = ["nytimes.com", "washingtonpost.com", "theguardian.com", "bbc"]
WAPO_END = "2024-03-04"                                  # X7: Media Cloud holds no Post stories after this date
MIN_WEEK_STORIES = 5                                     # C1: weeks with fewer than 5 outlet stories are dropped
MIN_WEEKS = 8                                            # a correlation needs at least 8 usable weeks (build assumption A35)
CENSOR_DAYS = 14                                         # C3; applied symmetrically (an outlet ahead of the core by more than 14 days is censored at -14; build assumption A38)
MIN_EVENTS = 10                                          # V3a needs at least 10 matched events in the cell (build assumption A37)
MAX_XCORR_LAG = 4                                        # V3b: lags -4..+4 weeks
PERM_DRAWS = 1000                                        # A25: pooled redraws for the framing bias correction
FRAMES = ["episodic", "thematic", "conflict", "human_interest", "responsibility", "economic", "other"]

# outlet: (country, Media Cloud domain | None, GDELT host | None)
OUTLETS = {
 "thedailystar.net": ("Bangladesh", None, "thedailystar.net"), "bdnews24.com": ("Bangladesh", None, "bdnews24.com"),
 "newagebd.net": ("Bangladesh", None, "newagebd.net"),
 "the-star.co.ke": ("Kenya", "the-star.co.ke", None), "nation.africa": ("Kenya", "nation.africa", None), "tuko.co.ke": ("Kenya", "tuko.co.ke", None),
 "iol.co.za": ("South Africa", "iol.co.za", None), "citizen.co.za": ("South Africa", "citizen.co.za", None), "timeslive.co.za": ("South Africa", "timeslive.co.za", None),
 "punchng.com": ("Nigeria", "punchng.com", None), "dailypost.ng": ("Nigeria", "dailypost.ng", None), "tribuneonlineng.com": ("Nigeria", "tribuneonlineng.com", None),
 "timesofindia": ("India", "indiatimes.com", None), "hindustantimes.com": ("India", "hindustantimes.com", None), "thehindu.com": ("India", "thehindu.com", None),
 "malaymail.com": ("Malaysia", "malaymail.com", None), "newsarawaktribune.com.my": ("Malaysia", "newsarawaktribune.com.my", None), "malaysiakini.com": ("Malaysia", "malaysiakini.com", None),
 "nytimes.com": ("core", "nytimes.com", None), "washingtonpost.com": ("core", "washingtonpost.com", None),
 "theguardian.com": ("core", "theguardian.com", None), "bbc": ("core", "bbc.com", None),
}
OUTLET_NAMES = {"thedailystar.net": "The Daily Star", "bdnews24.com": "bdnews24.com", "newagebd.net": "New Age",
 "the-star.co.ke": "The Star (Kenya)", "nation.africa": "Daily Nation", "tuko.co.ke": "Tuko", "iol.co.za": "IOL",
 "citizen.co.za": "The Citizen", "timeslive.co.za": "TimesLIVE", "punchng.com": "Punch", "dailypost.ng": "Daily Post",
 "tribuneonlineng.com": "Nigerian Tribune", "timesofindia": "Times of India", "hindustantimes.com": "Hindustan Times",
 "thehindu.com": "The Hindu", "malaymail.com": "Malay Mail", "newsarawaktribune.com.my": "New Sarawak Tribune",
 "malaysiakini.com": "Malaysiakini", "nytimes.com": "The New York Times", "washingtonpost.com": "The Washington Post",
 "theguardian.com": "The Guardian", "bbc": "BBC News"}
ISSUE_NAMES = {"ukraine": "Ukraine", "gaza": "Gaza", "cop": "COP27/COP28"}
COUNTRY_TERMS = {  # C9: country name, demonym or capital in the title
 "Bangladesh": r"\b(bangladesh|bangladeshi|bangladeshis|dhaka)\b", "Kenya": r"\b(kenya|kenyan|kenyans|nairobi)\b",
 "South Africa": r"\b(south africa|south african|south africans|pretoria|cape town|johannesburg)\b",
 "Nigeria": r"\b(nigeria|nigerian|nigerians|abuja)\b", "India": r"\b(india|indian|indians|new delhi|delhi)\b",
 "Malaysia": r"\b(malaysia|malaysian|malaysians|kuala lumpur|putrajaya)\b"}


def tiers():
    """X1: tier per country from data/coded/v5_tier.csv (index scores on World Bank 2022, D1)."""
    t = pd.read_csv(os.path.join(P, "data/coded/v5_tier.csv"))
    return dict(zip(t.country, t.tier)), dict(zip(t.country, t.gunaratne_index))


def tier_of(outlet):
    c = OUTLETS[outlet][0]
    return "core" if c == "core" else tiers()[0][c]


def weeks():
    w0 = dt.date(2022, 2, 24); out = []
    while w0 <= dt.date(2024, 12, 31):
        out.append(w0.isoformat()); w0 += dt.timedelta(days=7)
    return out


def week_of(d):
    """Thursday-start week containing ISO date d (GDELT WEEK(THURSDAY) convention, D21/D23)."""
    d0 = dt.date.fromisoformat(d[:10]); base = dt.date(2022, 2, 24)
    k = (d0 - base).days // 7
    return (base + dt.timedelta(days=7 * k)).isoformat()


def halves():
    """A23 (A34): validation halves. COP: first = the COP27 period (weeks up to June 8, 2023, the midpoint between the
    end of COP27 and the start of COP28), second = the COP28 period; Ukraine: date midpoint of Feb 24, 2022–Dec 31, 2024
    (Aug 13, 2023); Gaza: date midpoint of the war's period Oct 7, 2023–Dec 31, 2024 (May 19, 2024)."""
    return {"cop": ("2022-02-24", "2023-06-08", "2024-12-31"), "ukraine": ("2022-02-24", "2023-08-13", "2024-12-31"),
            "gaza": ("2023-10-07", "2024-05-19", "2024-12-31")}


def half_of(issue, d):
    s, m, e = halves()[issue]
    if d < s or d > e: return None
    return "H1" if d < m else "H2"


# ---------------------------------------------------------------- weekly series -----------------------------------
_series_cache = {}

def weekly_series():
    """→ DataFrame [outlet, issue, week, issue_n, all_n, share]; weeks with all_n < MIN_WEEK_STORIES removed.
    Media Cloud outlets: issue_n from the deduplicated census (data/sampling/census_urls.csv), all_n = the source's daily
    English story count (D4, query 'all') summed by week; Times of India all_n × toi_share (X13, D21).
    Bangladesh outlets (X5): GDELT GKG host rows (D21): articles and <issue>_title."""
    if "s" in _series_cache: return _series_cache["s"]
    W = set(weeks())
    cen = pd.read_csv(os.path.join(P, "data/sampling/census_urls.csv"))
    cen["week"] = cen["date"].map(week_of)
    num = cen.groupby(["outlet", "issue", "week"]).size().rename("issue_n").reset_index()
    rows = [json.loads(l) for l in open(os.path.join(P, "data/raw/mediacloud/r1_source_weeks.jsonl"))]
    mc = pd.DataFrame(rows); mc = mc[mc["query"] == "all"]
    mc["week"] = mc["date"].map(week_of)
    den = mc.groupby(["domain", "week"])["count"].sum().rename("all_n").reset_index()
    toi = pd.read_csv(os.path.join(P, "data/coded/toi_denominator_weeks.csv"))
    toi_share = dict(zip(toi.week_start, toi.toi_share))
    out = []
    for o, (country, dom, host) in OUTLETS.items():
        if host:  # Bangladesh via GDELT
            g = pd.read_csv(os.path.join(P, "data/raw/gdelt/g4_host_weeks.csv"))
            g = g[g.host == host]
            for _, r in g.iterrows():
                for iss in ISSUES:
                    out.append((o, iss, r.week_start, int(r[f"{iss}_title"]), int(r.articles)))
            continue
        d = den[den.domain == dom].set_index("week")["all_n"].to_dict()
        for iss in ISSUES:
            n = num[(num.outlet == o) & (num.issue == iss)].set_index("week")["issue_n"].to_dict()
            for w in sorted(W):
                if w not in d: continue
                a = d[w]
                if o == "timesofindia": a = a * toi_share.get(w, np.nan)
                if o == "washingtonpost.com" and w > WAPO_END: continue
                out.append((o, iss, w, int(n.get(w, 0)), float(a)))
    s = pd.DataFrame(out, columns=["outlet", "issue", "week", "issue_n", "all_n"])
    s = s[s.week.isin(W)].dropna()
    s = s[s.all_n >= MIN_WEEK_STORIES].copy()
    s["share"] = s.issue_n / s.all_n
    _series_cache["s"] = s
    return s


def core_series(exclude=None):
    """X7: the core share each week = mean over the core outlets present that week (optionally without `exclude`)."""
    s = weekly_series(); core = [c for c in CORE if c != exclude]
    c = s[s.outlet.isin(core)].groupby(["issue", "week"]).agg(core_share=("share", "mean"), core_n=("outlet", "count")).reset_index()
    return c


def events_weekly():
    """A31: weekly GDELT root-event counts per issue (D23)."""
    e = pd.read_csv(os.path.join(P, "data/raw/gdelt/g6b_issue_event_weeks.csv"))
    return {"ukraine": dict(zip(e.week_start, e.ukraine_events)), "gaza": dict(zip(e.week_start, e.gaza_events)),
            "cop": dict(zip(e.week_start, e.cop_place_events))}


def _resid(y, x):
    X = np.column_stack([np.ones(len(x)), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def v1_salience(outlet, issue, weeks_subset=None, core_issue=None, core_exclude=None):
    """A25: Pearson r between the residuals of the outlet's and the core's weekly shares on the issue's weekly event
    count. core_issue ≠ issue gives the mismatched-issue benchmark (P4). → (r, n_weeks) or (nan, n)."""
    s = weekly_series(); ci = core_issue or issue
    o = s[(s.outlet == outlet) & (s.issue == issue)][["week", "share"]]
    c = core_series(core_exclude); c = c[c.issue == ci][["week", "core_share"]]
    m = o.merge(c, on="week")
    if weeks_subset is not None: m = m[m.week.isin(weeks_subset)]
    ev = events_weekly()[issue]; m = m[m.week.isin(ev.keys())]
    if len(m) < MIN_WEEKS: return float("nan"), int(len(m))
    x = np.array([ev[w] for w in m.week], float)
    ro = _resid(m.share.values.astype(float), x); rc = _resid(m.core_share.values.astype(float), x)
    if ro.std() == 0 or rc.std() == 0: return float("nan"), int(len(m))
    return float(np.corrcoef(ro, rc)[0, 1]), int(len(m))


def v3b_xcorr_lag(outlet, issue, weeks_subset=None, core_issue=None):
    """V3b: lag k (weeks) at which corr(outlet[t], core[t-k]) peaks over k in -4..4 on raw weekly shares; entered as -k."""
    s = weekly_series(); ci = core_issue or issue
    o = s[(s.outlet == outlet) & (s.issue == issue)].set_index("week")["share"]
    c = core_series(); c = c[c.issue == ci].set_index("week")["core_share"]
    W = weeks(); idx = {w: i for i, w in enumerate(W)}
    best = None
    for k in range(-MAX_XCORR_LAG, MAX_XCORR_LAG + 1):
        xs, ys = [], []
        for w in o.index:
            if weeks_subset is not None and w not in weeks_subset: continue
            j = idx[w] - k
            if j < 0 or j >= len(W) or W[j] not in c.index: continue
            xs.append(o[w]); ys.append(c[W[j]])
        if len(xs) < MIN_WEEKS: continue
        xs, ys = np.array(xs), np.array(ys)
        if xs.std() == 0 or ys.std() == 0: continue
        r = float(np.corrcoef(xs, ys)[0, 1])
        if best is None or r > best[1]: best = (k, r, len(xs))
    if best is None: return float("nan"), float("nan"), 0
    return -best[0], best[1], best[2]


# ---------------------------------------------------------------- timing (V3a) --------------------------------------
_ev_cache = {}

def story_events():
    """D22: outlet × issue × event rows with the outlet's first mention; adds core_first (earliest core mention),
    lag_days (outlet first − core first, censored at CENSOR_DAYS), core_first_day_outlets (core outlets whose first
    mention falls on the core first day: the uncertainty proxy for P6, A36)."""
    if "e" in _ev_cache: return _ev_cache["e"]
    g = pd.read_csv(os.path.join(P, "data/raw/gdelt/g5_story_events.csv"))
    g["first_mention"] = pd.to_datetime(g["first_mention"].str.replace(" UTC", ""), utc=True)
    core = g[g.outlet.isin(CORE)]
    cf = core.groupby(["issue", "GLOBALEVENTID"])["first_mention"].min().rename("core_first").reset_index()
    core = core.merge(cf, on=["issue", "GLOBALEVENTID"])
    core["same_day"] = (core.first_mention.dt.floor("D") == core.core_first.dt.floor("D")).astype(int)
    cnt = core.groupby(["issue", "GLOBALEVENTID"]).agg(core_first_day_outlets=("same_day", "sum"), core_outlets=("outlet", "nunique"),
                                                       core_stories=("stories", "sum")).reset_index()
    g = g.merge(cf, on=["issue", "GLOBALEVENTID"]).merge(cnt, on=["issue", "GLOBALEVENTID"])
    g["lag_raw"] = (g.first_mention - g.core_first).dt.total_seconds() / 86400.0
    g["lag_days"] = g.lag_raw.clip(lower=-CENSOR_DAYS, upper=CENSOR_DAYS)
    g["core_first_date"] = g.core_first.dt.strftime("%Y-%m-%d")
    g = g[(g.core_first_date >= PERIOD[0]) & (g.core_first_date <= PERIOD[1])]
    _ev_cache["e"] = g
    return g


def v3a_timing(outlet, issue, half=None, rng=None):
    """V3a: −median lag (days) over the outlet's events with a core mention; half ∈ {H1, H2} selects by the core first
    date. With rng: the permutation benchmark (core first-mention times shuffled across the issue's events, A36)."""
    g = story_events(); e = g[(g.outlet == outlet) & (g.issue == issue)]
    if half: e = e[e.core_first_date.map(lambda d: half_of(issue, d)) == half]
    if len(e) < MIN_EVENTS: return float("nan"), int(len(e))
    if rng is not None:
        cf = e.core_first.values.copy(); rng.shuffle(cf)
        lag = ((e.first_mention.values - cf) / np.timedelta64(1, "D")).astype(float)
        lag = np.clip(lag, -CENSOR_DAYS, CENSOR_DAYS)
        return float(-np.median(lag)), int(len(e))
    return float(-e.lag_days.median()), int(len(e))


# ---------------------------------------------------------------- framing (V2) and credits ---------------------------
_codes_cache = {}

def codes():
    if "c" in _codes_cache: return _codes_cache["c"]
    c = pd.DataFrame([json.loads(l) for l in open(os.path.join(P, "data/coded/codes_final.jsonl"))])
    c["half"] = [half_of(i, d) for i, d in zip(c.issue, c.date)]
    _codes_cache["c"] = c
    return c


def _dist(frames):
    cnt = collections.Counter(frames); n = sum(cnt.values())
    return np.array([cnt.get(f, 0) / n for f in FRAMES], float)


def jsd(p, q):
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return float(np.sqrt(max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))))


def v2_framing(outlet_frames, core_frames, seed=SEED):
    """A25: (1 − JSD(outlet, core)) minus its mean over PERM_DRAWS random splits of the pooled articles at the observed
    sizes. → (v2, sim_obs, sim_expected, n_outlet, n_core); nan when either sample is empty."""
    o = list(outlet_frames); c = list(core_frames)
    if not o or not c: return float("nan"), float("nan"), float("nan"), len(o), len(c)
    sim = 1 - jsd(_dist(o), _dist(c))
    pool = np.array(o + c); rng = np.random.default_rng(seed); exp = []
    for _ in range(PERM_DRAWS):
        rng.shuffle(pool); exp.append(1 - jsd(_dist(pool[:len(o)]), _dist(pool[len(o):])))
    e = float(np.mean(exp))
    return sim - e, sim, e, len(o), len(c)


def core_frames(issue, half=None, exclude_headline_only=False, nonwire=False, exclude_wire=False):
    c = codes(); k = c[(c.tier == "core") & (c.issue == issue)]
    if half: k = k[k.half == half]
    if exclude_headline_only: k = k[k.text_window != "headline_only"]
    if nonwire or exclude_wire: k = k[k.wire_credit == 0]
    return list(k.frame)


def outlet_frames(outlet, issue, half=None, nonwire=False):
    c = codes(); k = c[(c.outlet == outlet) & (c.issue == issue)]
    if half: k = k[k.half == half]
    if nonwire: k = k[k.wire_credit == 0]
    return list(k.frame)


def credit_shares(outlet, issue):
    """V4, V9, V11 over the cell's foreign stories (C4); → dict with n_foreign and the three shares (nan if no foreign story)."""
    c = codes(); k = c[(c.outlet == outlet) & (c.issue == issue)]
    f = k[k.foreign_story == 1]
    n = int(len(f))
    sh = lambda col: float(f[col].mean()) if n else float("nan")
    return {"n_coded": int(len(k)), "n_foreign": n, "V4": sh("wire_credit"), "V9": sh("staff_foreign_byline"), "V11": sh("national_agency_credit")}


def v10_own_country():
    """C9 on the census titles: share of an outlet's issue stories whose title names its own country (titles only; the
    census holds no text). → dict (outlet, issue) → (share, n)."""
    import re
    from urllib.parse import urlparse
    terms = {k: re.compile(v, re.I) for k, v in COUNTRY_TERMS.items()}
    def nurl(u):
        p = urlparse(u or ""); h = p.netloc.lower(); h = h[4:] if h.startswith("www.") else h
        return h + p.path.rstrip("/")
    cen = pd.read_csv(os.path.join(P, "data/sampling/census_urls.csv"))
    keep = set(zip(cen.outlet, cen.issue, cen.url_norm))
    by_dom = collections.defaultdict(list)
    for o, (c, dom, host) in OUTLETS.items():
        if dom: by_dom[dom].append(o)
    hits = collections.Counter(); tot = collections.Counter()
    for iss in ISSUES:
        for l in open(os.path.join(P, f"data/raw/mediacloud/r1_stories_{iss}.jsonl")):
            r = json.loads(l)
            for o in by_dom.get(r.get("domain"), []):
                if OUTLETS[o][0] == "core": continue
                u = nurl(r["url"])
                if (o, iss, u) not in keep: continue
                key = (o, iss, u)
                if key in hits: continue
                tot[(o, iss)] += 1
                if terms[OUTLETS[o][0]].search(r.get("title") or ""): hits[(o, iss)] += 1
                hits[key] = 1
    g3 = pd.read_csv(os.path.join(P, "data/raw/gdelt/g3_bangladesh_census.csv"))
    for _, r in g3.iterrows():
        o = r.domain
        if o not in OUTLETS or r.host != OUTLETS[o][2]: continue
        for iss in ISSUES:
            if r[iss]:
                tot[(o, iss)] += 1
                if terms["Bangladesh"].search(str(r.title)): hits[(o, iss)] += 1
    return {k: (hits[k] / tot[k] if tot[k] else float("nan"), tot[k]) for k in tot}


# ---------------------------------------------------------------- cells and run bookkeeping --------------------------
def kept_cells():
    """Outlet × issue cells after the 20-story floor (data/sampling/cells.csv)."""
    c = pd.read_csv(os.path.join(P, "data/sampling/cells.csv"))
    c = c[~c.status.str.startswith("dropped")]
    return [(o, i) for o, i in zip(c.outlet, c.issue)]


def dropped_cells():
    c = pd.read_csv(os.path.join(P, "data/sampling/cells.csv"))
    return [(o, i) for o, i, s in zip(c.outlet, c.issue, c.status) if s.startswith("dropped")]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def new_run_id(tag):
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d"); n = 1
    log = os.path.join(P, "data/runs.jsonl")
    if os.path.exists(log):
        for l in open(log):
            r = json.loads(l)
            if r["run_id"].startswith(f"run_{today}_"): n = max(n, int(r["run_id"].split("_")[-1]) + 1)
    return f"run_{today}_{n:02d}"


def write_environment():
    env = os.path.join(P, "data/analysis/environment.txt")
    lines = [f"python {platform.python_version()} ({platform.platform()})"]
    for m in ("numpy", "pandas", "scipy", "statsmodels", "matplotlib"):
        try: lines.append(f"{m} {__import__(m).__version__}")
        except Exception: lines.append(f"{m} not installed")
    lines.append(f"seed {SEED}")
    open(env, "w").write("\n".join(lines) + "\n")
    return "data/analysis/environment.txt"


def finish_run(run_id, script, inputs, tables, figures, descriptives, summary_md, started, deviations, notes=""):
    """Write results/<run_id>/{run.json, tables.json, summary.md}, append data/runs.jsonl and a runs.log.jsonl line."""
    d = os.path.join(P, "results", run_id); os.makedirs(os.path.join(d, "figures"), exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    env = write_environment()
    shas = {i: sha256(os.path.join(P, i)) for i in inputs if os.path.isfile(os.path.join(P, i))}
    run = {"run_id": run_id, "plan_revision": PLAN_REVISION, "script": script, "inputs": inputs, "sha256s": shas,
           "started": started, "finished": now, "environment": env, "seed": SEED, "deviations_applied": deviations,
           "model": None, "notes": notes}
    json.dump(run, open(os.path.join(d, "run.json"), "w"), indent=1, ensure_ascii=False)
    tj = {"schema": "rihlah-results/2.0", "run_id": run_id, "plan_revision": PLAN_REVISION, "generated": now,
          "tables": tables, "figures": figures, "descriptives": descriptives}
    json.dump(tj, open(os.path.join(d, "tables.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(d, "summary.md"), "w").write(summary_md)
    outputs = [f"results/{run_id}/tables.json"] + [f"results/{run_id}/{f['file']}" for f in figures]
    line = {"run_id": run_id, "plan_revision": PLAN_REVISION, "script": script, "inputs": inputs, "outputs": outputs,
            "deviations_applied": deviations, "ts": now}
    with open(os.path.join(P, "data/runs.jsonl"), "a") as f: f.write(json.dumps(line, ensure_ascii=False) + "\n")
    with open(os.path.join(P, "runs.log.jsonl"), "a") as f:
        f.write(json.dumps({"ts": now, "action": "analysis_run", "project": os.path.basename(P), "args": [script, run_id],
                            "result": {"tables": [t["label"] for t in tables], "figures": [f["label"] for f in figures]}}) + "\n")
    print(f"run {run_id} written → results/{run_id}/")
    return d


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return f"{x:.{nd}f}"


def fmt_p(p):
    if p is None or np.isnan(p): return "—"
    if p < 0.001: return "< .001"
    v = f"{p:.3f}"
    return v[1:] if v.startswith("0") else v


def holm(pvals):
    """Holm step-down adjusted p-values for a list (nan kept)."""
    idx = [i for i, p in enumerate(pvals) if p is not None and not np.isnan(p)]
    m = len(idx); order = sorted(idx, key=lambda i: pvals[i]); adj = [float("nan")] * len(pvals); running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvals[i]); running = max(running, val); adj[i] = running
    return adj
