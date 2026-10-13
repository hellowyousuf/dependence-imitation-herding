#!/usr/bin/env python3
"""Build ./workspace/, a folder laid out like the original project, from the released files.
The analysis scripts read paths such as data/coded/following_cells.csv relative to a project root, which they take
from the PF_PROJECT environment variable. This script links the released files into that layout, decompresses the
.gz files, unpacks the agents' proposals and copies the run log and results (the scripts append to them).

  python3 code/make_workspace.py            # creates ./workspace
  export PF_PROJECT=$PWD/workspace
  python3 workspace/data/analysis/p2_tier_model.py
"""
import gzip, os, shutil, sys, zipfile
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(os.getcwd(), "workspace")
if os.path.exists(W): sys.exit("workspace/ exists; remove it first")

def place(src, dst, copy=False):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if ".gz.part" in src:                      # large files ship in 9 MB parts: join, then decompress
        if not src.endswith(".part01"): return
        import glob
        parts = sorted(glob.glob(src[:-2] + "[0-9][0-9]")); whole = dst[:dst.index(".gz.part")]
        import io
        buf = io.BytesIO(b"".join(open(p, "rb").read() for p in parts))
        with open(whole, "wb") as g, gzip.open(buf, "rb") as f: shutil.copyfileobj(f, g)
        return
    if src.endswith(".gz"):
        with gzip.open(src, "rb") as f, open(dst[:-3], "wb") as g: shutil.copyfileobj(f, g)
    elif copy: shutil.copy2(src, dst)
    else: os.symlink(src, dst)

# code -> data/analysis, codebook -> data/codebook.json
for root, _, files in os.walk(os.path.join(R, "code", "analysis")):
    for f in files:
        s = os.path.join(root, f); place(s, os.path.join(W, "data", "analysis", os.path.relpath(s, os.path.join(R, "code", "analysis"))))
place(os.path.join(R, "code", "codebook.json"), os.path.join(W, "data", "codebook.json"))
# data (results -> results/, copied)
for root, _, files in os.walk(os.path.join(R, "data")):
    for f in files:
        s = os.path.join(root, f); rel = os.path.relpath(s, os.path.join(R, "data"))
        if rel.startswith("results" + os.sep): place(s, os.path.join(W, rel), copy=True)
        elif rel == "runs.jsonl": place(s, os.path.join(W, "data", rel), copy=True)
        elif rel == "deviations.json": place(s, os.path.join(W, rel))
        else: place(s, os.path.join(W, "data", rel))
# simulation -> data/analysis/sim and data/raw/sim
SIMF = ["outlets.json", "feed_core.jsonl", "feed_wire.jsonl", "feed_events.jsonl", "feed_events.jsonl.gz",
        "pilot.json", "contamination_sample.json", os.path.join("_cache", "p5_cache.json")]
for f in SIMF:
    s = os.path.join(R, "simulation", f)
    if os.path.exists(s): place(s, os.path.join(W, "data", "analysis", "sim", f), copy=f.endswith("p5_cache.json"))
with zipfile.ZipFile(os.path.join(R, "simulation", "p5_proposals.zip")) as z:
    z.extractall(os.path.join(W, "data", "raw", "sim"))
print("workspace ready:", W)
