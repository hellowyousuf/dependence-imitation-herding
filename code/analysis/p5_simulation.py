#!/usr/bin/env python3
"""P5 step 2 — the CPU rule step (RQ2): 8 configurations × 20 seeds on the cached proposals (plan P5 steps 3–5; A15, A19,
A21, A24, A26, A29). Reads data/raw/sim/proposals/{A,B}/<date>.jsonl, data/raw/sim/wire_frames/<date>.json (registered
by register_data.py after `data ready P5`), data/analysis/sim/feed_*.jsonl and outlets.json, the observed cells
(data/coded/following_cells.csv) and the weekly series. Fits one free parameter per rule on the first half of each issue
(grid search on the mean standardized error), scores V8 on the second half, and writes T4 and F3.

Rules (plan P5.rules), applied dependence → imitation → herding:
  dependence  B = round(n_i × (1 − W_i) × (w × C_i + 1 − w)) per issue; keep the B highest-priority non-wire proposals of the
              issue, fill the rest of the proposed count from the day's wire copy (wire frames from the Colab labels)
  imitation   target (issue, frame) shares = (1 − v) × a_i + v × s_core(t); a_i = the proposal's own shares; s_core(t) = the
              core feed's issue shares that day × the core coded sample's frame shares within the issue; cells filled by
              priority, shortfall from the day's core items of that issue (feed A)
  herding     an item new (≤ 2 days since it entered the feed) and uncertain (its issue has < 3 core stories in that day's
              feed) is published with probability min(1, c × m_s / N), m_s = outlets (simulated so far in the run, plus the
              core when the item is a core story) that carried it, N = 18 + 4; the frame most earlier adopters used
Implementation choices beyond the plan's wording are build assumptions (A39) and are listed in run.json.
Dry run: --dry-run synthesizes proposals for 60 days so that the machinery is tested before the data arrive."""
import os, sys, json, glob, random, collections, argparse, datetime as dt, itertools
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")  # single-threaded BLAS: forked workers must not inherit a thread pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf

ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--seeds", type=int, default=20)
ap.add_argument("--proposals", default="data/raw/sim"); ap.add_argument("--grid", type=int, default=11); ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--budget", type=float, default=0, help="seconds; when exceeded the run saves its cache and exits 3 (re-run to resume)")
a = ap.parse_args()
SIM = os.path.join(pf.P, "data/analysis/sim"); RAW = os.path.join(pf.P, a.proposals)
CONFIGS = ["baseline", "D", "I", "H", "DI", "DH", "IH", "DIH"]; N_OUT = 22
started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------- inputs
feed = {}
for kind in ("core", "wire", "events"):
    p = os.path.join(SIM, f"feed_{kind}.jsonl")
    if os.path.exists(p):
        for l in open(p):
            x = json.loads(l); feed[x["id"]] = x
outlets = json.load(open(os.path.join(SIM, "outlets.json"))); codes_map = {o["code"]: o["outlet"] for o in outlets}  # release: outlet names from outlets.json
cells = pd.read_csv(os.path.join(pf.P, "data/coded/following_cells.csv")); cells = cells[(cells.tier != "core") & cells.cell_kept]
days_all = []; d0 = dt.date.fromisoformat(pf.PERIOD[0])
while d0 <= dt.date.fromisoformat(pf.PERIOD[1]): days_all.append(d0.isoformat()); d0 += dt.timedelta(days=1)
core_by_day = collections.defaultdict(list)
for x in feed.values():
    if x["kind"] == "core": core_by_day[x["date"]].append(x)
wire_by_day = collections.defaultdict(list); feed_by_day = collections.defaultdict(list)
for x in feed.values():
    feed_by_day[x["date"]].append(x)
    if x["kind"] == "wire": wire_by_day[x["date"]].append(x)
