#!/usr/bin/env python3
"""P1 — describe following (RQ1): V1, V2, V3a, V3b per outlet × issue (whole period and validation halves), V4, V9, V11,
V10; the validation table under X10; T1, T2, F1 and two descriptive tables (T8 outlet credits, T9 checks).
Writes data/coded/following_cells.csv (the cell dataset P2–P4 and P6 read) and results/<run_id>/.
Deviations applied: X1, X5, X6, X7, X10, X11, X12, X13. Seeds fixed (pf_common.SEED)."""
import os, sys, json, datetime as dt, collections
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_common as pf

started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "data/analysis/p1_describe_following.py"
INPUTS = ["data/coded/codes_final.jsonl", "data/sampling/census_urls.csv", "data/sampling/cells.csv",
          "data/raw/mediacloud/r1_source_weeks.jsonl", "data/raw/gdelt/g4_host_weeks.csv", "data/raw/gdelt/g5_story_events.csv",
          "data/raw/gdelt/g6b_issue_event_weeks.csv", "data/raw/gdelt/g3_bangladesh_census.csv", "data/coded/toi_denominator_weeks.csv",
          "data/coded/v5_tier.csv", "data/coded/stability_report.json", "data/coded/stability_report_v1.json", "data/coded/rule_model_check.json", "data/coded/agent_label_check.json", "data/raw/sim/contamination_check.json"]
DEV = ["X1", "X5", "X6", "X7", "X10", "X11", "X12", "X13"]
run_id = pf.new_run_id("p1")
tiers, index = pf.tiers()
W = pf.weeks()
mismatch = {"ukraine": "gaza", "gaza": "cop", "cop": "ukraine"}   # P4 second falsifier benchmark (used in P4; computed here)
v10 = pf.v10_own_country()

rows = []
for o, (country, dom, host) in pf.OUTLETS.items():
    tier = "core" if country == "core" else tiers[country]
    for iss in pf.ISSUES:
        kept = (o, iss) in pf.kept_cells()
        s, m, e = pf.halves()[iss]
        wk1 = [w for w in W if s <= w < m]; wk2 = [w for w in W if m <= w <= e]
        r = {"outlet": o, "name": pf.OUTLET_NAMES[o], "country": country, "tier": tier, "index": index.get(country, np.nan),
             "issue": iss, "stake": pf.STAKE[iss], "cell_kept": kept}
        r["V1"], r["V1_n_weeks"] = pf.v1_salience(o, iss)
        r["V1_H1"], _ = pf.v1_salience(o, iss, weeks_subset=set(wk1)); r["V1_H2"], _ = pf.v1_salience(o, iss, weeks_subset=set(wk2))
        r["V1_bench"], _ = pf.v1_salience(o, iss, core_issue=mismatch[iss])
        r["V1_core3"], _ = pf.v1_salience(o, iss, core_exclude="washingtonpost.com")          # X7 check
        r["V3b"], r["V3b_r"], r["V3b_n"] = pf.v3b_xcorr_lag(o, iss)
        r["V3b_H1"], _, _ = pf.v3b_xcorr_lag(o, iss, weeks_subset=set(wk1)); r["V3b_H2"], _, _ = pf.v3b_xcorr_lag(o, iss, weeks_subset=set(wk2))
        r["V3b_bench"], _, _ = pf.v3b_xcorr_lag(o, iss, core_issue=mismatch[iss])
        r["V3a"], r["V3a_n_events"] = pf.v3a_timing(o, iss)
        r["V3a_H1"], r["V3a_H1_n"] = pf.v3a_timing(o, iss, "H1"); r["V3a_H2"], r["V3a_H2_n"] = pf.v3a_timing(o, iss, "H2")
        r["V3a_bench"], _ = pf.v3a_timing(o, iss, rng=np.random.default_rng(pf.SEED))
        if kept:
            cf = pf.core_frames(iss); of = pf.outlet_frames(o, iss)
            r["V2"], r["V2_sim"], r["V2_exp"], r["V2_n"], r["V2_core_n"] = pf.v2_framing(of, cf)
            r["V2_H1"] = pf.v2_framing(pf.outlet_frames(o, iss, "H1"), pf.core_frames(iss, "H1"))[0]
            r["V2_H2"] = pf.v2_framing(pf.outlet_frames(o, iss, "H2"), pf.core_frames(iss, "H2"))[0]
            r["V2_x11"] = pf.v2_framing(of, pf.core_frames(iss, exclude_headline_only=True))[0]      # X11 sensitivity
            r["V2_corenonwire"] = pf.v2_framing(of, pf.core_frames(iss, exclude_wire=True))[0]         # A22 check
            r["V2_nonwire"] = pf.v2_framing(pf.outlet_frames(o, iss, nonwire=True), pf.core_frames(iss, nonwire=True))[0]  # P6 T2 input
            r["V2_nonwire_x11"] = pf.v2_framing(pf.outlet_frames(o, iss, nonwire=True), pf.core_frames(iss, nonwire=True, exclude_headline_only=True))[0]
            r["V2_nonwire_n"] = len(pf.outlet_frames(o, iss, nonwire=True))
            r["V2_bench"] = pf.v2_framing(of, pf.core_frames(mismatch[iss]))[0]
            cs = pf.credit_shares(o, iss); r.update({"n_coded": cs["n_coded"], "n_foreign": cs["n_foreign"], "V4": cs["V4"], "V9": cs["V9"], "V11": cs["V11"]})
        else:
            for k in ("V2", "V2_sim", "V2_exp", "V2_H1", "V2_H2", "V2_x11", "V2_corenonwire", "V2_nonwire", "V2_nonwire_x11", "V2_bench", "V4", "V9", "V11"): r[k] = np.nan
            r["V2_n"] = r["V2_core_n"] = r["V2_nonwire_n"] = r["n_coded"] = r["n_foreign"] = 0
        r["V10"], r["V10_n"] = v10.get((o, iss), (np.nan, 0))
        rows.append(r)
