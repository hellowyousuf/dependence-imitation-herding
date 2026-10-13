# Simulation records

| File | What it holds |
|---|---|
| `p5_proposals.zip` | 112,536 agent proposals (18 outlets × 1,042 days × 2 feeds × 3 samples). Each proposal lists item ids from the day's feed with a priority and a frame. Also: wire-item frame labels (`wire_frames/`), 300 written-out proposals with model-written headline and lead (`written_out_proposals.jsonl`), the written-out sample for simulated framing (`written_out_cells.jsonl`), and run records. Outputs of Qwen3-14B (Apache 2.0) via vLLM 0.31 on Google Colab (NVIDIA RTX PRO 6000 Blackwell), temperature 0.7. |
| `outlets.json` | The 18 agents: code, outlet, country, audience used in the persona, daily issue-story counts in the fitting half, wire reliance W and correspondent presence C. |
| `feed_events.jsonl` | Daily GDELT event lines the agents read. |
| `feed_core.jsonl`, `feed_wire.jsonl` | Core and wire feed items: id, date, kind, issue. Headline text removed. |
| `pilot.json` | Pilot dates. |
| `contamination_sample.json` | The 100 sampled stories of the recall check: id, outlet, issue, date. Headlines removed. |
| `contamination_check.json` | The agents' recall attempts and similarity scores. |
| `_cache/p5_cache.json` | Per-configuration, per-seed simulation records and errors written by `p5_simulation.py`. |

For each result table, the command, runtime and hardware are listed in the top-level `README.md`.