core_frame_share = {iss: pf._dist(pf.core_frames(iss)) for iss in pf.ISSUES}
# plan P5 step 6 fallback (agent labels alpha .232 < .80, October 7, 2026): simulated framing uses the model coder's frames on
# written-out proposals (50 per outlet x issue, held-out half; data/coded/model/cell_labels/all_coded.json) and on a sample of
# wire headlines; published items without a coder frame do not enter the simulated frame distribution.
CODER = {}
_cp = os.path.join(pf.P, "data/coded/model/cell_labels/all_coded.json")
if os.path.exists(_cp):
    for x in json.load(open(_cp)):
        p = x["sample_id"].split("|")
        if p[0] == "cell": CODER[(p[1], p[2], p[3])] = x["frame"]      # (outlet code, issue, item id)
        elif p[0] == "wire": CODER[("wire", p[1])] = x["frame"]
def coder_frame(code, issue, item_id, kind):
    f = CODER.get((code, issue, item_id))
    if f is None and kind == "wire": f = CODER.get(("wire", item_id))
    return f

def load_proposals():
    P = {"A": {}, "B": {}}; WF = {}
    if a.dry_run:
        rng = random.Random(1); days = days_all[::10]
        for d in days:
            items_A = [x for x in feed.values() if x["date"] == d]; items_B = [x for x in items_A if x["kind"] != "core"]
            for fd, items in (("A", items_A), ("B", items_B)):
                for o in outlets:
                    for k in (1, 2, 3):
                        n = min(len(items), rng.randint(0, 8))
                        P[fd][(o["code"], d, k)] = [{"id": x["id"], "priority": rng.randint(1, 5), "frame": rng.choice(pf.FRAMES)} for x in rng.sample(items, n)]
            WF.update({x["id"]: rng.choice(pf.FRAMES) for x in wire_by_day.get(d, [])})
        return P, WF, days
    days = set()
    for fd in ("A", "B"):
        for f in sorted(glob.glob(os.path.join(RAW, "proposals", fd, "*.jsonl"))):
            for l in open(f):
                r = json.loads(l); P[fd][(r["code"], r["date"], r["sample"])] = r["proposals"]; days.add(r["date"])
    for f in glob.glob(os.path.join(RAW, "wire_frames", "*.json")): WF.update(json.load(open(f)))
    return P, WF, sorted(days)
PROPS, WIRE_FRAMES, DAYS = load_proposals()
if not DAYS: sys.exit("no proposals found")