cells = pd.DataFrame(rows)
cells.to_csv(os.path.join(pf.P, "data/coded/following_cells.csv"), index=False)

per = cells[(cells.tier != "core") & cells.cell_kept].copy()
# ---------------------------------------------------------------- T1 validation (X10)
sr = json.load(open(os.path.join(pf.P, "data/coded/stability_report.json"))); sr1 = json.load(open(os.path.join(pf.P, "data/coded/stability_report_v1.json")))
rm = json.load(open(os.path.join(pf.P, "data/coded/rule_model_check.json")))["all"]
_alp = os.path.join(pf.P, "data/coded/agent_label_check.json"); al = json.load(open(_alp)) if os.path.exists(_alp) else None
_ccp = os.path.join(pf.P, "data/raw/sim/contamination_check.json"); cc = json.load(open(_ccp)) if os.path.exists(_ccp) else None
def a(x): return pf.fmt(x, 3).replace("0.", ".") if x is not None and not (isinstance(x, float) and np.isnan(x)) else "—"
T1 = {"label": "T1", "title": "Validation of the Coding Under the Model-Stability Protocol", "answers": ["RQ1"],
      "columns": ["Variable", "Coded by", "Model stability α (3 passes, n = 300)", "Prompt-variant α", "Rule-vs-model α (n)", "Meets .80 floor"],
      "rows": [
       ["V2/V7 frame", "model", a(sr["frame"]["alpha_passes_1_3"]), a(sr["frame"]["alpha_pass1_vs_variant"]), "—", "yes"],
       ["Foreign story (C4)", "rule, else model", a(sr["binary"]["foreign_story"]["alpha_passes_1_3"]), a(sr["binary"]["foreign_story"]["alpha_pass1_vs_variant"]), f"{a(rm['foreign_story']['alpha'])} ({rm['foreign_story']['rule_decides']:,})", "yes, after one revision"],
       ["V4 wire credit", "rule", a(sr["binary"]["wire_credit"]["alpha_passes_1_3"]), a(sr["binary"]["wire_credit"]["alpha_pass1_vs_variant"]), f"{a(rm['wire_credit']['alpha'])} ({rm['wire_credit']['rule_decides']:,})", "yes"],
       ["V11 national-agency credit", "rule", a(sr["binary"]["national_agency_credit"]["alpha_passes_1_3"]), a(sr["binary"]["national_agency_credit"]["alpha_pass1_vs_variant"]), f"{a(rm['national_agency_credit']['alpha'])} ({rm['national_agency_credit']['rule_decides']:,})", "yes"],
       ["V9 staff foreign byline", "rule, else model", a(sr["binary"]["staff_foreign_byline"]["alpha_passes_1_3"]), a(sr["binary"]["staff_foreign_byline"]["alpha_pass1_vs_variant"]), f"{a(rm['staff_foreign_byline']['alpha'])} ({rm['staff_foreign_byline']['rule_decides']:,})", "no — exploratory (X12)"],
       ["Agent frame labels vs coder (300 written-out proposals)", "agents / model", f"{a(al['alpha'])} (agents vs coder, n = {al['n']})" if al else "pending (P5)", "—", "—", ("no — coder frames on written-out proposals (plan P5 step 6)" if not al["meets_floor"] else "yes") if al else "pending (P5)"],
       ["Agent recall of sampled outlet headlines (contamination check)", "agents", f"recall at 0.8 similarity = {pf.fmt(cc['recall_at_0.8'], 2)} (n = {cc['n']}; mean similarity to the true headline {pf.fmt(cc['mean_similarity_true'], 3)}, to a random one {pf.fmt(cc['mean_similarity_random'], 3)})" if cc else "pending (P5)", "—", "—", "—"]],
      "note": (f"No human coder took part (deviation X10). Model stability is Krippendorff's α (nominal) across three fresh-context passes of the model coder "
               f"({sr['model']}, prompt version 2) on a random reliability sample of 300 articles stratified by tier; all three passes agreed on {sr['frame']['all_three_agree']} of 300 frames. "
               f"Prompt-variant α compares pass 1 with a reworded prompt. The full coding pass agreed with pass 1 of the reliability sample at α = {a(rm.get('frame_all_pass_vs_reliability_v2_p1', {}).get('alpha'))} (n = 300). "
               f"Rule-vs-model α is the agreement between the fixed credit and dateline rules and the model coder on every story the rules decide (n in parentheses, of 3,121). "
               f"The foreign-story wording was revised once under the plan's if_below rule (first wording α = {a(sr1['binary']['foreign_story']['alpha_passes_1_3'])}). "
               f"Wire credit excludes the 49 Washington Post syndicated copies coded 1 by URL rule (X11) from the rule-vs-model count. "
               + (f"Agent frame labels: Krippendorff's α between the frame each simulation agent ({al['agent_model']}) gave its proposal and the model coder's frame for the headline and lead the agent wrote out for it; below the .80 floor, simulated framing is computed from the coder's frames on written-out proposals (plan P5 step 6). " if al else "")
               + (f"Contamination check: the agents were asked to recall sampled outlets' headlines for sampled dates; recall is the share recalled at a token-set similarity of 0.8 or more, with mean similarity to the true headline against a random headline of the same outlet and issue for comparison." if cc else "")),
      "stats": [{"name": "frame_stability_alpha", "value": f"α = {a(sr['frame']['alpha_passes_1_3'])} (3 passes, n = 300)", "p": None, "effect": None},
                {"name": "wire_rule_model_alpha", "value": f"α = {a(rm['wire_credit']['alpha'])} (n = {rm['wire_credit']['rule_decides']:,})", "p": None, "effect": None}]}

