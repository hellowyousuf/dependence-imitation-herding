import json
cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s})

md("""# P5 step 1 — proposal pass (Qwen3-14B, vLLM, Google Colab)

Plan P5 steps 1–2 (plan revision 5; A11, A19, A24, A26). The 18 peripheral outlets are assistant agents without names (codes P01–P18, country and audience only). Each agent reads one day's feed — GDELT event lines, wire headlines and (feed A only) core headlines, all stripped of outlet names, at their observed dates — and its own proposals of the previous seven days, and returns the items it would publish with a priority (1–5) and a codebook frame. Three samples per outlet-day, two feeds (A with core stories, B without), about 112,000 calls. Outputs are checkpointed to Google Drive and the run resumes where it stopped.

Order of work: **0 setup → 1 contamination check → 2 pilot month → (report to the build; fix FEED_CAP if asked) → 3 full pass → 4 wire frame labels → 5 written-out proposals (300) → 6 package.**

Runtime: an A100 (40 GB) runs Qwen3-14B in bf16; a T4 runs `Qwen/Qwen3-8B-AWQ` (plan: 8B if only a T4 is available) — set MODEL accordingly. Record the exact model id, the vLLM version, dtype/quantization, temperature and the dates in `run_record.json` (cell 0 writes it).""")

code("""#@title 0 · Setup — mount Drive, install vLLM, configuration
from google.colab import drive; drive.mount('/content/drive')
!pip -q install "vllm>=0.9" >/dev/null 2>&1 || pip -q install vllm
import os, json, re, glob, random, hashlib, time, datetime as dt
DRIVE = '/content/drive/MyDrive/periphery_sim'           # upload the sim/ folder here: feed_core.jsonl, feed_wire.jsonl, feed_events.jsonl, outlets.json, pilot.json, contamination_sample.json
OUT = f'{DRIVE}/proposals'; os.makedirs(OUT, exist_ok=True)
MODEL = 'Qwen/Qwen3-14B'                                  # A100: Qwen/Qwen3-14B (bf16). T4 only: 'Qwen/Qwen3-8B-AWQ' (plan A11)
QUANT = None                                              # 'awq' for the AWQ checkpoint
TEMPERATURE = 0.7; MAX_TOKENS = 700; SEED_BASE = 20261006
FEED_CAP = {'core': 80, 'wire': 40, 'event': 40}          # items per day per kind shown to an agent; the pilot fixes these (A26)
SAMPLES = 3; FEEDS = ['A', 'B']                           # A = with core headlines, B = without (A26)
PERIOD = ('2022-02-24', '2024-12-31')
import vllm; print('vllm', vllm.__version__)
json.dump({'model': MODEL, 'quantization': QUANT, 'vllm': vllm.__version__, 'temperature': TEMPERATURE, 'max_tokens': MAX_TOKENS, 'feed_cap': FEED_CAP, 'samples': SAMPLES,
           'seed_base': SEED_BASE, 'started': dt.datetime.utcnow().isoformat()+'Z', 'gpu': os.popen('nvidia-smi --query-gpu=name --format=csv,noheader').read().strip()},
          open(f'{DRIVE}/run_record.json', 'w'), indent=1)
print(open(f'{DRIVE}/run_record.json').read())""")

code("""#@title 0b · Load the model and the feeds
from vllm import LLM, SamplingParams
llm = LLM(model=MODEL, quantization=QUANT, dtype='auto', max_model_len=16384, enable_prefix_caching=True, gpu_memory_utilization=0.92, seed=SEED_BASE)
tok = llm.get_tokenizer()
def load_jsonl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
core = load_jsonl(f'{DRIVE}/feed_core.jsonl'); wire = load_jsonl(f'{DRIVE}/feed_wire.jsonl'); events = load_jsonl(f'{DRIVE}/feed_events.jsonl')
outlets = json.load(open(f'{DRIVE}/outlets.json')); pilot = json.load(open(f'{DRIVE}/pilot.json'))
assert events, 'feed_events.jsonl is missing or empty — the plan feed needs GDELT event records (prompt B registers the G6a export)'
from collections import defaultdict
byday = {'core': defaultdict(list), 'wire': defaultdict(list), 'event': defaultdict(list)}
for x in core: byday['core'][x['date']].append(x)
for x in wire: byday['wire'][x['date']].append(x)
for x in events: byday['event'][x['date']].append(x)
days = []; d = dt.date.fromisoformat(PERIOD[0])
while d <= dt.date.fromisoformat(PERIOD[1]): days.append(d.isoformat()); d += dt.timedelta(days=1)
print(len(core), 'core ·', len(wire), 'wire ·', len(events), 'events ·', len(days), 'days ·', len(outlets), 'outlets')""")