# ---------------------------------------------------------------- the rules
def run_outlet_day(o, d, props, cfg, par, rng, state, order="DIH"):
    """→ list of published {id, issue, frame, kind, date} for outlet o on day d; rules applied in `order`."""
    props = [dict(p, issue=feed[p["id"]]["issue"] or "", kind=feed[p["id"]]["kind"]) for p in props if p["id"] in feed]
    n_prop = len(props)
    pub = list(props)
    for rule in order:
      if rule == "D" and "D" in cfg:
          out = []
          for iss in pf.ISSUES:
              pi = [p for p in pub if p["issue"] == iss]
              if not pi: continue
              n_i = o["n_i_daily_fitting_half"].get(iss, 0.0); W, C = (o["W_i"] or 0.0), (o["C_i"] or 0.0)
              B = int(round(n_i * (1 - W) * (par["w"] * C + 1 - par["w"])))
              own = sorted([p for p in pi if p["kind"] != "wire"], key=lambda p: -p["priority"])[:B]
              need = len(pi) - len(own)
              wires = [x for x in wire_by_day.get(d, []) if x["issue"] == iss]; rng.shuffle(wires)
              fill = [{"id": x["id"], "priority": 3, "frame": WIRE_FRAMES.get(x["id"], "other"), "issue": iss, "kind": "wire"} for x in wires[:max(0, need)]]
              out += own + fill
          pub = out
      if rule == "I" and "I" in cfg and pub:
          cnt = collections.Counter((p["issue"], p["frame"]) for p in pub); n = len(pub)
          core_today = collections.Counter(x["issue"] for x in core_by_day.get(d, [])); tot = sum(core_today.values())
          target = {}
          for iss in pf.ISSUES:
              s_issue = core_today[iss] / tot if tot else 0.0
              for j, fr in enumerate(pf.FRAMES):
                  a_ = cnt[(iss, fr)] / n; s_ = s_issue * core_frame_share[iss][j]
                  target[(iss, fr)] = (1 - par["v"]) * a_ + par["v"] * s_
          out = []
          for (iss, fr), share in target.items():
              k = int(round(share * n))
              if k <= 0: continue
              have = sorted([p for p in pub if p["issue"] == iss and p["frame"] == fr], key=lambda p: -p["priority"])[:k]
              out += have
              short = k - len(have)
              if short > 0:
                  cands = [x for x in core_by_day.get(d, []) if x["issue"] == iss and x["id"] not in {p["id"] for p in out}]; rng.shuffle(cands)
                  out += [{"id": x["id"], "priority": 3, "frame": fr, "issue": iss, "kind": "core"} for x in cands[:short]]
          pub = out
      if rule == "H" and "H" in cfg:
          d_date = dt.date.fromisoformat(d); have = {p["id"] for p in pub}
          core_today = collections.Counter(x["issue"] for x in core_by_day.get(d, []))
          recent = [x for k in range(0, 3) for x in feed_by_day.get((d_date - dt.timedelta(days=k)).isoformat(), [])]
          for x in recent:
              iss = x["issue"]
              if not iss or core_today[iss] >= 3 or x["id"] in have: continue
              m = len(state["adopters"].get(x["id"], set())) + (1 if x["kind"] == "core" else 0)
              if m == 0: continue
              if rng.random() < min(1.0, par["c"] * m / N_OUT):
                  frames = state["frames"].get(x["id"], collections.Counter())
                  fr = frames.most_common(1)[0][0] if frames else (WIRE_FRAMES.get(x["id"]) or "other")
                  pub.append({"id": x["id"], "priority": 3, "frame": fr, "issue": iss, "kind": x["kind"]}); have.add(x["id"])
    pub = sorted(pub, key=lambda p: -p["priority"])[:max(n_prop, len(pub) if "H" in cfg else n_prop)]
    for p in pub:
        state["adopters"].setdefault(p["id"], set()).add(o["code"]); state["frames"].setdefault(p["id"], collections.Counter())[p["frame"]] += 1
    return [dict(p, date=d) for p in pub]

def simulate(cfg, par, seed, days, order="DIH"):
    rng = random.Random(f"{pf.SEED}|{seed}|{cfg}"); state = {"adopters": {}, "frames": {}}; fd = "A" if "I" in cfg else "B"
    out = collections.defaultdict(list)
    for d in days:
        for o in outlets:
            k = rng.randint(1, 3); props = PROPS[fd].get((o["code"], d, k), [])
            out[o["code"]] += run_outlet_day(o, d, props, cfg, par, rng, state, order)
    return out

# ---------------------------------------------------------------- V8 on a half
series = pf.weekly_series(); core = pf.core_series(); ev = pf.events_weekly()
def v8(published, half):
    rows = []
    for o in outlets:
        name = codes_map[o["code"]]; stories = published[o["code"]]
        for iss in o["cells_kept"]:
            s, m, e = pf.halves()[iss]; lo, hi = (s, m) if half == "H1" else (m, e)
            st = [p for p in stories if p["issue"] == iss and lo <= p["date"] < hi]
            # salience: simulated weekly issue count / observed all_n, event-adjusted r with the observed core series
            wk = collections.Counter(pf.week_of(p["date"]) for p in st)
            ob = series[(series.outlet == name) & (series.issue == iss)][["week", "all_n"]]; ob = ob[(ob.week >= lo) & (ob.week < hi)]
            cs = core[core.issue == iss][["week", "core_share"]]; mm = ob.merge(cs, on="week"); mm = mm[mm.week.isin(ev[iss].keys())]
            if len(mm) >= pf.MIN_WEEKS:
                x = np.array([ev[iss][w] for w in mm.week], float); ys = np.array([wk.get(w, 0) / an for w, an in zip(mm.week, mm.all_n)])
                ro, rc = pf._resid(ys, x), pf._resid(mm.core_share.values.astype(float), x)
                v1 = float(np.corrcoef(ro, rc)[0, 1]) if ro.std() > 0 and rc.std() > 0 else np.nan
            else: v1 = np.nan
            fr = [coder_frame(o["code"], iss, p["id"], p["kind"]) for p in st]; fr = [f for f in fr if f]
            v2 = pf.v2_framing(fr, pf.core_frames(iss, half))[0] if len(fr) >= 5 else np.nan
            lags = [(dt.date.fromisoformat(p["date"]) - dt.date.fromisoformat(feed[p["id"]]["date"])).days for p in st if p["kind"] in ("core", "event")]
            v3 = -float(np.median(np.clip(lags, -pf.CENSOR_DAYS, pf.CENSOR_DAYS))) if len(lags) >= 3 else np.nan
            rows.append({"outlet": name, "issue": iss, "V1": v1, "V2": v2, "V3a": v3, "n_pub": len(st)})
    return pd.DataFrame(rows)