# ---------------------------------------------------------------- T2 following by tier × issue
def msd(x, nd=2):
    x = pd.Series(x).dropna()
    return f"{pf.fmt(x.mean(), nd)} ({pf.fmt(x.std(ddof=1), nd)})" if len(x) > 1 else (pf.fmt(x.mean(), nd) if len(x) else "—")
def mdn(x, nd=2):
    x = pd.Series(x).dropna(); return pf.fmt(x.median(), nd) if len(x) else "—"
T2rows = []
for tier in ("periphery", "semi-periphery"):
    for iss in pf.ISSUES:
        g = per[(per.tier == tier) & (per.issue == iss)]
        T2rows.append([tier.capitalize() if tier == "periphery" else "Semi-periphery", pf.ISSUE_NAMES[iss], str(len(g)), f"{int(g.n_coded.sum())}",
                       msd(g.V1), msd(g.V2), f"{mdn(g.V3a)} (events {int(g.V3a_n_events.sum()):,})", mdn(g.V3b, 0)])
    g = per[per.tier == tier]
    T2rows.append([tier.capitalize() if tier == "periphery" else "Semi-periphery", "All issues", str(len(g)), f"{int(g.n_coded.sum())}", msd(g.V1), msd(g.V2), f"{mdn(g.V3a)} (events {int(g.V3a_n_events.sum()):,})", mdn(g.V3b, 0)])