code("""#@title 0c · Prompt builder (the day's feed is the shared prefix so vLLM's prefix cache serves all 54 calls of a day)
FRAMES = 'episodic, thematic, conflict, human_interest, responsibility, economic, other'
CODEBOOK = ('Frames (one per item): episodic = a single event, incident or person with no wider background; thematic = background, trend, cause, history or policy; '
            'conflict = disagreement or confrontation between parties is the organizing idea; human_interest = a personal or emotional angle leads; '
            'responsibility = attributes the cause of or the solution to the problem to an actor; economic = costs, prices, trade, aid money or markets lead; other = none fits.')
def day_feed(date, feed, rng):
    parts = []
    for kind, head in (('event', 'World events recorded today'), ('wire', 'Wire-service stories available to you today (any may be republished)'), ('core', 'Stories published today by major international news outlets')):
        if kind == 'core' and feed == 'B': continue
        xs = list(byday[kind].get(date, []))
        if len(xs) > FEED_CAP[kind]: xs = rng.sample(xs, FEED_CAP[kind]); xs.sort(key=lambda x: x['id'])
        if not xs: continue
        parts.append(f'## {head} ({len(xs)})\\n' + '\\n'.join(f"[{x['id']}] {x['text']}" for x in xs))
    return f'# Daily feed for {date}\\n\\n' + '\\n\\n'.join(parts)
def persona(o):
    return (f"You are the foreign-news editor of {o['audience']} (country: {o['country']}). You decide which items from today's feed your outlet would publish for its readers. "
            'You know nothing about which outlet produced any feed item. Judge newsworthiness for your audience only.')
def own_history(o, date, feed, store):
    lines = []
    d0 = dt.date.fromisoformat(date)
    for k in range(7, 0, -1):
        dd = (d0 - dt.timedelta(days=k)).isoformat()
        prev = store.get((o['code'], dd, feed))
        if prev: lines.append(f"{dd}: " + '; '.join(f"{p['id']} (p{p['priority']}, {p['frame']})" for p in prev[:12]))
    return ('## Your own proposals of the previous seven days\\n' + '\\n'.join(lines)) if lines else '## Your own proposals of the previous seven days\\n(none yet)'
def build_messages(o, date, feed, store, rng):
    system = persona(o) + ' ' + CODEBOOK
    user = (day_feed(date, feed, rng) + '\\n\\n' + own_history(o, date, feed, store) +
            '\\n\\n## Task\\nList the feed items you would publish today, in order of priority. For each give the item id, a priority from 5 (lead story) to 1 (brief), and the frame you would give it from the list: '
            + FRAMES + '. Choose as many or as few items as your outlet would run on these topics today (typically 0–15). Answer with a JSON list only: '
            '[{"id": "c-2022-02-24-33c6089f", "priority": 4, "frame": "conflict"}, ...]')
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
def render(messages):
    return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
def parse(text, valid_ids):
    m = re.search(r'\\[.*\\]', text, re.S)
    if not m: return []
    try: xs = json.loads(m.group(0))
    except Exception: return []
    out = []
    for x in xs if isinstance(xs, list) else []:
        if not isinstance(x, dict) or x.get('id') not in valid_ids: continue
        try: pr = int(x.get('priority', 3))
        except Exception: pr = 3
        fr = str(x.get('frame', 'other')).strip().lower().replace(' ', '_')
        out.append({'id': x['id'], 'priority': min(5, max(1, pr)), 'frame': fr if fr in FRAMES.split(', ') else 'other'})
    return out
def valid_ids_for(date, feed):
    ids = {x['id'] for x in byday['event'].get(date, [])} | {x['id'] for x in byday['wire'].get(date, [])}
    if feed == 'A': ids |= {x['id'] for x in byday['core'].get(date, [])}
    return ids
print(render(build_messages(outlets[0], days[10], 'A', {}, random.Random(1)))[:3000])""")