obs = {"H1": cells.set_index(["outlet", "issue"])[["V1_H1", "V2_H1", "V3a_H1"]].rename(columns={"V1_H1": "V1", "V2_H1": "V2", "V3a_H1": "V3a"}),
       "H2": cells.set_index(["outlet", "issue"])[["V1_H2", "V2_H2", "V3a_H2"]].rename(columns={"V1_H2": "V1", "V2_H2": "V2", "V3a_H2": "V3a"})}
def std_error(sim, half):
    e = {}
    for lev in ("V1", "V2", "V3a"):
        m = sim.set_index(["outlet", "issue"])[lev].to_frame("sim").join(obs[half][lev].rename("obs")).dropna()
        sd = cells[f"{lev}_{half}"].std(ddof=1)
        e[lev] = float((m.sim - m.obs).abs().mean() / sd) if len(m) and sd > 0 else np.nan
    e["mean"] = float(np.nanmean([e["V1"], e["V2"], e["V3a"]]))
    return e

# ---------------------------------------------------------------- fit on H1, score on H2
days_H1 = {iss: [d for d in DAYS if pf.halves()[iss][0] <= d < pf.halves()[iss][1]] for iss in pf.ISSUES}
days_all_run = DAYS
GRID = {"w": np.linspace(0, 1, a.grid), "v": np.linspace(0, 1, a.grid), "c": np.linspace(0.5, 5, a.grid)}
import multiprocessing as mp
def _err(args):
    cfg, par, seed, half, order = args
    return std_error(v8(simulate(cfg, par, seed, days_all_run, order), half), half)
def _sim_v8(args):
    cfg, par, seed, order = args
    sim = v8(simulate(cfg, par, seed, days_all_run, order), "H2"); return sim, std_error(sim, "H2")
N_WORKERS = int(os.environ.get("P5_WORKERS", "1"))  # the loaded proposals take ~1.5 GB; forked workers touch every page, so more than one worker exhausts a 4 GB machine
POOL = mp.get_context("fork").Pool(N_WORKERS) if N_WORKERS > 1 else None
# resumable cache of simulation results (the device shell cannot hold a process beyond one call)
CACHE_P = os.path.join(SIM, "_cache", "p5_cache.json" if not a.dry_run else "p5_cache_dry.json"); os.makedirs(os.path.dirname(CACHE_P), exist_ok=True)
CACHE = json.load(open(CACHE_P)) if os.path.exists(CACHE_P) else {}
T0 = __import__("time").time()
def _key(cfg, par, seed, half, order): return f"{cfg}|{par['w']:.4f}|{par['v']:.4f}|{par['c']:.4f}|{seed}|{half}|{order}"
def pool_map(fn, jobs, kind):
    """fn over jobs with caching and a time budget; kind 'err' (std_error dict) or 'sim' (records + error)."""
    out = [None] * len(jobs); todo = []
    for i, j in enumerate(jobs):
        k = kind + ":" + _key(j[0], j[1], j[2], j[3] if kind == "err" else "H2", j[4] if kind == "err" else j[3])
        if k in CACHE: out[i] = CACHE[k]
        else: todo.append((i, k, j))
    for n in range(0, len(todo), 8):
        chunk = todo[n:n + 8]
        res = POOL.map(fn, [j for _, _, j in chunk]) if POOL else [fn(j) for _, _, j in chunk]
        for (i, k, _), r in zip(chunk, res):
            if kind == "sim": r = {"records": r[0].to_dict("records"), "err": r[1]}
            CACHE[k] = r; out[i] = r
        json.dump(CACHE, open(CACHE_P, "w"))
        if a.budget and __import__("time").time() - T0 > a.budget:
            print(f"budget reached: {len(CACHE)} cached results; re-run to resume", flush=True); sys.exit(3)
    return out
