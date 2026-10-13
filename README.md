# Structural Dependence, Imitation or Herding? Code and data

Code, data and simulation records for the paper *Structural Dependence, Imitation or Herding? A Multi-Agent Simulation of Global Intermedia Agenda Setting* by Mohammad Yousuf and Arif Md Tareque Habib (University of New Mexico). Preprint: arXiv:[ARXIV ID]. Archive: Zenodo, DOI [ZENODO DOI].

## What the study is

News outlets in poorer countries cover the world much as the leading outlets of rich countries do. The study measured how closely 18 national outlets in Bangladesh, Kenya, South Africa, India, Malaysia and Nigeria followed four core outlets on the wars in Ukraine and Gaza and the COP27 and COP28 climate conferences, February 24, 2022, to December 31, 2024. It measured following at three levels: attention (salience), angle (framing) and timing. It then ran a simulation in which a language model acted as each outlet's editor. In that simulation, three mechanisms were switched on and off: dependence on wire agencies, imitation of prestigious outlets, and herding.

## Layout

```
code/         analysis scripts (data/analysis in the original project), prompts, codebook,
              make_workspace.py, rehydrate_mediacloud.py
data/         raw/ (World Bank, Media Cloud counts and ids, GDELT, fetch logs), sampling/, coded/,
              results/<run>/ (tables, figures, fits, run records), runs.jsonl
simulation/   agents' proposals (p5_proposals.zip), outlets.json, feeds, pilot, contamination check, cache
release_manifest.json   every file with sha256, source dataset id (D1-D35), licence, fields removed
```

## Reproduce the tables

Python 3.10 with the package versions in `code/analysis/environment.txt` (numpy 2.2.6, pandas 2.3.3, scipy 1.15.3, statsmodels 0.15.0, matplotlib 3.10.9).

```
python3 code/make_workspace.py
export PF_PROJECT=$PWD/workspace
python3 workspace/data/analysis/<script>.py
```

Each run writes a new folder under `workspace/results/`. Compare its `tables.json` with the released run named below.

| Paper table or figure | Command (script in `workspace/data/analysis/`) | Released run | Runtime | Hardware |
|---|---|---|---|---|
| Table 1, Figure 1, Tables S3, S4, S5 | `p1_describe_following.py` (needs the withheld story URLs and titles first; see below) | run_20261008_02 | 42 s | MacBook Air (Apple silicon), Linux aarch64 VM, Python 3.10.12 |
| Table 2 (H1 rows), Table S8 | `p2_tier_model.py` | run_20261006_02 | under 1 s | same |
| Table 2 (H2 rows, first falsifier), Table S9 | `p3_wire_model.py` | run_20261006_03 | 1 s | same |
| Table 2 (H3 rows, Holm decisions, second falsifier), Figure 2, Table S10 | `p4_stake_interaction.py` | run_20261009_01 | 1 s | same |
| Table S7 | `p6_rival_tests.py` | run_20261006_05 | 4 s | same |
| Table 3, Figure 3 | `p5_simulation.py` | run_20261012_01 | 6 s with the released cache | same |
| Table S6 | `p1b_source_check.py` | run_20261009_03 | 1 s | same |
| Tables S11, S12 | `p5b_sim_coverage.py` | run_20261009_02 | under 1 s | same |

Runtimes are the start-to-finish times in each run's `run.json`.

`p1_describe_following.py` matches stories by URL, and it reads titles for the own-country check. It therefore runs only after you restore the Media Cloud URLs and titles with `code/rehydrate_mediacloud.py` (your own key) and the GDELT page titles of `data/raw/gdelt/g3_bangladesh_census.csv` with query G3 in `code/analysis/gdelt_bigquery.sql` (your own Google Cloud project). The other seven commands run from the released files alone.

Tested on October 12, 2026, from a fresh copy of the released files. The seven commands that need no withheld input reproduced their released `tables.json` exactly, row for row. That includes `p5_simulation.py`, run once with the released cache and once with the cache deleted.

Table S2 states the simulation rules and holds no results. The agents' proposals were produced once, on Google Colab (NVIDIA RTX PRO 6000 Blackwell, vLLM 0.31, Qwen3-14B, temperature 0.7), by `code/analysis/p5_colab_proposals.ipynb`.

### The simulation reruns without a language model

The mechanisms are rules applied to the agents' recorded proposals. `p5_simulation.py` reads the proposals from `simulation/p5_proposals.zip` (unpacked by `make_workspace.py`) and applies the rules. With the released cache (`simulation/_cache/p5_cache.json`), it reproduces Table 3 in seconds. To recompute every configuration from the proposals, delete `workspace/data/analysis/sim/_cache/p5_cache.json` first. On the hardware above, that full run took about 20 minutes. It was run in chunks with `--budget 150`; the script saves its cache and exits with code 3 when the budget is spent, and a rerun resumes. It rebuilt all 299 cache entries identically.

