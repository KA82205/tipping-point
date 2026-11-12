"""Third Nowcast model: five of Allan Lichtman's objective Keys to the White House, counted.

The five keys (each one TRUE favors the party holding the White House):
  1  Party mandate      After the midterms the party holds more House seats than after the previous midterms.
  2  No primary contest There is no serious contest for the party's nomination.
  3  Incumbent running  The party's candidate is the sitting president.
  5  Short-term economy The economy is not in recession during the campaign.
  6  Long-term economy  Real per capita growth during the term equals or exceeds the mean of the previous two terms.
Key 4 (no significant third party) is left out: before an election it rests on polls of candidates who may
never run, and leaving it out was more accurate in the back-tests. The other seven keys (scandal, charisma,
foreign success and so on) need Lichtman's judgment and are not used.

Each key is scored by Lichtman's own rule (as set out on Wikipedia, "The Keys to the White House"):
  1  Set by hand after each midterm (config.json "keys"): seats after this midterm against after the last.
  2  True if the nominee wins at least two-thirds of the first-ballot delegates at the convention, with no
     deep and vocal party divisions. Set by hand once the delegates are known; until then it counts as half
     false (in the 16 elections since 1864 with no incumbent running it was false in 8), and the note shows
     the leader's share in the latest national primary polls.
  3  Set by hand: is the party's candidate the sitting president?
  5  Scored daily from FRED: false if the real-time Sahm rule indicator (SAHMREALTIME) is 0.5 or more, or
     real GDP per capita (A939RX0Q048SBEA) fell in each of the last two quarters. Lichtman also counts a
     recession the public believes is happening; config.json "key5" can set that by hand.
  6  Scored daily from FRED: annualized growth of real GDP per capita from the quarter before the term began
     to the latest quarter, against the mean of the same growth over each of the previous two terms.

The vote: incumbent party's share of the national two-party vote = a + b x (number of the five keys false),
fitted on every election 1864-2024 (keys_history.csv: Lichtman's ratings as tabulated on Wikipedia; the
two-party vote from the Gov 1347 course data, certified results for 2024). It is spread to the states by
shifting the 2024 state results by the change in the national vote. Lichtman forecasts only the winner, not
states; this state-by-state spread is the Nowcast's.

Back-test (each election forecast from earlier elections only, 2008-2024): adding this model to the other
two with equal weights lowered the average state miss from 2.10 to 1.85 points and the national miss from
0.98 to 0.90 points. Against the same model with key 4 included: state miss 1.85 vs 1.87, national 0.90 vs
0.78; forecasting each of 1996-2024 from all other elections, state 2.09 vs 2.15, national 1.01 vs 1.13; the
keys alone over all 41 elections, national 3.64 vs 3.68.
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {1: "Party mandate", 2: "No primary contest", 3: "Sitting president running",
         5: "Short-term economy", 6: "Long-term economy"}
KEYS = (1, 2, 3, 5, 6)


def load_history(path=os.path.join(HERE, "keys_history.csv")):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            nf = sum(int(r[f"key{k}_false"]) for k in KEYS)
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


def build(cfg, fetch, api_key, base_dem, standing=None):
    """Score the six keys and return the payload block. fetch(series, key, start) -> [(YYYY-MM, value)].
    base_dem: Democratic share of the national two-party vote in the previous election.
    standing: primary polling by party, for the key 2 note."""
    kc = cfg["keys"]
    party = cfg["election"]["incumbent_party"]
    gdp = fetch(kc["fred_gdp_per_capita"], api_key, "2016-01-01")
    sahm = fetch(kc["fred_sahm"], api_key, "2025-01-01")
    auto = dict(zip((5, 6), score_economy(gdp, sahm, kc["term_start"])))
    k5_hand = kc.get("key5") or {}
    if k5_hand.get("false") is not None:          # a recession the public perceives, set by hand
        auto[5] = {"false": k5_hand["false"], "why": k5_hand["why"]}
    keys = []
    for k in KEYS:
        s = dict(auto.get(k) or kc[f"key{k}"])
        if k == 2 and s["false"] is None:
            s["why"] = s["why"] + primary_note(standing, party)
        keys.append({"n": k, "name": NAMES[k], "false": s["false"], "why": s["why"]})
    n_false = sum(1.0 if x["false"] is True else 0.5 if x["false"] is None else 0.0 for x in keys)
    a, b, see, n = fit(load_history())
    inc = a + b * n_false
    dem = inc if cfg["election"]["incumbent_party"] == "D" else 100 - inc
    return {"keys": keys, "count": len(keys), "false": n_false, "pending": sum(1 for x in keys if x["false"] is None),
            "fit": {"a": round(a, 4), "b": round(b, 4), "se": round(see, 3), "n": n},
            "demNational": round(dem, 3), "base": round(base_dem, 3)}