def fit_one(key, cfg):
    """one free parameter per rule, fitted in the rule's single-mechanism configuration on the first half (3 seeds per grid point)"""
    jobs = []
    for val in GRID[key]:
        par = {"w": 0, "v": 0, "c": 0}; par[key] = float(val)
        jobs += [(cfg, par, s_, "H1", "DIH") for s_ in range(1, 4)]
    errs = pool_map(_err, jobs, "err"); best = None
    for i, val in enumerate(GRID[key]):
        e = float(np.nanmean([x["mean"] for x in errs[3 * i:3 * i + 3]]))
        if best is None or e < best[0]: best = (e, float(val))
    print(f"fitted {key} in {cfg}: {best[1]:.2f} (H1 error {best[0]:.3f})", flush=True)
    return best[1]
fitted = {"w": fit_one("w", "D"), "v": fit_one("v", "I"), "c": fit_one("c", "H")}
params = {cfg: {"w": fitted["w"] if "D" in cfg else 0, "v": fitted["v"] if "I" in cfg else 0, "c": fitted["c"] if "H" in cfg else 0} for cfg in CONFIGS}
res = {cfg: [] for cfg in CONFIGS}; sims = {cfg: [] for cfg in CONFIGS}
for cfg in CONFIGS:
    for r in pool_map(_sim_v8, [(cfg, params[cfg], s_, "DIH") for s_ in range(1, a.seeds + 1)], "sim"):
        res[cfg].append(r["err"]); sims[cfg].append(pd.DataFrame(r["records"]))
    print(f"{cfg}: mean error {np.mean([r['mean'] for r in res[cfg]]):.3f}", flush=True)
def summarize(cfg):
    E = pd.DataFrame(res[cfg]); return {"V1": E.V1.mean(), "V2": E.V2.mean(), "V3a": E.V3a.mean(), "mean": E["mean"].mean(), "sd": E["mean"].std(ddof=1)}
S = {cfg: summarize(cfg) for cfg in CONFIGS}
def diff(cfg, other):
    d = np.array([r["mean"] for r in res[cfg]]) - np.array([r["mean"] for r in res[other]]); return float(d.mean()), float(d.std(ddof=1))
singles = ["D", "I", "H"]; winner = None
for cfg in singles:
    others = [c for c in singles if c != cfg]
    ok = all(S[cfg]["mean"] < S[c]["mean"] for c in others) and all((lambda m, sd: m < 0 and abs(m) > 2 * sd)(*diff(cfg, c)) for c in others + ["baseline"])
    if ok: winner = cfg