## What is withheld and why

| Withheld | Why | How to regenerate |
|---|---|---|
| Article texts of the 18 outlets (headline, lead, byline, last paragraph) | Belong to the outlets; collected for analysis only | `fetch_public_pages.py` (public pages, robots.txt obeyed) from the sample in `data/sampling/sample_ranked.csv` after rehydration |
| *New York Times* and *Guardian* API texts | API terms | `fetch_core_texts.py` with your own `NYT_API_KEY` and `GUARDIAN_API_KEY` |
| *New York Times* and *Washington Post* leads from ProQuest | Library licence, no redistribution | Your own library access; `core_manual_list.py` writes the search list |
| Internet Archive copies | Third-party copies of outlet pages | `fetch_public_pages.py` (Wayback route) |
| Headlines and titles in every list, from Media Cloud or GDELT | Outlet content | Media Cloud: `code/rehydrate_mediacloud.py` with your own `MC_API_KEY`. GDELT: `code/analysis/gdelt_bigquery.sql` in Google BigQuery |
| Media Cloud story URLs | Media Cloud's terms do not cover redistribution of story content | `code/rehydrate_mediacloud.py` |
| Headline text in the simulation feeds (`feed_core`, `feed_wire`) | Core and wire headlines | Rehydrate, then run `p5_build_feeds.py` |

Coding from texts (`model_coder.py`, `code_rules.py`) needs the withheld texts and a Claude model. The released labels (`data/coded/`) let every table be recomputed without them.

## Differences from the project copy

- Fields removed: `title` and `url` from Media Cloud story lists, `title` from GDELT page lists, `url` and `fetched_from` from fetch logs, `note` (the coder's free text) from coder label files, `text` from the core and wire feeds, and `headline` from the contamination sample. `release_manifest.json` lists each one.
- `simulation/outlets.json` has an added `outlet` field. It maps codes P01–P18 to outlets by the rule in `p5_build_feeds.py`: the 18 outlets sorted by domain. `p5_simulation.py` and `p5b_sim_coverage.py` read it. In the original project they read a separate code file, which is not released.
- Because the feeds' `text` field was removed, their sha256 differs from the one recorded in `run.json`. The simulation does not read that field.

## Decision codes in the run records

Run records (`run.json`, `runs.jsonl`), result notes and script comments refer to processing decisions by short codes. Each code stands for one of these:

| Code | Decision |
|---|---|
| X1 | Tiers by Gunaratne's index on 2022 World Bank data; the three higher-scoring countries form the semi-periphery; Nigeria's exports from the balance-of-payments series |
| X3, X4 (X4a, X4b) | Texts: headline, lead, byline, dateline and credits from the outlets' public pages (robots.txt obeyed), and from the *New York Times* and *Guardian* APIs; wire reliance from credits only |
| X5 | Bangladesh outlets (*The Daily Star*, *bdnews24.com*, *New Age*) chosen purposively; their weekly series from GDELT page titles |
| X6 | Malaysian outlets by the outlet-selection rule; Bernama counted as the national agency |
| X7 | Core series as the weekly mean of the core outlets present; *The Washington Post* absent after March 4, 2024 |
| X8 | *New Sarawak Tribune* stories read from Internet Archive copies |
| X9 | *New York Times* and *Washington Post* leads from library databases |
| X10 | Coding by fixed rules and the model coder under the stability protocol; no human coding |
| X11 | The 49 syndicated *Washington Post* copies kept as headline-only records, wire credit by URL; frame tests repeated without them |
| X12 | Correspondent presence (staff foreign byline) exploratory, below the .80 stability floor |
| X13 | *Times of India* weekly total from Media Cloud's domain total scaled by the GDELT host share |
| X14 | Local stake coded at the issue level only |
| X15 | RQ2 decided by the full rule in the paper's Method, including the bootstrap condition |

## Licences

| Folder | Licence |
|---|---|
| `code/` scripts | MIT (`LICENSE`) |
| `code/` prompts and codebook; `data/`; `simulation/` data | CC BY 4.0 (`LICENSE-DATA`) |
| `simulation/p5_proposals.zip`, `simulation/contamination_check.json` | Outputs of Qwen3-14B (Apache License 2.0); released under CC BY 4.0 |
| World Bank data | CC BY 4.0, World Bank |
| GDELT-derived files | GDELT open data; cite Leetaru and Schrodt (2013) |
| Media Cloud counts and ids | Media Cloud Terms of Use; cite Roberts et al. (2021) |

## How to cite

Cite the paper and this archive. `CITATION.cff` holds both; GitHub shows them under "Cite this repository".

Yousuf, M., and Habib, A. M. T. (2026). Structural dependence, imitation or herding? A multi-agent simulation of global intermedia agenda setting. arXiv:[ARXIV ID]. Code and data: Zenodo, https://doi.org/[ZENODO DOI].