dropped = pf.dropped_cells()
T2 = {"label": "T2", "title": "Following at Three Levels by Tier and Issue", "answers": ["RQ1"],
      "columns": ["Tier", "Issue", "Cells (n, after the 20-story floor)", "Coded articles (n)", "Salience r (M, SD)", "Framing similarity (M, SD)", "Timing V3a (Mdn days)", "Timing V3b (Mdn weeks)"],
      "rows": T2rows,
      "note": ("Salience r is the Pearson correlation between the event-adjusted residuals of an outlet's weekly issue share and the core set's over the weeks both hold at least 5 stories "
               "(149 weeks, February 24, 2022, to December 31, 2024). The core set is the weekly mean of The New York Times, The Washington Post, The Guardian and BBC News over the core outlets present "
               "that week; The Washington Post is absent after March 4, 2024 (X7). Framing similarity is 1 minus the Jensen–Shannon distance between the cell's frame distribution and the pooled core "
               "sample's, minus its expected value over 1,000 random splits of the pooled articles at the observed sizes, so that 0 means indistinguishable from the core and negative values mean "
               "farther than sampling alone would give. Timing V3a is the negative median lag in days from the first core mention of a GDELT event to the outlet's first mention; lags above 14 days are "
               "censored; V3b is the negative lag in weeks of the peak cross-correlation of weekly shares (−4 to 4). "
               f"Dropped cells (fewer than 20 stories): {', '.join(pf.OUTLET_NAMES[o] + ' ' + pf.ISSUE_NAMES[i] for o, i in dropped)}. "
               "Cells with 20–49 stories were coded whole: bdnews24.com COP (33), New Sarawak Tribune COP (36), Tuko COP (33). "
               "V3a is reported only for cells with at least 10 matched events (37 of 52 kept cells); New Sarawak Tribune has no GDELT event mentions, so its three cells have no V3a value. Tiers by Gunaratne's index on World Bank 2022 data (X1): "
               "periphery = Bangladesh, Kenya, South Africa; semi-periphery = India, Malaysia, Nigeria."),
      "stats": []}
for tier in ("periphery", "semi-periphery"):
    g = per[per.tier == tier]
    T2["stats"].append({"name": f"{tier}_salience_mean", "value": f"M = {pf.fmt(g.V1.mean())}, SD = {pf.fmt(g.V1.std(ddof=1))}, n = {len(g)} cells", "p": None, "effect": None})
    T2["stats"].append({"name": f"{tier}_framing_mean", "value": f"M = {pf.fmt(g.V2.mean())}, SD = {pf.fmt(g.V2.std(ddof=1))}, n = {len(g)} cells", "p": None, "effect": None})
    T2["stats"].append({"name": f"{tier}_timing_median", "value": f"Mdn = {pf.fmt(g.V3a.median())} days, n = {int(g.V3a.notna().sum())} cells", "p": None, "effect": None})

# ---------------------------------------------------------------- T8 outlet credits (V4, V9 exploratory, V11)
T8rows = []
for tier in ("periphery", "semi-periphery", "core"):
    for o in [o for o in pf.OUTLETS if ("core" if pf.OUTLETS[o][0] == "core" else tiers[pf.OUTLETS[o][0]]) == tier]:
        g = cells[(cells.outlet == o) & cells.cell_kept]
        nf = int(g.n_foreign.sum()); nc = int(g.n_coded.sum())
        c = pf.codes(); k = c[(c.outlet == o)]; f = k[k.foreign_story == 1]
        T8rows.append([pf.OUTLET_NAMES[o], pf.OUTLETS[o][0] if tier != "core" else "Core", tier if tier != "core" else "—",
                       pf.fmt(index.get(pf.OUTLETS[o][0], np.nan)) if tier != "core" else "—", str(nc), str(nf), f"{nf/nc:.2f}" if nc else "—",
                       pf.fmt(f.wire_credit.mean()) if nf else "—", pf.fmt(f.staff_foreign_byline.mean()) if nf else "—", pf.fmt(f.national_agency_credit.mean()) if nf else "—"])