# bootstrap over outlets for the winner's margin (same error as std_error, computed from per-outlet sums so that 1,000 resamples are cheap)
boot_share = None
if winner:
    rng = np.random.default_rng(pf.SEED); names = sorted(cells.outlet.unique()); idx = {n: i for i, n in enumerate(names)}; hold = 0
    SD = {lev: float(cells[f"{lev}_H2"].std(ddof=1)) for lev in ("V1", "V2", "V3a")}
    def per_outlet(sim):
        """per level: (sum of |sim-obs| by outlet, count by outlet) over cells with both values"""
        out = {}
        for lev in ("V1", "V2", "V3a"):
            m = sim.set_index(["outlet", "issue"])[lev].to_frame("sim").join(obs["H2"][lev].rename("obs")).dropna().reset_index()
            su = np.zeros(len(names)); ct = np.zeros(len(names))
            for n, g in m.groupby("outlet"): su[idx[n]] = (g.sim - g.obs).abs().sum(); ct[idx[n]] = len(g)
            out[lev] = (su, ct)
        return out
    PO = {cfg: [per_outlet(sims[cfg][s]) for s in range(a.seeds)] for cfg in singles + ["baseline"]}
    def err_sub(cfg, pick):
        out = []
        for s in range(a.seeds):
            e = []
            for lev in ("V1", "V2", "V3a"):
                su, ct = PO[cfg][s][lev]; n = ct[pick].sum()
                e.append(su[pick].sum() / n / SD[lev] if n > 0 and SD[lev] > 0 else np.nan)
            out.append(float(np.nanmean(e)))
        return np.array(out)
    for _ in range(a.boot):
        pick = rng.integers(0, len(names), len(names))
        e_w = err_sub(winner, pick); ok = True
        for c in [c for c in singles if c != winner] + ["baseline"]:
            d = e_w - err_sub(c, pick); ok = ok and d.mean() < 0 and abs(d.mean()) > 2 * d.std(ddof=1)
        hold += ok
    boot_share = hold / a.boot
# sign agreement: observed tier contrast and stake slope per level vs simulated
def contrasts(df, prefix=""):
    out = {}
    m = df[[c for c in df.columns if c not in ("tier", "stake")]].merge(cells[["outlet", "issue", "tier", "stake"]], on=["outlet", "issue"])
    for lev in ("V1", "V2", "V3a"):
        out[f"tier_{lev}"] = np.sign(m[m.tier == "periphery"][lev].mean() - m[m.tier == "semi-periphery"][lev].mean())
        g = m.groupby("stake")[lev].mean(); out[f"stake_{lev}"] = np.sign(g.get(2, np.nan) - g.get(0, np.nan))
    return out
obs_c = contrasts(cells[["outlet", "issue"]].assign(V1=cells.V1_H2.values, V2=cells.V2_H2.values, V3a=cells.V3a_H2.values))
sign_rows = {}
for cfg in CONFIGS:
    agree = []
    for sim in sims[cfg]:
        c = contrasts(sim); agree.append(np.mean([c[k] == obs_c[k] for k in obs_c if not np.isnan(obs_c[k]) and not np.isnan(c[k])]))
    sign_rows[cfg] = float(np.nanmean(agree))
# within-outlet error (A29): deviations from the outlet's own mean across issues and halves
def _sim_both(args):
    cfg, par, seed, order = args
    pub = simulate(cfg, par, seed, days_all_run, order); parts = []
    for half in ("H1", "H2"):
        sim = v8(pub, half); sim["half"] = half; parts.append(sim)
    return pd.concat(parts), None
def within(cfg):
    out = []
    for r in pool_map(_sim_both, [(cfg, params[cfg], s_, "BOTH") for s_ in range(1, min(a.seeds, 5) + 1)], "sim"):
        sim = pd.DataFrame(r["records"]); o2 = pd.concat([obs[h].reset_index().assign(half=h) for h in ("H1", "H2")])
        m = sim.merge(o2, on=["outlet", "issue", "half"], suffixes=("_s", "_o")).dropna()
        errs = []
        for lev in ("V1", "V2", "V3a"):
            ds = m[f"{lev}_s"] - m.groupby("outlet")[f"{lev}_s"].transform("mean"); do = m[f"{lev}_o"] - m.groupby("outlet")[f"{lev}_o"].transform("mean")
            sd = do.std(ddof=1); errs.append(float((ds - do).abs().mean() / sd) if sd > 0 else np.nan)
        out.append(np.nanmean(errs))
    return float(np.nanmean(out))
