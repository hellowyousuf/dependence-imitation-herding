# Model coder prompt — periphery_follows_v5, prompt-variation check (X10; same codes, reworded, categories reordered)

You will classify news stories for a research content analysis. Each story comes with its outlet, the outlet's home
country, a headline, an opening paragraph (lead), byline information and the closing paragraph. Base every decision on
this text alone; do not draw on what you know about the outlet. Answer with a JSON list holding one object per story,
in the order given.

## What to decide

**frame** — which single generic frame organizes the headline and lead? Choose one:
- `conflict` — the story is built around a dispute, clash or confrontation between parties, sides or states.
- `economic` — money, prices, costs, trade, markets, aid budgets or other economic effects are what the story leads with.
- `human_interest` — the story leads with particular people: their experiences, feelings, suffering or personal stories.
- `responsibility` — the story assigns blame for the problem, or the task of solving it, to a government, group or person.
- `thematic` — the story sets the news in a broader frame: background, causes, a trend, history or policy.
- `episodic` — the story reports one event, incident or person and gives no wider background, trend or cause.
- `other` — none of these describes the headline and lead.
How to decide: start with the headline, then read the lead; if the two point to different frames, follow the lead. If
two frames appear, take the one the headline expresses; if the headline expresses none, take the one in the lead's first
sentence. Use `thematic` only when the lead itself supplies background, a trend or a cause.

**foreign_story** — 1 when the story carries a dateline outside the outlet's home country or is credited to a foreign
source; otherwise 0.

**wire_credit** — 1 when Reuters, AFP or AP (Associated Press) is credited in the byline, the dateline or a closing
credit line; otherwise 0.

**national_agency_credit** — 1 when a national news agency or a non-Western international agency is credited in the
byline, the dateline or a closing credit line (for example BSS, UNB, KNA, NAN, PTI, ANI, IANS, SAnews, ANA, APA,
Bernama, Xinhua, Anadolu, TASS, WAFA); otherwise 0. A story may be 1 on both credit codes.

**staff_foreign_byline** — 1 when the outlet's own named staff reporter or correspondent (not a wire or syndication
credit) files from a dateline outside the outlet's home country; otherwise 0.

## Output (JSON list only)
[{"sample_id": "...", "frame": "economic", "foreign_story": 0, "wire_credit": 0, "national_agency_credit": 0,
  "staff_foreign_byline": 0, "note": "up to 15 words, optional"}]
