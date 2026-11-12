"""Third Nowcast model: Allan Lichtman's six objective Keys to the White House, counted.

The six keys (each one TRUE favors the party holding the White House):
  1  Party mandate      After the midterms the party holds more House seats than after the previous midterms.
  2  No primary contest There is no serious contest for the party's nomination.
  3  Incumbent running  The party's candidate is the sitting president.
  4  No third party     There is no significant third-party or independent campaign.
  5  Short-term economy The economy is not in recession during the campaign.
  6  Long-term economy  Real per capita growth during the term equals or exceeds the mean of the previous two terms.
The other seven keys (scandal, charisma, foreign success and so on) need Lichtman's judgment and are not used.

Each key is scored by Lichtman's own rule (as set out on Wikipedia, "The Keys to the White House"):
  1  Set by hand after each midterm (config.json "keys"): seats after this midterm against after the last.
  2  True if the nominee wins at least two-thirds of the first-ballot delegates at the convention, with no
     deep and vocal party divisions. Set by hand once the delegates are known; until then it counts as half
     false, and the note shows the leader's share in the latest national primary polls.
  3  Set by hand: is the party's candidate the sitting president?
  4  Scored daily from PollResults.org: false if a single third-party or independent candidate consistently
     polls at 10% or more in national general-election polls. "Consistently" here means a median of 10% or
     more over at least 3 polls from at least 2 pollsters in the last 120 days.
  5  Scored daily from FRED: false if the real-time Sahm rule indicator (SAHMREALTIME) is 0.5 or more, or
     real GDP per capita (A939RX0Q048SBEA) fell in each of the last two quarters. Lichtman also counts a
     recession the public believes is happening; config.json "key5" can set that by hand.
  6  Scored daily from FRED: annualized growth of real GDP per capita from the quarter before the term began
     to the latest quarter, against the mean of the same growth over each of the previous two terms.
A key that is not known yet counts as half false.

The vote: incumbent party's share of the national two-party vote = a + b x (number of the six keys false),
fitted on every election 1864-2024 (keys_history.csv: Lichtman's ratings as tabulated on Wikipedia; the
two-party vote from the Gov 1347 course data, certified results for 2024). It is spread to the states by
shifting the 2024 state results by the change in the national vote.

Back-test (each election forecast from earlier elections only, 2008-2024): adding this model to the other
two with equal weights lowered the average state miss from 2.10 to 1.87 points and the national miss from
0.98 to 0.78 points.
"""
import csv
import datetime as dt
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {1: "Party mandate", 2: "No primary contest", 3: "Sitting president running", 4: "No third party",
         5: "Short-term economy", 6: "Long-term economy"}


def load_history(path=os.path.join(HERE, "keys_history.csv")):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            nf = sum(int(r[f"key{k}_false"]) for k in range(1, 7))
            dem = float(r["dem_two_party"])
            rows.append({"year": int(r["year"]), "party": r["incumbent_party"], "false": nf,
                         "share": dem if r["incumbent_party"] == "D" else 100 - dem})
    return rows


def fit(rows):
    """Least squares of incumbent share on the number of false keys. Returns (a, b, standard error, n)."""
    n = len(rows)
    mx = sum(r["false"] for r in rows) / n
    my = sum(r["share"] for r in rows) / n
    sxx = sum((r["false"] - mx) ** 2 for r in rows)
    b = sum((r["false"] - mx) * (r["share"] - my) for r in rows) / sxx
    a = my - b * mx
    see = math.sqrt(sum((r["share"] - a - b * r["false"]) ** 2 for r in rows) / (n - 2))
    return a, b, see, n


THIRD_PARTY = {"threshold": 10.0, "days": 120, "min_polls": 3, "min_pollsters": 2}
_NOT_A_PERSON = ("undecided", "other", "someone else", "none", "not sure", "don't know", "dont know", "refused",
                 "would not vote", "no one", "unsure", "generic", "cannot vote")


def score_third_party(raw, end, iso, rule=THIRD_PARTY):
    """Key 4 from PollResults.org records. A poll counts once per candidate (the average over the match-ups
    in that poll that named them). Returns a key dict, or None if there are no general-election polls."""
    start = end - dt.timedelta(days=rule["days"])
    seen, n_polls = {}, set()
    for res in raw or []:
        if str(res.get("state") or "").upper() not in ("US", "USA", "NATIONAL", "") or res.get("internal"):
            continue
        try:
            day = dt.date.fromisoformat(iso(res.get("endDate") or res.get("end_date")))
        except (ValueError, TypeError):
            continue
        if not (start <= day <= end):
            continue
        pollster = str(res.get("pollster") or "").strip()
        for q in res.get("questions") or []:
            if str(q.get("stage") or "").lower() != "general":
                continue
            n_polls.add((pollster, day))
            for a in q.get("answers") or []:
                name = str(a.get("candidateName") or "").strip()
                tag = str(a.get("party") or "").upper()[:1]
                if not name or a.get("pct") is None or tag in ("D", "R", "N", "") \
                        or any(w in name.lower() for w in _NOT_A_PERSON):
                    continue
                seen.setdefault(name, {}).setdefault((pollster, day), []).append(float(a["pct"]))
    if not n_polls:
        return None
    rows = []
    for name, polls in seen.items():
        vals = [sum(v) / len(v) for v in polls.values()]
        rows.append({"name": name, "median": statistics.median(vals), "polls": len(vals),
                     "pollsters": len({p for p, _ in polls})})
    rows.sort(key=lambda r: (-r["median"], -r["polls"]))
    hits = [r for r in rows if r["median"] >= rule["threshold"] and r["polls"] >= rule["min_polls"]
            and r["pollsters"] >= rule["min_pollsters"]]
    def desc(r):
        return (f"{r['name']} ({r['median']:.0f}% median in {r['polls']} poll{'s' if r['polls'] != 1 else ''} "
                f"from {r['pollsters']} pollster{'s' if r['pollsters'] != 1 else ''})")
    if hits:
        why = (f"{desc(hits[0])} is consistently polling at {rule['threshold']:.0f}% or more in national polls "
               f"over the last {rule['days']} days.")
    else:
        top = f" The highest tested: {desc(rows[0])}." if rows else " No poll tested one."
        why = (f"No third-party or independent candidate is consistently polling at {rule['threshold']:.0f}% or "
               f"more in national polls ({len(n_polls)} polls in the last {rule['days']} days).{top}")
    return {"false": bool(hits), "why": why, "tested": rows[:5]}


