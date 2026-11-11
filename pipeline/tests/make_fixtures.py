"""Synthetic FRED and VoteHub responses for offline testing. NOT real data."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from economy import STATES  # noqa: E402

out = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(out, exist_ok=True)
rng = random.Random(1)
for st in STATES:
    v, rows, g = 100.0, [], rng.uniform(-0.05, 0.35)
    for i in range(23):  # Dec 2024 .. Oct 2026
        y, m = 2024 + (11 + i) // 12, (11 + i) % 12 + 1
        rows.append([f"{y}-{m:02d}", round(v, 2)])
        v *= 1 + (g + rng.gauss(0, 0.1)) / 100
    json.dump(rows, open(os.path.join(out, f"{st}PHCI.json"), "w"))

polls = []
for i, name in enumerate(["Pollster A", "Pollster B", "Pollster C", "Pollster D", "Pollster E"]):
    for d in (3, 12, 25):
        ap = 40 + rng.gauss(0, 2)
        polls.append({"pollster": name, "end_date": f"2026-11-{28 - d - i:02d}" if 28 - d - i > 0 else "2026-10-20",
                      "sample_size": str(800 + 300 * i), "population": "rv", "internal": False, "partisan": None,
                      "answers": [{"choice": "Approve", "pct": round(ap)}, {"choice": "Disapprove", "pct": round(96 - ap)}]})
polls.append({"pollster": "Campaign Internal", "end_date": "2026-11-05", "sample_size": "500", "internal": True,
              "partisan": "R", "answers": [{"choice": "Approve", "pct": 70}, {"choice": "Disapprove", "pct": 28}]})
json.dump(polls, open(os.path.join(out, "votehub.json"), "w"))
print("fixtures written to", out)

# PollResults.org records in its real format (camelCase, M/D/YY dates, yes/no answers). NOT real data.
pr = [
    {"pollster": "Pollster F", "state": "US", "endDate": "11/6/26", "internal": "", "partisan": "", "url": "",
     "questions": [{"sampleSize": 1200, "population": "rv", "answers": [{"politician": "Donald Trump", "yes": 40, "no": 57}]},
                   {"sampleSize": 1500, "population": "a", "answers": [{"politician": "Donald Trump", "yes": 38, "no": 59}]}]},
    {"pollster": "Pollster A", "state": "US", "endDate": "11/3/26",
     "questions": [{"sampleSize": 900, "population": "rv", "answers": [{"politician": "Donald Trump", "yes": 41, "no": 55}]}]},
    {"pollster": "State Poll Co", "state": "PA", "endDate": "11/1/26",
     "questions": [{"sampleSize": 900, "population": "rv", "answers": [{"politician": "Donald Trump", "yes": 36, "no": 60}]}]},
    {"pollster": "Odd Format", "foo": "bar"},
]
json.dump({"results": pr}, open(os.path.join(out, "pollresults.json"), "w"))