code("""#@title 1 · Contamination check (A26) — recall of sampled outlets' headlines, before the proposal pass
import difflib
sample = json.load(open(f'{DRIVE}/contamination_sample.json'))
prompts = [render([{'role': 'user', 'content': f"On {s['date']}, what headline did {s['outlet']} publish about {s['issue']}? Reply with the single most likely headline and nothing else."}]) for s in sample]
outs = llm.generate(prompts, SamplingParams(temperature=0.0, max_tokens=60, seed=SEED_BASE))
def sim(a, b): return difflib.SequenceMatcher(None, re.sub(r'\\W+', ' ', a.lower()).strip(), re.sub(r'\\W+', ' ', b.lower()).strip()).ratio()
rng = random.Random(SEED_BASE); res = []
for s, o in zip(sample, outs):
    ans = o.outputs[0].text.strip().split('\\n')[0]
    others = [t['headline'] for t in sample if t['outlet'] == s['outlet'] and t['issue'] == s['issue'] and t['sample_id'] != s['sample_id']] or [t['headline'] for t in sample if t['sample_id'] != s['sample_id']]
    res.append({'sample_id': s['sample_id'], 'answer': ans, 'sim_true': sim(ans, s['headline']), 'sim_random': sim(ans, rng.choice(others))})
rec = sum(r['sim_true'] >= 0.8 for r in res) / len(res); chance = sum(r['sim_random'] >= 0.8 for r in res) / len(res)
mean_true = sum(r['sim_true'] for r in res) / len(res); mean_rand = sum(r['sim_random'] for r in res) / len(res)
report = {'model': MODEL, 'n': len(res), 'recall_at_0.8': rec, 'chance_at_0.8': chance, 'mean_similarity_true': mean_true, 'mean_similarity_random': mean_rand, 'items': res, 'ts': dt.datetime.utcnow().isoformat()+'Z'}
json.dump(report, open(f'{DRIVE}/contamination_check.json', 'w'), indent=1)
print(f'recall ≥ .8: {rec:.3f} (chance {chance:.3f}); mean similarity true {mean_true:.3f} vs random {mean_rand:.3f}')""")

code("""#@title 2–3 · Proposal pass — PILOT (one month) or FULL; resumable; checkpoint per day and feed
MODE = 'pilot'  #@param ['pilot', 'full']
day_list = [d for d in days if pilot['pilot_start'] <= d <= pilot['pilot_end']] if MODE == 'pilot' else days
sp = SamplingParams(temperature=TEMPERATURE, top_p=0.95, max_tokens=MAX_TOKENS, seed=SEED_BASE)
store = {}   # (code, date, feed) -> proposals of sample 1 (own history uses sample 1, A24)
# reload history from existing checkpoints
for f in sorted(glob.glob(f'{OUT}/*/*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if r['sample'] == 1: store[(r['code'], r['date'], r['feed'])] = r['proposals']
t0 = time.time(); n_calls = 0; tok_in = 0
for date in day_list:
    for feed in FEEDS:
        path = f'{OUT}/{feed}/{date}.jsonl'
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rng = random.Random(f'{SEED_BASE}|{date}|{feed}')
        vids = valid_ids_for(date, feed)
        jobs, prompts = [], []
        for o in outlets:
            msgs = build_messages(o, date, feed, store, random.Random(f'{SEED_BASE}|{date}|{feed}'))  # same feed sample for every outlet that day
            p = render(msgs)
            for k in range(1, SAMPLES + 1):
                jobs.append((o['code'], k)); prompts.append(p)
        outs = llm.generate(prompts, sp)
        with open(path + '.tmp', 'w') as fh:
            for (code, k), o in zip(jobs, outs):
                props = parse(o.outputs[0].text, vids)
                rec = {'code': code, 'date': date, 'feed': feed, 'sample': k, 'proposals': props, 'n_raw': len(o.outputs[0].text), 'model': MODEL}
                fh.write(json.dumps(rec) + '\\n')
                if k == 1: store[(code, date, feed)] = props
        os.replace(path + '.tmp', path)
        n_calls += len(prompts); tok_in += sum(len(o.prompt_token_ids) for o in outs)
    if n_calls and n_calls % (len(outlets) * SAMPLES * len(FEEDS) * 5) == 0:
        el = time.time() - t0; print(f'{date}: {n_calls} calls, {el/60:.1f} min, {n_calls/el:.2f} calls/s, mean prompt tokens {tok_in/n_calls:.0f}')
el = time.time() - t0
print(f'{MODE}: {n_calls} calls in {el/60:.1f} min → {n_calls/max(el,1):.2f} calls/s; mean prompt tokens {tok_in/max(n_calls,1):.0f}; projected full pass {len(days)*len(FEEDS)*len(outlets)*SAMPLES/max(n_calls/max(el,1),1e-9)/3600:.1f} h')
if MODE == 'pilot':
    json.dump({'calls': n_calls, 'seconds': el, 'calls_per_s': n_calls/max(el,1), 'mean_prompt_tokens': tok_in/max(n_calls,1), 'feed_cap': FEED_CAP, 'model': MODEL}, open(f'{DRIVE}/pilot_report.json', 'w'), indent=1)""")

