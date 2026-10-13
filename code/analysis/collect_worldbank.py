#!/usr/bin/env python3
"""V5 input (codebook C5): World Bank WDI, 2022 — GNI (current US$, NY.GNP.MKTP.CD; the WDI series for GNP) and exports
of goods and services (current US$, NE.EXP.GNFS.CD) for the world (WLD) and the six sampled countries.
Writes data/raw/worldbank_wdi_2022.json (the API responses verbatim, plus retrieval metadata). Also fetched, for the gap and robustness only: BX.GSR.GNFS.CD (exports of goods and services, BoP),
TX.VAL.MRCH.CD.WT (merchandise exports) and NY.GNP.ATLS.CD (GNI, Atlas method) — NE.EXP.GNFS.CD is null for Nigeria in 2022.
No computation here."""
import json, sys, urllib.request, datetime as dt, os
P = sys.argv[1]
C = ["WLD", "BGD", "KEN", "NGA", "IND", "ZAF", "MYS"]; IND = ["NY.GNP.MKTP.CD", "NE.EXP.GNFS.CD", "BX.GSR.GNFS.CD", "TX.VAL.MRCH.CD.WT", "NY.GNP.ATLS.CD"]
out = {"retrieved": dt.date.today().isoformat(), "source": "World Bank, World Development Indicators (API v2)",
       "licence": "CC BY 4.0", "year": 2022, "responses": {}}
for i in IND:
    url = f"https://api.worldbank.org/v2/country/{';'.join(C)}/indicator/{i}?date=2022&format=json&per_page=100"
    with urllib.request.urlopen(url, timeout=60) as r:
        out["responses"][i] = {"url": url, "body": json.load(r)}
p = os.path.join(P, "data/raw/worldbank_wdi_2022.json"); json.dump(out, open(p, "w"), indent=1)
print("wrote", p)