T8 = {"label": "T8", "title": "Foreign Stories, Wire Reliance, Correspondent Presence and National-Agency Credits by Outlet", "answers": ["RQ1"],
      "columns": ["Outlet", "Country", "Tier", "Index score", "Coded stories", "Foreign stories", "Foreign share", "Wire reliance V4", "Staff foreign byline V9 (exploratory)", "National-agency credit V11"],
      "rows": T8rows,
      "note": ("Shares are over the outlet's coded foreign stories across its kept issue cells. V4 counts credits to AP, AFP or Reuters in the byline, dateline or end note; no text-reuse rule was applied "
               "because no agency full texts were available (X4). The 49 Washington Post syndicated copies count as wire copy by URL rule (X11). V9 is exploratory (X12): its model self-consistency "
               "was .749. The index score is Gunaratne's (2001) weighted share of world GNP (55%) and world exports (45%) on 2022 World Bank data, in percent-share units (X1)."),
      "stats": []}
for tier in ("periphery", "semi-periphery", "core"):
    c = pf.codes(); k = c[c.tier == tier]; f = k[k.foreign_story == 1]
    T8["stats"].append({"name": f"{tier}_wire_reliance", "value": f"V4 = {pf.fmt(f.wire_credit.mean())} (foreign stories n = {len(f):,} of {len(k):,} coded)", "p": None, "effect": None})
    T8["stats"].append({"name": f"{tier}_staff_foreign_byline", "value": f"V9 = {pf.fmt(f.staff_foreign_byline.mean())} (n = {len(f):,}; exploratory)", "p": None, "effect": None})
    T8["stats"].append({"name": f"{tier}_national_agency", "value": f"V11 = {pf.fmt(f.national_agency_credit.mean())} (n = {len(f):,})", "p": None, "effect": None})

# ---------------------------------------------------------------- T9 checks
def tierrow(label, col, nd=2):
    return [label] + [msd(per[per.tier == t][col], nd) for t in ("periphery", "semi-periphery")]
T9rows = [tierrow("Salience r, whole period (main)", "V1"), tierrow("Salience r, first validation half", "V1_H1"), tierrow("Salience r, second validation half", "V1_H2"),
          tierrow("Salience r, core of three (without The Washington Post, X7 check)", "V1_core3"),
          tierrow("Salience r, mismatched-issue core series (benchmark)", "V1_bench"),
          tierrow("Framing similarity, whole period (main)", "V2"), tierrow("Framing similarity, first half", "V2_H1"), tierrow("Framing similarity, second half", "V2_H2"),
          tierrow("Framing similarity without the 49 headline-only Post copies (X11)", "V2_x11"),
          tierrow("Framing similarity against wire-credited core stories removed (A22 check)", "V2_corenonwire"),
          tierrow("Framing similarity, non-wire stories only (both samples)", "V2_nonwire"),
          tierrow("Framing similarity, mismatched-issue core sample (benchmark)", "V2_bench"),
          tierrow("Timing V3a (Mdn days), whole period (main)", "V3a"), tierrow("Timing V3a, first half", "V3a_H1"), tierrow("Timing V3a, second half", "V3a_H2"),
          tierrow("Timing V3a, core first mentions permuted across events (benchmark)", "V3a_bench"),
          tierrow("Timing V3b (weeks), whole period", "V3b", 2), tierrow("Timing V3b, mismatched-issue core series (benchmark)", "V3b_bench", 2),
          tierrow("Own-country share of issue-story titles V10", "V10")]
T9 = {"label": "T9", "title": "Checks on the Following Measures by Tier", "answers": ["RQ1"],
      "columns": ["Measure and check", "Periphery M (SD)", "Semi-periphery M (SD)"], "rows": T9rows,
      "note": ("Means over kept outlet × issue cells (periphery 26, semi-periphery 26). Halves: the climate issue splits at June 8, 2023 (COP27 period first, COP28 second); Ukraine at "
               "August 13, 2023; Gaza at May 19, 2024 within the war's period from October 7, 2023. The mismatched-issue benchmark pairs each cell with the core series or core sample of a "
               "different issue (Ukraine with Gaza, Gaza with COP, COP with Ukraine). The timing benchmark shuffles the core first-mention times across the issue's events (fixed seed). "
               "The check with wire-credited core stories removed applies to framing only: census story records carry no credit codes, so salience and timing cannot be recomputed on a "
               "wire-free core. V10 is computed on story titles, since the census holds no article text."),
      "stats": []}

