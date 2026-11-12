"""Third Nowcast model: Allan Lichtman's six objective Keys to the White House, counted.

The six keys (each one TRUE favors the party holding the White House):
  1  Party mandate      After the midterms the party holds more House seats than after the previous midterms.
  2  No primary contest There is no serious contest for the party's nomination.
  3  Incumbent running  The party's candidate is the sitting president.
  4  No third party     There is no significant third-party or independent campaign.
  5  Short-term economy The economy is not in recession during the campaign.
  6  Long-term economy  Real per capita growth during the term equals or exceeds the mean of the previous two terms.
The other seven keys (scandal, charisma, foreign success and so on) need Lichtman's judgment and are not used.

Keys 1 to 4 are set in config.json ("keys") once they are known; a key not yet known counts as half false.
Keys 5 and 6 are scored every day from FRED:
  5  false if the real-time Sahm rule indicator (SAHMREALTIME) is 0.5 or more, or real GDP per capita
     (A939RX0Q048SBEA) fell in each of the last two quarters.
  6  annualized growth of real GDP per capita from the quarter before the term began to the latest quarter,
     against the mean of the same growth over each of the previous two terms.

The vote: incumbent party's share of the national two-party vote = a + b x (number of the six keys false),
fitted on every election 1864-2024 (keys_history.csv: Lichtman's ratings as tabulated on Wikipedia; the
two-party vote from the Gov 1347 course data, certified results for 2024). It is spread to the states by
shifting the 2024 state results by the change in the national vote.

Back-test (each election forecast from earlier elections only, 2008-2024): adding this model to the other
two with equal weights lowered the average state miss from 2.10 to 1.87 points and the national miss from
0.98 to 0.78 points.
"""
import csv
import math
import os

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


def build(cfg, fetch, api_key, base_dem):
    """Score the six keys and return the payload block. fetch(series, key, start) -> [(YYYY-MM, value)].
    base_dem: Democratic share of the national two-party vote in the previous election."""
    kc = cfg["keys"]
    gdp = fetch(kc["fred_gdp_per_capita"], api_key, "2016-01-01")
    sahm = fetch(kc["fred_sahm"], api_key, "2025-01-01")
    k5, k6 = score_economy(gdp, sahm, kc["term_start"])
    keys = []
    for k in range(1, 7):
        if k == 5:
            s = k5
        elif k == 6:
            s = k6
        else:
            s = kc[f"key{k}"]
        keys.append({"n": k, "name": NAMES[k], "false": s["false"], "why": s["why"]})
    n_false = sum(1.0 if x["false"] is True else 0.5 if x["false"] is None else 0.0 for x in keys)
    a, b, see, n = fit(load_history())
    inc = a + b * n_false
    dem = inc if cfg["election"]["incumbent_party"] == "D" else 100 - inc
    return {"keys": keys, "false": n_false, "pending": sum(1 for x in keys if x["false"] is None),
            "fit": {"a": round(a, 4), "b": round(b, 4), "se": round(see, 3), "n": n},
            "demNational": round(dem, 3), "base": round(base_dem, 3)}