within_err = {cfg: within(cfg) for cfg in CONFIGS}
# reverse order for a winning pair
best_all = min(CONFIGS, key=lambda c: S[c]["mean"]); reverse_note = ""; rev = None
if len(best_all) == 2:
    rev_order = "".join(reversed([r for r in "DIH" if r in best_all])) + "".join(r for r in "DIH" if r not in best_all)
    rev_res = pool_map(_err, [(best_all, params[best_all], s_, "H2", rev_order) for s_ in range(1, a.seeds + 1)], "err")
    E = pd.DataFrame(rev_res); rev = {"V1": E.V1.mean(), "V2": E.V2.mean(), "V3a": E.V3a.mean(), "mean": E["mean"].mean(), "sd": E["mean"].std(ddof=1), "order": rev_order}
    reverse_note = f"The best configuration ({best_all}) is a pair; run again with the rules in reverse order ({rev_order[:2]}): mean standardized error {rev['mean']:.3f} (SD {rev['sd']:.3f}) against {S[best_all]['mean']:.3f} in the planned order."

# ---------------------------------------------------------------- tables
rank = sorted(CONFIGS, key=lambda c: S[c]["mean"])
rows = []
for cfg in CONFIGS:
    db = diff(cfg, "baseline"); best_other = min([c for c in singles if c != cfg], key=lambda c: S[c]["mean"]) if cfg in singles else None
    do = diff(cfg, best_other) if best_other else (np.nan, np.nan)
    rows.append([{"baseline": "Baseline (no rule)", "D": "Dependence", "I": "Imitation", "H": "Herding", "DI": "Dependence + imitation", "DH": "Dependence + herding", "IH": "Imitation + herding", "DIH": "All three"}[cfg],
                 pf.fmt(S[cfg]["V1"]), pf.fmt(S[cfg]["V2"]), pf.fmt(S[cfg]["V3a"]), pf.fmt(S[cfg]["mean"]), pf.fmt(S[cfg]["sd"]),
                 f"{pf.fmt(db[0])} ({pf.fmt(db[1])})" if cfg != "baseline" else "—", f"{pf.fmt(do[0])} ({pf.fmt(do[1])})" if best_other else "—",
                 pf.fmt(sign_rows[cfg]), str(rank.index(cfg) + 1), pf.fmt(boot_share) if (winner == cfg and boot_share is not None) else "—", pf.fmt(within_err[cfg])])
if rev is not None:
    rows.append([{"DI": "Dependence + imitation", "DH": "Dependence + herding", "IH": "Imitation + herding"}[best_all] + f" (reverse order {rev['order'][:2]})", pf.fmt(rev["V1"]), pf.fmt(rev["V2"]), pf.fmt(rev["V3a"]), pf.fmt(rev["mean"]), pf.fmt(rev["sd"]), "—", "—", "—", "—", "—", "—"])
# Decision read by the Method's full rule (methods-b10, A29; deviation X15): the seed margin of the plan file AND a bootstrap share of at least 0.95
BOOT_FLOOR = 0.95
if winner and boot_share is not None and boot_share >= BOOT_FLOOR: decision = f"{winner} wins (seed margin met; bootstrap share {boot_share:.2f} at or above {BOOT_FLOOR:.2f})"
elif winner: decision = f"RQ2 undecided: {winner} met the seed margin of the plan file but its margin held in a share of {boot_share:.2f} of outlet resamples, below the {BOOT_FLOOR:.2f} the Method requires (X15)"
else: decision = "no single mechanism wins by the margin: RQ2 undecided"
T4 = {"label": "T4", "title": "Out-of-Sample Fit of Simulation Configurations", "answers": ["RQ2"],
      "columns": ["Configuration", "Std. error salience", "Std. error framing", "Std. error timing", "Mean std. error", "SD across seeds", "Difference from baseline (M, SD of seed-matched difference)",
                  "Difference from the best other single mechanism (M, SD)", "Signs of tier and stake contrasts reproduced", "Rank", "Bootstrap share of outlet resamples holding the margin", "Within-outlet error"],
      "rows": rows,
      "note": (f"Standardized error = mean absolute difference between simulated and observed following over outlet × issue cells on the second validation half, divided by the SD of the observed "
               f"values; {a.seeds} seeds per configuration. Parameters fitted on the first half: " + "; ".join(f"{c}: w = {params[c]['w']:.2f}, v = {params[c]['v']:.2f}, c = {params[c]['c']:.2f}" for c in CONFIGS if c != "baseline") +
               f". Decision (plan P5 margin and the Method's bootstrap condition, X15): {decision}. {reverse_note}" + (" DRY RUN on synthetic proposals — not a result." if a.dry_run else "")),
      "stats": [{"name": "decision", "value": decision, "p": None, "effect": None}, {"name": "framing_source", "value": "simulated framing from the model coder's frames on written-out proposals (agent labels alpha .232 < .80; plan P5 step 6 fallback)", "p": None, "effect": None}] + [{"name": f"err_{cfg}", "value": f"mean std. error = {pf.fmt(S[cfg]['mean'], 3)} (SD {pf.fmt(S[cfg]['sd'], 3)}), salience {pf.fmt(S[cfg]['V1'], 3)}, framing {pf.fmt(S[cfg]['V2'], 3)}, timing {pf.fmt(S[cfg]['V3a'], 3)}", "p": None, "effect": None} for cfg in CONFIGS]}
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 3.6)); xs = np.arange(len(CONFIGS))
for j, (lev, col) in enumerate((("V1", "#1b9e77"), ("V2", "#d95f02"), ("V3a", "#7570b3"))):
    ax.bar(xs + (j - 1) * 0.27, [S[c][lev] for c in CONFIGS], 0.27, color=col, label={"V1": "Salience", "V2": "Framing", "V3a": "Timing"}[lev])
