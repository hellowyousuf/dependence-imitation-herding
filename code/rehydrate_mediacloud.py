#!/usr/bin/env python3
"""Recover the URL and title of every released Media Cloud story from its id, with your own Media Cloud key.
The release holds Media Cloud story ids, dates, outlets and issues, not URLs or titles (Media Cloud's terms give no
permission to redistribute story content). Run inside the workspace made by code/make_workspace.py:

  pip install mediacloud
  export MC_API_KEY="<your key from search.mediacloud.org>"
  python3 code/rehydrate_mediacloud.py workspace

It writes data/raw/mediacloud/<file>.rehydrated.jsonl next to each story file. To rebuild the simulation feeds'
headline text, move the rehydrated files over the originals and run data/analysis/p5_build_feeds.py; that script
then stops at the contamination sample, which needs the withheld article texts.
"""
import json, os, sys, time, glob
import mediacloud.api
W = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "workspace")
key = os.environ.get("MC_API_KEY") or sys.exit("set MC_API_KEY first")
S = mediacloud.api.SearchApi(key)
for path in sorted(glob.glob(os.path.join(W, "data", "raw", "mediacloud", "r*_stories_*.jsonl"))):
    out = path.replace(".jsonl", ".rehydrated.jsonl"); done = set()
    if os.path.exists(out):
        done = {json.loads(l)["id"] for l in open(out)}
    with open(path) as f, open(out, "a") as g:
        for line in f:
            r = json.loads(line)
            if r["id"] in done: continue
            for attempt in range(5):
                try:
                    st = S.story(r["id"]); break
                except Exception as e:
                    time.sleep(2 ** attempt); st = None
            if st:
                r["url"] = st.get("url"); r["title"] = st.get("title")
            g.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("done", os.path.basename(path))