def primary_note(standing, party):
    """A line on the incumbent party's primary polling, for key 2 while it is still pending."""
    rows = (standing or {}).get(party) or []
    if not rows:
        return ""
    lead = rows[0]
    second = f", ahead of {rows[1]['name']} at {rows[1]['pct']:.0f}%" if len(rows) > 1 else ""
    return (f" In the latest national primary polls {lead['name']} leads with {lead['pct']:.0f}%{second}; "
            f"two-thirds of the delegates would need a much larger share.") if lead["pct"] < 66.7 else \
           (f" In the latest national primary polls {lead['name']} leads with {lead['pct']:.0f}%{second}.")


def _quarter_back(ym, q):
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + m - 1 - 3 * q
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def score_economy(gdp, sahm, term_start):
    """gdp: [(YYYY-MM, real GDP per capita)] quarterly; sahm: [(YYYY-MM, value)] monthly.
    term_start: first month of the term, e.g. '2025-01'. Returns (key5, key6) as dicts."""
    g = dict(gdp)
    months = sorted(g)
    last = months[-1]
    base = _quarter_back(term_start, 1)                      # quarter before the term began
    prev1, prev2 = _quarter_back(base, 32), _quarter_back(base, 16)

    def ann(a, b):
        q = (int(b[:4]) * 12 + int(b[5:7]) - int(a[:4]) * 12 - int(a[5:7])) / 3
        return 100 * ((g[b] / g[a]) ** (4 / q) - 1)
    now = ann(base, last)
    before = (ann(prev1, prev2) + ann(prev2, base)) / 2
    d = 3 if round(now, 2) == round(before, 2) else 2
    k6 = {"false": now < before,
          "why": f"Real GDP per person has grown {now:.{d}f}% a year this term (through {last}), "
                 f"{'just ' if abs(now - before) < 0.05 else ''}{'above' if now >= before else 'below'} the average of "
                 f"{before:.{d}f}% a year over the previous two terms."}
    s_last = sahm[-1]
    falls = len(months) >= 3 and g[months[-1]] < g[months[-2]] < g[months[-3]]
    k5 = {"false": s_last[1] >= 0.5 or falls,
          "why": f"The real-time Sahm rule recession indicator is {s_last[1]:.2f} ({s_last[0]}); 0.5 or more signals a "
                 f"recession. Real GDP per person {'fell' if falls else 'did not fall'} in each of the last two quarters."}
    return k5, k6


def build(cfg, fetch, api_key, base_dem, polls=None, standing=None, today=None, iso=None):
    """Score the six keys and return the payload block. fetch(series, key, start) -> [(YYYY-MM, value)].
    base_dem: Democratic share of the national two-party vote in the previous election.
    polls: PollResults.org presidential records (key 4); standing: primary polling by party (key 2 note)."""
    kc = cfg["keys"]
    party = cfg["election"]["incumbent_party"]
    gdp = fetch(kc["fred_gdp_per_capita"], api_key, "2016-01-01")
    sahm = fetch(kc["fred_sahm"], api_key, "2025-01-01")
    auto = dict(zip((5, 6), score_economy(gdp, sahm, kc["term_start"])))
    k5_hand = kc.get("key5") or {}
    if k5_hand.get("false") is not None:          # a recession the public perceives, set by hand
        auto[5] = {"false": k5_hand["false"], "why": k5_hand["why"]}
    if kc.get("key4", {}).get("false") is None and today and iso:
        k4 = score_third_party(polls, today, iso)
        if k4:
            auto[4] = k4
    keys = []
    for k in range(1, 7):
        s = dict(auto.get(k) or kc[f"key{k}"])
        if k == 2 and s["false"] is None:
            s["why"] = s["why"] + primary_note(standing, party)
        row = {"n": k, "name": NAMES[k], "false": s["false"], "why": s["why"]}
        if s.get("tested"):
            row["tested"] = [{"name": t["name"], "median": round(t["median"], 1), "polls": t["polls"]}
                             for t in s["tested"]]
        keys.append(row)
    n_false = sum(1.0 if x["false"] is True else 0.5 if x["false"] is None else 0.0 for x in keys)
    a, b, see, n = fit(load_history())
    inc = a + b * n_false
    dem = inc if cfg["election"]["incumbent_party"] == "D" else 100 - inc
    return {"keys": keys, "false": n_false, "pending": sum(1 for x in keys if x["false"] is None),
            "fit": {"a": round(a, 4), "b": round(b, 4), "se": round(see, 3), "n": n},
            "demNational": round(dem, 3), "base": round(base_dem, 3)}