# ---------------------------------------------------------------- F1 weekly issue shares
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
s = pf.weekly_series(); cs = pf.core_series()
fig, axes = plt.subplots(3, 1, figsize=(8, 8.5), sharex=False)
for ax, iss in zip(axes, pf.ISSUES):
    c = cs[cs.issue == iss].set_index("week").core_share.reindex(W)
    ax.plot(range(len(W)), c.values * 100, color="#222222", lw=1.6, label="Core (mean of four outlets)")
    for tier, col in (("periphery", "#d95f02"), ("semi-periphery", "#1b9e77")):
        outs = [o for o in pf.OUTLETS if pf.OUTLETS[o][0] != "core" and tiers[pf.OUTLETS[o][0]] == tier and (o, iss) in pf.kept_cells()]
        t = s[(s.issue == iss) & s.outlet.isin(outs)].groupby("week").share.mean().reindex(W)
        ax.plot(range(len(W)), t.values * 100, color=col, lw=1.2, label=f"{tier.capitalize()} (mean of outlets)")
    ax.set_title(pf.ISSUE_NAMES[iss], loc="left", fontsize=10); ax.set_ylabel("% of the week's stories")
    ticks = [i for i, w in enumerate(W) if w[5:7] in ("01", "07") and w[8:10] <= "07"]
    ax.set_xticks(ticks); ax.set_xticklabels([W[i][:7] for i in ticks], fontsize=8)
axes[0].legend(fontsize=8, frameon=False); fig.tight_layout()
d = os.path.join(pf.P, "results", run_id, "figures"); os.makedirs(d, exist_ok=True)
fig.savefig(os.path.join(d, "f1.svg")); fig.savefig(os.path.join(d, "f1.png"), dpi=150)
F1 = {"label": "F1", "title": "Weekly Issue Shares, Core and Peripheral Outlets", "file": "figures/f1.svg",
      "note": "Weekly share of each outlet's stories on the issue, averaged over the outlets of a tier (kept cells) and over the core outlets present that week; weeks with fewer than 5 stories excluded."}

# ---------------------------------------------------------------- descriptives and summary
desc = [{"name": "coded_stories", "value": int(len(pf.codes())), "unit": "stories"},
        {"name": "coded_peripheral", "value": int((pf.codes().tier != "core").sum()), "unit": "stories"},
        {"name": "coded_core", "value": int((pf.codes().tier == "core").sum()), "unit": "stories"},
        {"name": "kept_cells_peripheral", "value": int(len(per)), "unit": "cells"},
        {"name": "dropped_cells", "value": len(dropped), "unit": "cells"},
        {"name": "weeks", "value": len(W), "unit": "weeks"},
        {"name": "events_peripheral", "value": int(per.V3a_n_events.sum()), "unit": "outlet-events"}]
summary = f"""# {run_id} — P1 describe following (RQ1)

Cell dataset: data/coded/following_cells.csv ({len(cells)} outlet × issue rows; {len(per)} kept peripheral cells).
T1 validation (X10), T2 following by tier and issue, T8 outlet credits, T9 checks, F1 weekly shares.

Periphery: salience r M = {pf.fmt(per[per.tier=='periphery'].V1.mean())}; framing M = {pf.fmt(per[per.tier=='periphery'].V2.mean())}; timing Mdn = {pf.fmt(per[per.tier=='periphery'].V3a.median())} days.
Semi-periphery: salience r M = {pf.fmt(per[per.tier=='semi-periphery'].V1.mean())}; framing M = {pf.fmt(per[per.tier=='semi-periphery'].V2.mean())}; timing Mdn = {pf.fmt(per[per.tier=='semi-periphery'].V3a.median())} days.
Wire reliance V4 by tier: periphery {pf.fmt(per[per.tier=='periphery'].V4.mean())}, semi-periphery {pf.fmt(per[per.tier=='semi-periphery'].V4.mean())} (cell means).
Dropped cells: {dropped}. New Sarawak Tribune: no GDELT event mentions (V3a missing, 3 cells).
"""
pf.finish_run(run_id, SCRIPT, INPUTS, [T1, T2, T8, T9], [F1], desc, summary, started, DEV,
              notes="Plan T1 columns adapted to X10 (no human coders). T8 and T9 are descriptive tables beyond the plan's shells (same measures, no test).")
