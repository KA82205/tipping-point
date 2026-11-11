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
json.dump({"polls": polls}, open(os.path.join(out, "votehub.json"), "w"))
print("fixtures written to", out)

# PollResults-style records (guessed shape: poll -> questions -> answers). NOT real data.
pr = [
    {"pollster": "Pollster F", "url": None, "questions": [{"end_date": "2026-11-06", "sample_size": 1200, "population": "a",
      "answers": [{"choice": "Approve", "pct": 39}, {"choice": "Disapprove", "pct": 57}]}]},
    {"pollster": "Pollster A", "end_date": "2026-11-03", "questions": [{"answers": [{"answer": "Approve", "pct": 41}, {"answer": "Disapprove", "pct": 55}]}]},
    {"pollster": "State Poll Co", "state": "PA", "questions": [{"end_date": "2026-11-01", "sample_size": 900,
      "answers": [{"choice": "Approve", "pct": 36}, {"choice": "Disapprove", "pct": 60}]}]},
    {"pollster": "Odd Format", "foo": "bar"},
]
json.dump({"results": pr}, open(os.path.join(out, "pollresults.json"), "w"))
