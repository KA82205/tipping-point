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

# Wikipedia lead sections and VoteHub favorability, for the candidate/VP steps. NOT real data.
open(os.path.join(out, "wiki_2028-united-states-presidential-election.txt"), "w").write(
    "{{Infobox election\n| nominee1 = \n| party1 = Republican Party (United States)\n| home_state1 = \n"
    "| running_mate1 = \n| nominee2 = \n| party2 = Democratic Party (United States)\n}}")
open(os.path.join(out, "wiki_vice-president-of-the-united-states.txt"), "w").write("| incumbent = [[JD Vance]]\n")
fav = lambda f, u: [{"pollster": p, "end_date": "2026-11-0" + str(i + 1), "answers": [  # noqa: E731
    {"choice": "Favorable", "pct": f}, {"choice": "Unfavorable", "pct": u}]} for i, p in enumerate("ABCD")]
json.dump(fav(38, 50), open(os.path.join(out, "fav_jd-vance.json"), "w"))
json.dump(fav(40, 56), open(os.path.join(out, "fav_donald-trump.json"), "w"))
appr = lambda a, d: [{"pollster": p, "end_date": "2026-11-0" + str(i + 1), "answers": [  # noqa: E731
    {"choice": "Approve", "pct": a}, {"choice": "Disapprove", "pct": d}]} for i, p in enumerate("ABCD")]
json.dump(appr(39, 49), open(os.path.join(out, "appr_jd-vance.json"), "w"))

# PollResults.org 2028 primary polls in its real format. NOT real data.
prim = lambda who, sub, rows: {"pollster": who, "state": "US", "endDate": "11/2/26", "questions": [  # noqa: E731
    {"stage": "primary", "subpopulation": sub, "answers": [{"candidateName": n, "pct": v, "party": sub.upper()} for n, v in rows]}]}
# General-election pairings in the same format: one question per pairing. NOT real data.
gen = lambda who, day, pop, rows: {"pollster": who, "state": "US", "endDate": day, "internal": "", "questions": [  # noqa: E731
    {"stage": "general", "population": pop, "answers": [
        {"candidateName": d, "pct": dp, "party": "DEM"}, {"candidateName": r, "pct": rp, "party": "REP"},
        {"candidateName": "", "answer": "Don't know", "pct": 100 - dp - rp, "party": "NONE"}] + extra}
    for d, dp, r, rp, extra in rows]}
json.dump({"results": [
    gen("Pollster A", "11/2/26", "lv", [("Gavin Newsom", 46, "JD Vance", 44, []), ("Gavin Newsom", 45, "Marco Rubio", 43, []),
                                        ("Alexandria Ocasio-Cortez", 42, "J.D. Vance", 46, [])]),
    gen("Pollster B", "10/20/26", "rv", [("Gavin Newsom", 47, "JD Vance", 45, []), ("Pete Buttigieg", 44, "JD Vance", 44, []),
                                         ("Democrat", 48, "Republican", 40, []),
                                         ("Gavin Newsom", 40, "JD Vance", 38, [{"candidateName": "Some Independent", "pct": 9, "party": "IND"}])]),
    gen("Pollster C", "9/15/26", "lv", [("Gavin Newsom", 48, "JD Vance", 45, []), ("Barack Obama", 52, "Donald Trump", 42, [])]),
    gen("Pollster C", "1/5/26", "lv", [("Gavin Newsom", 50, "JD Vance", 40, [])]),
    prim("Pollster A", "d", [("Gavin Newsom", 24), ("Pete Buttigieg", 14), ("Josh Shapiro", 9), ("Undecided", 20)]),
    prim("Pollster B", "d", [("Gavin Newsom", 22), ("Pete Buttigieg", 16), ("Josh Shapiro", 7)]),
    prim("Pollster A", "r", [("JD Vance", 48), ("Marco Rubio", 12), ("Donald Trump Jr.", 10)]),
    prim("Pollster B", "r", [("J.D. Vance", 44), ("Marco Rubio", 14)]),
]}, open(os.path.join(out, "pollresults_president.json"), "w"))
