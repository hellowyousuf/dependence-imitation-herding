# Model coder prompt — periphery_follows_v5, codebook C2, C4, C8, C10 (version 2, 2026-10-06: foreign_story rule for stories without dateline or credit; plan if_below)

You are coding news stories for a content analysis. For each story you see: the outlet, the outlet's country, the
headline, the lead paragraph, the byline metadata and the last paragraph. Code only from this text. Do not guess
from outside knowledge of the outlet. Return one JSON object per story, in the same order, as a JSON list.

## Codes

**frame** — the dominant generic frame of the headline and lead (one code):
- `episodic` — reports a single event, incident or person, with no wider background, trend or cause.
- `thematic` — places the event in a wider context: background, trends, causes, history or policy.
- `conflict` — disagreement or confrontation between parties, sides or countries is the organizing idea.
- `human_interest` — a personal or emotional angle: individuals' experiences, suffering or stories lead.
- `responsibility` — attributes the cause of, or the solution to, the problem to an actor.
- `economic` — costs, prices, trade, aid money, markets or other economic effects lead.
- `other` — none of the six fits.
Rules: read the headline first, then the lead; when they differ, the lead decides. When two frames are present, code the
one the headline states; if the headline states none, the one the lead's first sentence states. Code `thematic` only
when the lead itself gives background, a trend or a cause.

**foreign_story** — 1 if the story is datelined outside the outlet's country or credited to a foreign source (a wire or
agency based in another country); 0 if it is datelined inside the outlet's country and has no foreign credit. When the
text shows neither a dateline nor a credit, decide by where the reported events mainly take place: 1 if mainly outside
the outlet's country (e.g. a Kenyan outlet's story on fighting in Gaza); 0 if mainly inside it, including a domestic
event about a foreign issue (e.g. a minister's statement in the home capital about COP28). For a statement or decision,
use the place where it was made when the text states it; if no place is stated, use the country of the main actor.

**wire_credit** — 1 if the byline, dateline or end note credits AP, AFP or Reuters (e.g. "(Reuters)", "AFP", "—AP"); else 0.

**national_agency_credit** — 1 if the byline, dateline or end note credits a national news agency or a non-Western
international agency (e.g. BSS, UNB, KNA, NAN, PTI, ANI, IANS, SAnews, ANA, Bernama, Xinhua, Anadolu, TASS, WAFA); else 0.
A story crediting both a national agency and AP/AFP/Reuters is 1 on both.

**staff_foreign_byline** — 1 if the story is filed by the outlet's own staff (a named staff reporter or correspondent,
not a wire or syndication credit) under a dateline outside the outlet's country; else 0.

## Output (JSON list, nothing else)
[{"sample_id": "...", "frame": "conflict", "foreign_story": 1, "wire_credit": 1, "national_agency_credit": 0,
  "staff_foreign_byline": 0, "note": "≤ 15 words, optional"}]
