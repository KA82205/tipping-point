"""Builds docs/archive.js: the back-test of 2008 to 2020, state by state, for the site's Archive page.

Each election is forecast by each model refitted on the elections before it only, with that year's inputs,
exactly as pipeline/backtest_2008_2024.py does for the Method page's track record; the Nowcast is the plain
average of the two. Nobody published these: they are today's versions of the models run on the past.
(2024 is not here. The Archive shows it from docs/data.js and docs/backtest2024.js, which hold the forecasts
the authors published for that year.)

Ranges and odds use the site's error model on each back-test forecast, as the track record does: for each of
seven draws of the correlation (0.70 to 0.97) a shared national error and a state error, total size the
approval model's standard error at the time. Coefficient draws are left out, so ranges are slightly narrow.

The District of Columbia is not in the long-range model's data. Its row is the approval and fundamentals
back-test in every view, and its 3 electoral votes are counted for the Democrat in the odds. The equation is a
straight line, so in 2020 it puts the District a tenth of a point above 100%; the page shows 100.
Electoral votes count each state as a whole, as both papers did for these years.

Usage:  python pipeline/make_archive.py /path/to/replication/folder     (see backtest_2008_2024.py)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest_2008_2024 as bt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = {
    2008: {"dem": "Obama", "rep": "McCain", "realEV": {"dem": 365, "rep": 173},
           "evNote": "The real count was 365 to 173: Nebraska's 2nd district went to Obama."},
    2012: {"dem": "Obama", "rep": "Romney", "realEV": {"dem": 332, "rep": 206}, "evNote": ""},
    2016: {"dem": "Clinton", "rep": "Trump", "realEV": {"dem": 227, "rep": 304},
           "evNote": "The real count was 304 to 227: Maine's 2nd district went to Trump, and seven electors voted for other people."},
    2020: {"dem": "Biden", "rep": "Trump", "realEV": {"dem": 306, "rep": 232},
           "evNote": "The real count was also 306 to 232: Maine's 2nd district went to Trump and Nebraska's 2nd to Biden."},
}
PUBLISHED = {
    2008: "Nothing. Neither model had made a forecast yet: the long-range model's first was for 2016, and the approval and fundamentals model's was for 2020.",
    2012: "Nothing. Neither model had made a forecast yet: the long-range model's first was for 2016, and the approval and fundamentals model's was for 2020.",
    2016: "DeSart's long-range forecast for Clinton against Trump, as he reports it in his 2024 paper, had Clinton at 50.3% of the two-party vote, against a result of 51.0%. The paper gives no count of states for that year. The approval and fundamentals model's first forecast was for 2020.",
    2020: "Enns and Lagodny's forecast called 49 of 50 states, missing only Georgia, with Biden at 54.5% of the two-party vote. DeSart's forecast, made from October 2019 polls, called 48 of 50, missing Florida and North Carolina, with Biden at 54.8%. The result was 52.2%.",
}


def rating(p):
    top, party = max(p, 1 - p), "D" if p >= 0.5 else "R"
    return "S" + party if top > 0.98 else "L" + party if top > 0.75 else "T" + party if top > 0.55 else "TOSS"


def simulate(point, ev, sd, rng, n=20000):
    """The track record's error model: state win chances and the chance of 270 (DC's 3 votes to the Democrat)."""
    wins, dem = np.zeros(len(point)), 0
    for _ in range(7):
        u = rng.uniform(0.70, 0.97)
        sh = point + np.sqrt(u) * sd * rng.standard_normal((n, 1)) + np.sqrt(1 - u) * sd * rng.standard_normal((n, len(point)))
        w = sh > 50
        wins += w.sum(axis=0)
        dem += ((w * ev).sum(axis=1) + 3 >= 270).sum()
    return wins / (7 * n), dem / (7 * n)


def main(folder):
    res = json.load(open(os.path.join(HERE, "results_2024.json")))
    name2ab = {v["name"]: k for k, v in res.items() if len(k) == 2}
    d, D = bt.load(folder)
    A = bt.frame(d, D, "onestep")
    out = {}
    # The Nowcast's odds are drawn exactly as the track record draws them (same generator, same order of years),
    # so the chances shown here are the ones quoted on the Method page.
    main_rng, avg_sim = np.random.default_rng(2028), {}
    for y, g in A.groupby("year"):
        avg_sim[int(y)] = simulate(g.avg.values, g.ecvotes.values, float(g.rmse.iloc[0]), main_rng)
    for y, meta in YEARS.items():
        g = A[A.year == y].reset_index(drop=True)
        sd = float(g.rmse.iloc[0])
        rng = np.random.default_rng(2028 + y)
        states = {name2ab[s]: {"ev": int(e), "share": round(float(r), 2)} for s, e, r in zip(g.State, g.ecvotes, g.Result)}
        nat = {}
        for key, col in (("bt", "avg"), ("enns", "enns"), ("desart", "desart")):
            p_state, p_win = avg_sim[y] if key == "bt" else simulate(g[col].values, g.ecvotes.values, sd, rng)
            nat[key] = {"fc": round(bt.nat(g, col), 2), "pDemWin": round(float(p_win), 4),
                        "demEV": int(g.loc[g[col] > 50, "ecvotes"].sum() + 3)}
            for s, fc, p in zip(g.State, g[col], p_state):
                states[name2ab[s]][key] = {"fc": round(float(fc), 2), "lo": round(float(fc - 1.645 * sd), 1), "hi": round(float(fc + 1.645 * sd), 1),
                                           "pDem": round(float(p), 3), "rating": rating(float(p))}
        # The District of Columbia: in the approval model's data only.
        e, _ = bt.enns(d, y, range(1980, y, 4))
        dc_fc = min(100.0, float(e.loc[e.State == "District of Columbia", "enns"].iloc[0]))
        dc_res = float(d.loc[(d.year == y) & (d.State == "District of Columbia"), "PerDem2Party"].iloc[0])
        cell = {"fc": round(dc_fc, 2), "lo": round(dc_fc - 1.645 * sd, 1), "hi": round(min(100.0, dc_fc + 1.645 * sd), 1), "pDem": 1.0, "rating": "SD"}
        states["DC"] = {"ev": 3, "share": round(dc_res, 2), "bt": cell, "enns": cell, "desart": cell, "only": "enns"}
        whole = int(g.loc[g.Result > 50, "ecvotes"].sum() + 3)
        out[str(y)] = {**meta, "wholeEV": {"dem": whole, "rep": 538 - whole}, "natActual": round(bt.nat(g, "Result"), 2),
                       "rmse": round(sd, 2), "pub": PUBLISHED[y], "nat": nat, "states": states}
        assert sum(s["ev"] for s in states.values()) == 538, y
    path = os.path.join(HERE, "..", "docs", "archive.js")
    with open(path, "w") as f:
        f.write("// Generated by pipeline/make_archive.py: the back-test of 2008-2020, state by state (see that file).\n"
                "window.ARCHIVE = " + json.dumps({"years": out}, separators=(",", ":")) + ";\n")
    for y, v in out.items():
        st = [s for a, s in v["states"].items() if a != "DC"]
        called = {k: sum((s[k]["fc"] > 50) == (s["share"] > 50) for s in st) for k in ("bt", "enns", "desart")}
        print(y, "result", v["natActual"], "| Nowcast", v["nat"]["bt"], "| called of 50:", called, "| whole-state EV actual", v["wholeEV"])
    print("wrote", os.path.normpath(path), os.path.getsize(path), "bytes")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
