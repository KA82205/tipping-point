"""Builds docs/archive.js: 2008 to 2020, state by state, for the site's Archive page.

Where the authors published state forecasts before the election, the Archive shows those. Where they did not, it
shows a back-test and says so.

2020  Both models were published. The approval and fundamentals forecast is Enns and Lagodny's, read from the
      chart in their article (pipeline/extract_fig3_2020.py -> pipeline/forecast_2020_fig3.json). The long-range
      forecast is DeSart's, from his replication file (pipeline/forecast_2020_desart.json). The Nowcast's method
      is the plain average of the two, state by state, which nobody published at the time.
2008, 2012, 2016
      No state forecasts were published: the approval and fundamentals model's first forecast was for 2020, and
      only the national figure of DeSart's 2016 forecast is on record. Each model is refitted on the elections
      before that year only, with that year's inputs, exactly as pipeline/backtest_2008_2024.py does for the Method
      page's track record; the Nowcast's method is the average of the two.
(2024 is not here. The Archive builds it in the browser from docs/data.js and docs/backtest2024.js, which hold the
two forecasts the authors published for that year.)

Results. State results are the official counts in pipeline/results_2008_2020.json. The national result is the
official two-party vote from the FEC's Federal Elections reports.

National vote. A back-test's national figure adds up its 50 state forecasts with the long-range model's turnout
weights, then adds the District of Columbia by its share of the national vote. Published forecasts keep the
national figure their authors published.

Ranges and odds. For a back-test, and for the average of the two published 2020 forecasts, they come from the
site's error model as in the track record: for each of seven draws of the correlation (0.70 to 0.97) a shared
national error and a state error, total size the approval model's standard error at the time. Coefficient draws
are left out, so ranges are slightly narrow. Published forecasts keep their authors' own ranges and state chances.

The District of Columbia is not in the long-range model's data before 2020. In those years its row is the approval
and fundamentals back-test in every view, capped at 100, and its 3 electoral votes are counted for the Democrat in
the odds. Electoral votes count each state as a whole in every year, and the scores count the 50 states.

Usage:  python pipeline/make_archive.py /path/to/replication/folder     (see backtest_2008_2024.py)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest_2008_2024 as bt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# dem, rep: the nominees. official: the national vote for the two (FEC, Federal Elections 2008, 2012, 2016, 2020).
YEARS = {
    2008: {"dem": "Obama", "rep": "McCain", "realEV": {"dem": 365, "rep": 173}, "official": (69498516, 59948323),
           "evNote": "The real count was 365 to 173: Nebraska's 2nd district went to Obama."},
    2012: {"dem": "Obama", "rep": "Romney", "realEV": {"dem": 332, "rep": 206}, "official": (65915795, 60933504), "evNote": ""},
    2016: {"dem": "Clinton", "rep": "Trump", "realEV": {"dem": 227, "rep": 304}, "official": (65853514, 62984828),
           "evNote": "The real count was 304 to 227: Maine's 2nd district went to Trump, and seven electors voted for other people."},
    2020: {"dem": "Biden", "rep": "Trump", "realEV": {"dem": 306, "rep": 232}, "official": (81283501, 74223975),
           "evNote": "The real count was also 306 to 232: Maine's 2nd district went to Trump and Nebraska's 2nd to Biden."},
}
PUBLISHED = {
    2008: "Nothing. Neither model had made a forecast yet: the long-range model's first was for 2016, and the approval and fundamentals model's was for 2020.",
    2012: "Nothing. Neither model had made a forecast yet: the long-range model's first was for 2016, and the approval and fundamentals model's was for 2020.",
    2016: "Only a national figure. DeSart's long-range forecast for Clinton against Trump, as he reports it in his 2024 paper, had Clinton at 50.3% of the two-party vote, against a result of 51.1%. His state forecasts for that year are not on record, and the approval and fundamentals model's first forecast was for 2020.",
    2020: "",
}
BACKTEST_NOTE = "A back-test, not a forecast anyone published"


def texts_backtest(y, nat):
    return {
        "bt": {"kind": "backtest", "tab": "Nowcast method, back-tested",
               "lede": f"What the Nowcast's method would have said in {y}: the average of the two models, each refitted only on the elections before {y} and given that year's inputs. No state forecasts were published for {y}, so this is a back-test.",
               "note": f"{BACKTEST_NOTE}: the average of the two models' back-tests, whose national votes were {nat['enns']['fc']:.1f}% and {nat['desart']['fc']:.1f}%."},
        "enns": {"kind": "backtest", "tab": "State-level approval and fundamentals, back-tested",
                 "lede": f"The state-level approval and fundamentals model, refitted only on the elections before {y} and given that year's approval and state economies. The authors' first forecast was for 2020, so this is today's version of the model run on the past.",
                 "note": f"{BACKTEST_NOTE}."},
        "desart": {"kind": "backtest", "tab": "Long-range model, back-tested",
                   "lede": f"The long-range model, refitted only on the elections before {y} and given the head-to-head polls from October {y - 1}. This is today's version of the model run on the past.",
                   "note": f"{BACKTEST_NOTE}."},
    }


TEXTS_2020 = {
    "bt": {"kind": "backtest", "tab": "Nowcast method, back-tested",
           "lede": "What the Nowcast's method would have said in 2020. State by state it averages the two forecasts published before the election: Enns and Lagodny's, made 104 days out, and Jay DeSart's long-range forecast from October 2019 polls. Nobody published this average at the time, so it is a back-test.",
           "note": "A back-test, not a forecast anyone published. State by state it averages two forecasts that were published, whose national votes were 54.5% and 54.8%."},
    "enns": {"kind": "published", "tab": "State-level approval and fundamentals, as published",
             "lede": "The state-level approval and fundamentals forecast as Enns and Lagodny published it for 2020, from data 104 days before the election. Their article gives the state forecasts as a chart, so the state numbers here are read from that chart and are good to about a tenth of a point.",
             "note": "The national vote, the 290 electoral votes and the chance of winning are the article's own. The chance is the share of its simulations with 270 or more electoral votes."},
    "desart": {"kind": "published", "tab": "Long-range model, as published",
               "lede": "The long-range model's forecast as Jay DeSart announced it in November 2019, a year before the election, from head-to-head polls taken that October.",
               "note": "The state forecasts, state chances and national vote are from DeSart's own file. His chance of winning the Electoral College is not on record here; his article called a Biden win highly probable."},
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


def cell(fc, lo, hi, p):
    return {"fc": round(float(fc), 2), "lo": round(float(max(0.0, lo)), 1), "hi": round(float(min(100.0, hi)), 1),
            "pDem": round(float(p), 3), "rating": rating(float(p))}


def year_backtest(y, d, g, avg_sim, name2ab, w_dc):
    """2008, 2012, 2016: each model refitted on earlier elections only, and their average."""
    sd = float(g.rmse.iloc[0])
    rng = np.random.default_rng(2028 + y)
    states = {name2ab[s]: {"ev": int(e)} for s, e in zip(g.State, g.ecvotes)}
    e, _ = bt.enns(d, y, range(1980, y, 4))
    dc_fc = min(100.0, float(e.loc[e.State == "District of Columbia", "enns"].iloc[0]))
    nat = {}
    for key, col in (("bt", "avg"), ("enns", "enns"), ("desart", "desart")):
        p_state, p_win = avg_sim[y] if key == "bt" else simulate(g[col].values, g.ecvotes.values, sd, rng)
        nat[key] = {"fc": round((1 - w_dc) * bt.nat(g, col) + w_dc * dc_fc, 2), "pDemWin": round(float(p_win), 4),
                    "demEV": int(g.loc[g[col] > 50, "ecvotes"].sum() + 3)}
        for s, fc, p in zip(g.State, g[col], p_state):
            states[name2ab[s]][key] = cell(fc, fc - 1.645 * sd, fc + 1.645 * sd, p)
    dc = cell(dc_fc, dc_fc - 1.645 * sd, dc_fc + 1.645 * sd, 1.0)
    states["DC"] = {"ev": 3, "bt": dc, "enns": dc, "desart": dc, "same": True,
                    "note": "The District of Columbia is not in the long-range model's data, so this is the approval and fundamentals back-test in every view."}
    return states, nat, sd, texts_backtest(y, nat)


def year_2020(g, name2ab):
    """2020: the two forecasts the authors published, and their average."""
    E = json.load(open(os.path.join(HERE, "forecast_2020_fig3.json")))
    S = json.load(open(os.path.join(HERE, "forecast_2020_desart.json")))
    sd, se = float(g.rmse.iloc[0]), S["se"]
    order = [name2ab[s] for s in g.State]
    assert sorted(order + ["DC"]) == sorted(E["states"]) == sorted(S["forecast"])
    states = {a: {"ev": S["ev"][a]} for a in order + ["DC"]}
    for a in states:
        c, f = E["states"][a], S["forecast"][a]
        states[a]["enns"] = cell(c["fc"], c["lo"], c["hi"], c["pDem"])
        states[a]["desart"] = cell(f, f - 1.645 * se, f + 1.645 * se, S["winprob"][a])
    avg = np.array([(states[a]["enns"]["fc"] + states[a]["desart"]["fc"]) / 2 for a in order])
    ev = np.array([states[a]["ev"] for a in order])
    p_state, p_win = simulate(avg, ev, sd, np.random.default_rng(2020))
    for a, fc, p in zip(order, avg, p_state):
        states[a]["bt"] = cell(fc, fc - 1.645 * sd, fc + 1.645 * sd, p)
    dc = (states["DC"]["enns"]["fc"] + states["DC"]["desart"]["fc"]) / 2
    states["DC"]["bt"] = cell(dc, dc - 1.645 * sd, 100.0, 1.0)
    states["DC"]["note"] = ("The chart in Enns and Lagodny's article cuts the District of Columbia off at 100%, so its forecast there "
                            "(about 99%) is worked out from the part that shows. DeSart's file has it at 100%.")
    tw = sum(S["turnout"].values())
    nat = {"bt": {"fc": round(sum(S["turnout"][a] * states[a]["bt"]["fc"] for a in states) / tw, 2), "pDemWin": round(float(p_win), 4),
                  "demEV": int(ev[avg > 50].sum() + 3)},
           "enns": {"fc": E["national"], "pDemWin": E["p_dem_win"], "demEV": E["electoral_votes"]},
           "desart": {"fc": S["national"], "pDemWin": None, "demEV": S["electoral_votes"]}}
    assert sum(states[a]["ev"] for a in states if states[a]["enns"]["fc"] > 50) == E["electoral_votes"]
    assert sum(states[a]["ev"] for a in states if states[a]["desart"]["fc"] > 50) == S["electoral_votes"]
    return states, nat, sd, TEXTS_2020


def main(folder):
    res = json.load(open(os.path.join(HERE, "results_2024.json")))
    votes = json.load(open(os.path.join(HERE, "results_2008_2020.json")))
    name2ab = {v["name"]: k for k, v in res.items() if len(k) == 2}
    d, D = bt.load(folder)
    A = bt.frame(d, D, "onestep")
    out = {}
    # The Nowcast's back-test odds are drawn exactly as the track record draws them (same generator, same order
    # of years), so the chances shown for 2008, 2012 and 2016 are the ones quoted on the Method page.
    main_rng, avg_sim = np.random.default_rng(2028), {}
    for y, g in A.groupby("year"):
        avg_sim[int(y)] = simulate(g.avg.values, g.ecvotes.values, float(g.rmse.iloc[0]), main_rng)
    for y, meta in YEARS.items():
        g = A[A.year == y].reset_index(drop=True)
        dem, rep = meta["official"]
        v = votes[str(y)]
        assert abs(sum(a for a, _ in v.values()) / dem - 1) < 0.001 and abs(sum(b for _, b in v.values()) / rep - 1) < 0.001, y
        w_dc = sum(v["DC"]) / (dem + rep)
        if y == 2020:
            states, nat, sd, src = year_2020(g, name2ab)
        else:
            states, nat, sd, src = year_backtest(y, d, g, avg_sim, name2ab, w_dc)
        for a in states:
            states[a]["share"] = round(100 * v[a][0] / sum(v[a]), 2)
        whole = sum(s["ev"] for s in states.values() if s["share"] > 50)
        assert sum(s["ev"] for s in states.values()) == 538 and len(states) == 51, y
        out[str(y)] = {"dem": meta["dem"], "rep": meta["rep"], "realEV": meta["realEV"], "evNote": meta["evNote"],
                       "wholeEV": {"dem": whole, "rep": 538 - whole}, "natActual": round(100 * dem / (dem + rep), 2),
                       "rmse": round(sd, 2), "pub": PUBLISHED[y], "src": src, "nat": nat, "states": states}
    path = os.path.join(HERE, "..", "docs", "archive.js")
    with open(path, "w") as f:
        f.write("// Generated by pipeline/make_archive.py: 2008 to 2020 state by state (see that file).\n"
                "window.ARCHIVE = " + json.dumps({"years": out}, separators=(",", ":")) + ";\n")
    for y, v in out.items():
        st = {a: s for a, s in v["states"].items() if a != "DC"}
        called = {k: sum((s[k]["fc"] > 50) == (s["share"] > 50) for s in st.values()) for k in ("bt", "enns", "desart")}
        print(y, "result", v["natActual"], "| national", {k: n["fc"] for k, n in v["nat"].items()}, "| chance", {k: n["pDemWin"] and round(n["pDemWin"], 2) for k, n in v["nat"].items()},
              "| D electoral votes", {k: n["demEV"] for k, n in v["nat"].items()}, "| called of 50", called, "| actual by whole states", v["wholeEV"]["dem"])
        if y == "2020":
            print("     missed in 2020:", {k: [a for a, s in st.items() if (s[k]["fc"] > 50) != (s["share"] > 50)] for k in ("bt", "enns", "desart")})
    print("wrote", os.path.normpath(path), os.path.getsize(path), "bytes")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