code("""#@title 4 · Wire frame labels — one call per day: the frame of each wire item (the dependence rule publishes wire copy with the wires' frames)
os.makedirs(f'{DRIVE}/wire_frames', exist_ok=True)
sp0 = SamplingParams(temperature=0.0, max_tokens=1200, seed=SEED_BASE)
todo = [d for d in days if byday['wire'].get(d) and not os.path.exists(f'{DRIVE}/wire_frames/{d}.json')]
for i in range(0, len(todo), 64):
    chunk = todo[i:i+64]; prompts = []
    for d in chunk:
        xs = byday['wire'][d]
        prompts.append(render([{'role': 'system', 'content': 'You code news headlines with a frame codebook. ' + CODEBOOK},
                               {'role': 'user', 'content': 'Give the frame of each headline. Answer with a JSON list only: [{"id": "...", "frame": "..."}].\\n' + '\\n'.join(f"[{x['id']}] {x['text']}" for x in xs)}]))
    outs = llm.generate(prompts, sp0)
    for d, o in zip(chunk, outs):
        lab = parse(o.outputs[0].text.replace('"priority"', '"p"'), {x['id'] for x in byday['wire'][d]})
        json.dump({x['id']: x['frame'] for x in lab}, open(f'{DRIVE}/wire_frames/{d}.json', 'w'))
print('wire frame files:', len(glob.glob(f'{DRIVE}/wire_frames/*.json')))""")

code("""#@title 5 · Written-out proposals — 300 sampled proposals get a headline and lead paragraph for the label check (plan P5 step 6)
rng = random.Random(SEED_BASE); allp = []
for f in sorted(glob.glob(f'{OUT}/A/*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        for p in r['proposals']: allp.append((r['code'], r['date'], r['feed'], r['sample'], p))
pick = rng.sample(allp, min(300, len(allp)))
texts = {x['id']: x['text'] for x in core + wire + events}
omap = {o['code']: o for o in outlets}
prompts = [render([{'role': 'system', 'content': persona(omap[c])}, {'role': 'user', 'content': f"Write the headline and the lead paragraph (2–3 sentences) your outlet would publish on {d} for this item: {texts.get(p['id'], '')}. Answer as JSON: {{\\"headline\\": \\"...\\", \\"lead\\": \\"...\\"}}"}]) for c, d, fd, k, p in pick]
outs = llm.generate(prompts, SamplingParams(temperature=TEMPERATURE, max_tokens=250, seed=SEED_BASE))
with open(f'{DRIVE}/written_out_proposals.jsonl', 'w') as fh:
    for (c, d, fd, k, p), o in zip(pick, outs):
        m = re.search(r'\\{.*\\}', o.outputs[0].text, re.S); w = {}
        try: w = json.loads(m.group(0)) if m else {}
        except Exception: w = {'raw': o.outputs[0].text}
        fh.write(json.dumps({'code': c, 'date': d, 'feed': fd, 'sample': k, 'id': p['id'], 'agent_frame': p['frame'], 'priority': p['priority'], 'headline': w.get('headline', ''), 'lead': w.get('lead', ''), 'raw': w.get('raw', '')}) + '\\n')
print('written-out proposals:', len(pick))""")

code("""#@title 6 · Package — one zip for the project (register with register_data.py)
json.dump(dict(json.load(open(f'{DRIVE}/run_record.json')), finished=dt.datetime.utcnow().isoformat()+'Z', proposal_files=len(glob.glob(f'{OUT}/*/*.jsonl'))), open(f'{DRIVE}/run_record.json', 'w'), indent=1)
!cd "{DRIVE}" && zip -qr p5_proposals.zip proposals wire_frames written_out_proposals.jsonl contamination_check.json pilot_report.json run_record.json
print('→', f'{DRIVE}/p5_proposals.zip')""")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("p5_colab_proposals.ipynb", "w"), indent=1)
print("notebook written")
