# P5 step 1 — your Colab run (proposal pass), step by step

Plan P5 steps 1–2 (plan revision 5; A11, A19, A24, A26). Everything below runs under your Google account. The build has
prepared the files; you run the notebook; then you say `data ready P5` and the build registers the outputs and runs the
CPU rule step (`p5_simulation.py`).

## 0 · Event source — DONE October 6, 2026 (D34 registered; feed_events.jsonl built: the 200 most-mentioned events per day, issue-tagged by the A31 rules)
The plan feed holds GDELT event records. The manifest has no complete event-attributes file (`g6a_event_attributes_PARTIAL_not_used.csv`
is partial and unregistered). In BigQuery, run the **G6a** query of `data/analysis/gdelt_bigquery.sql` (the `events_small`
table filtered to the event ids of `periphery.story_events`) and save it as `data/raw/gdelt/g6a_event_attributes.csv`
(columns: GLOBALEVENTID, SQLDATE, Actor1CountryCode, Actor2CountryCode, EventCode, EventRootCode, QuadClass, IsRootEvent,
NumMentions, ActionGeo_CountryCode, ActionGeo_FullName). Say so in chat (prompt `B` registers it as D34), and the build
re-runs `p5_build_feeds.py` to write `feed_events.jsonl`. The notebook refuses to start without it.

## 1 · Upload to Google Drive
Create `MyDrive/periphery_sim/` and upload from `data/analysis/sim/`:
`feed_core.jsonl` (96,439 core headlines, outlet names stripped), `feed_wire.jsonl` (7,111 wire headlines), `feed_events.jsonl` (35 MB), `outlets.json` (18 agents P01–P18: country, audience, n_i, W_i, C_i — no names), `pilot.json`,
`contamination_sample.json` (100 coded peripheral stories for the recall check).
Do **not** upload `outlet_codes_PRIVATE.json` (it maps codes to outlet names; it stays in the project).

## 2 · Open `data/analysis/p5_colab_proposals.ipynb` in Colab
Runtime → A100 (bf16 Qwen3-14B) if your Colab plan offers one; on a T4 set `MODEL = 'Qwen/Qwen3-8B-AWQ'` and `QUANT = 'awq'`
(plan A11: 8B if only a T4). Run the cells in order:
- **0, 0b, 0c** — setup, model, feeds, prompt builder (cell 0 writes `run_record.json`: model id, vLLM version, GPU, settings).
- **1 · Contamination check** — 100 recall prompts; writes `contamination_check.json` (recall at similarity ≥ .8 vs chance).
- **2 · Pilot** — `MODE = 'pilot'`: March 2022, all 18 agents, both feeds, 3 samples (≈ 3,300 calls). It prints calls/s, mean
  prompt tokens and the projected hours for the full pass, and writes `pilot_report.json`. **Stop here and paste the printed
  line and `contamination_check.json`'s first four numbers in chat.** The build reads them and says whether `FEED_CAP`
  (core 80 / wire 40 / events 40 per day) or `MAX_TOKENS` changes before the full pass (A26). If the projection exceeds the
  time you have, the cap comes down.
- **3 · Full pass** — set `MODE = 'full'` and run the same cell. 1,042 days × 2 feeds × 18 agents × 3 samples = 112,536
  calls. It checkpoints one file per day and feed under `proposals/A/` and `proposals/B/` and resumes after a disconnect:
  re-run cells 0, 0b, 0c and the pass cell again; finished days are skipped.
- **4 · Wire frame labels** — one call per day (≈ 1,000): the frame of each wire headline (the dependence rule publishes
  wire copy with the wires' frames).
- **5 · Written-out proposals** — 300 sampled proposals get a headline and lead paragraph (for the agent-label check; the
  build's model coder codes them afterwards with the same codebook, floor .80).
- **6 · Package** — zips `proposals/`, `wire_frames/`, `written_out_proposals.jsonl`, `contamination_check.json`,
  `pilot_report.json`, `run_record.json` into `p5_proposals.zip`.

## 2b · After the first full pass (October 7, 2026): two more cells before packaging
- **3r · Repair** — 24% of calls were cut off at the 700-token limit and parsed as empty; 3r regenerates exactly those with a 1,600-token limit (resumable; ~2–4 h on the G4).
- **5b · Fallback** — the agent frame labels failed the .80 floor against the model coder (alpha .232 on the 300 written-out proposals), so the plan's fallback applies: 5b writes out 50 proposals per outlet × issue from the held-out half (≈ 2,700 short calls) for the model coder.
Run cells 0, 0b, 0c, then 3r, then 4 and 5 again are NOT needed; run 5b, then 6, and replace the zip.

## 3 · Bring it back
Copy `p5_proposals.zip` to `data/raw/sim/p5_proposals.zip` in the project folder and say **`data ready P5`**. The build then
registers the zip (D35) and its unpacked files, codes the 300 written-out proposals, runs `p5_simulation.py` (8
configurations × 20 seeds, parameters fitted on the first half of each issue, V8 on the second half), and writes T4 and F3.

## What the run records (keep for the Method)
Exact model id and quantization, vLLM version, GPU, temperature .7, top-p .95, seed base 20261006, the feed cap, the
dates of the run (`run_record.json`), the contamination recall (a limit if above chance), the pilot throughput.