ax.set_xticks(xs); ax.set_xticklabels(CONFIGS); ax.set_ylabel("Standardized error (held-out half)"); ax.legend(frameon=False, fontsize=8); fig.tight_layout()
run_id = pf.new_run_id("p5"); d_out = os.path.join(pf.P, "results", run_id, "figures"); os.makedirs(d_out, exist_ok=True)
fig.savefig(os.path.join(d_out, "f3.svg")); fig.savefig(os.path.join(d_out, "f3.png"), dpi=150)
F3 = {"label": "F3", "title": "Observed and Simulated Following by Configuration", "file": "figures/f3.svg", "note": "Standardized error per level and configuration on the held-out half (mean over seeds)."}
json.dump({"params": params, "errors": res, "winner": winner, "boot_share": boot_share, "sign_agreement": sign_rows, "within_outlet_error": within_err}, open(os.path.join(pf.P, "results", run_id, "fits.json"), "w"), indent=1, default=float)
summary = f"# {run_id} — P5 simulation (CPU rule step){' — DRY RUN' if a.dry_run else ''}\n\n" + "\n".join(f"- {r[0]}: mean error {r[4]} (SD {r[5]}), rank {r[9]}" for r in rows) + f"\n\nDecision: {decision}\n"
inputs = ["data/coded/following_cells.csv", "data/analysis/sim/outlets.json", "data/analysis/sim/feed_core.jsonl", "data/analysis/sim/feed_wire.jsonl"] + ([] if a.dry_run else [a.proposals])
if a.dry_run:
    dd = os.path.join(SIM, "_dryrun"); os.makedirs(dd, exist_ok=True)
    json.dump({"tables": [T4], "figures": [F3], "params": params}, open(os.path.join(dd, "tables_dryrun.json"), "w"), indent=1, default=float)
    import shutil; shutil.move(os.path.join(pf.P, "results", run_id), os.path.join(dd, run_id)) if os.path.isdir(os.path.join(pf.P, "results", run_id)) else None
    print("dry run →", dd); print(summary); sys.exit(0)
pf.finish_run(run_id, "data/analysis/p5_simulation.py", inputs, [T4], [F3], [], summary, started, ["X1", "X4", "X7", "X12", "X13"],
              notes=("DRY RUN on synthetic proposals; withdraw before use. " if a.dry_run else "") + "Supersedes run_20261008_01 (identical errors from the cached simulation records; decision line now read by the Method's full rule, X15). Implementation choices (A39): imitation target shares use the core feed's daily issue shares × the core coded sample's frame shares; herding 'uncertain' = fewer than 3 core stories on the item's issue in the day's feed; items are stories, not GDELT events, for m_s.")
