"""Reproduces the track record on the site's Method page from the two papers' replication files.

Download the replication data (not stored in this repository) into one folder:
  Enns, Colner, Kumar & Lagodny (2024), doi:10.7910/DVN/PBGFOF   ->  Forecast2024_Replication.dta
  DeSart (2025), doi:10.7910/DVN/HZGLY9                          ->  DeSart_PS_2024_Long-Range_Forecast_Data.sav
                                                                    DeSart_PS_2024_Forecast_11-5-23.sav
Then:  python pipeline/backtest_2008_2024.py /path/to/that/folder      (needs numpy, pandas, pyreadstat)

What it does
  1. One-step-ahead back-test, 2008-2024: each election is forecast by each model refitted on the elections
     before it only, with that year's inputs; the Nowcast is the plain average of the two, state by state.
  2. Leave-one-out test, 1996-2024: each election forecast from all the other elections.
  3. Baselines: every state votes as it did last time; the national vote repeats.
  4. How the simulated uncertainty did: the site simulates the average with the approval model's error
     (a shared national error plus a state error). Here the same error model is applied to each back-test
     forecast, with the error size the approval model had at the time, to see how often results fell inside
     the stated ranges and how often the stated odds came true. Coefficient draws are left out, so the ranges
     here are slightly narrower than the site's.
Shares are Democratic shares of the two-party vote. National figures add up the 50 states by turnout.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import pyreadstat

HERE = os.path.dirname(os.path.abspath(__file__))


def find(folder, pattern):
    hits = sorted(glob.glob(os.path.join(folder, pattern)))
    if not hits:
        sys.exit(f"Could not find {pattern} in {folder}. See the top of this file for where to download it.")
    return hits[0]


def load(folder):
    res = json.load(open(os.path.join(HERE, "results_2024.json")))
    name2ab = {v["name"]: k for k, v in res.items() if len(k) == 2}
    d = pd.read_stata(find(folder, "*Forecast2024_Replication.dta"))
    d["PerDem2Party"] = d["PerDem2Party"].astype("float64")
    d.loc[d.year == 2024, "PerDem2Party"] = d.loc[d.year == 2024, "State"].map(lambda s: res[name2ab[s]]["share"])
    tr, _ = pyreadstat.read_sav(find(folder, "*2024_Long-Range_Forecast_Data.sav"))
    fc, _ = pyreadstat.read_sav(find(folder, "*Forecast_11-5-23.sav"))
    # DeSart's 2024 row: his October 2023 poll average and terms, the actual nominees' home states, the result.
    f = fc[fc.State != "DC"].copy()
    f["Home"] = f.State.map({"California": 1, "Florida": -1, "Delaware": -1, "New York": 1}).fillna(0)
    f["Result"] = f.State.map(lambda s: res[name2ab[s]]["share"])
    f["RegimeAge"], f["NatlPoll"], f["Year"] = f.Terms, f.Polls, 2024
    f["ecvotes"] = f.State.map(lambda s: res[name2ab[s]]["ev"])
    votes = f.State.map(lambda s: res[name2ab[s]]["votes"])
    f["TOweight"] = votes / votes.sum()
    cols = ["State", "Year", "Result", "Previous", "NatlPoll", "Home", "RegimeAge", "TOweight", "ecvotes"]
    D = pd.concat([tr[cols], f[cols]], ignore_index=True)
    return d, D


# ---- the approval and fundamentals model (Enns et al.) ----
VP_ADJ = {1988: 5, 2000: -8.5, 2024: 8.2}     # the authors' vice-president adjustments to approval
ENNS = ["lag_PerDem2Party_dev", "APP", "ECON", "Anderson", "Perot2", "democrat_p_state", "lag_democrat_p_state", "democrat_vp_state"]


def enns(d, year, train, final=False):
    """Forecast `year` from the elections in `train`. One-step-ahead uses the approval and economy variables
    the authors built for that forecast year; `final` uses the 2024 versions (economic weighting 0.55, with
    2020 rescaled as in their code), for the leave-one-out test."""
    t = d.copy()
    if final:
        c = "Cwt_55_d_"
        t[c] = np.where(t.republican_incumbent == 1, -t[c], t[c])
        sd = np.mean([t.loc[t.year == y, c].std() for y in (2008, 2012, 2016)])
        sel = t.year == 2020
        m20 = t.loc[sel, c].mean()
        t.loc[sel, c] = (t.loc[sel, c] - m20) / t.loc[sel, c].std() * sd + m20
        t["APP"], t["ECON"] = t["pres_approval_2024"].astype(float), t[c].astype(float)
    else:
        t["APP"], t["ECON"] = t[f"pres_approval_{year}"].astype(float), t[f"econ_conditions_{year}"].astype(float)
    a = t[t.year.isin(train)].dropna(subset=ENNS + ["PerDem2Party"])
    X = np.column_stack([a[ENNS].astype(float).values, np.ones(len(a))])
    b, *_ = np.linalg.lstsq(X, a.PerDem2Party.values, rcond=None)
    resid = a.PerDem2Party.values - X @ b
    rmse = float(np.sqrt(resid @ resid / (len(a) - X.shape[1])))
    te = t[t.year == year].copy()
    te["APP"] += VP_ADJ.get(year, 0)
    te["enns"] = np.column_stack([te[ENNS].astype(float).values, np.ones(len(te))]) @ b
    return te[["State", "enns"]], rmse


# ---- the long-range model (DeSart) ----
def desart(D, year, train):
    X = lambda t: np.column_stack([np.ones(len(t)), t.Previous, t.NatlPoll, t.Home, t.RegimeAge])  # noqa: E731
    a = D[D.Year.isin(train)]
    b, *_ = np.linalg.lstsq(X(a), a.Result.values, rcond=None)
    te = D[D.Year == year].copy()
    te["desart"] = X(te) @ b
    return te[["State", "Result", "Previous", "TOweight", "ecvotes", "desart"]]


def frame(d, D, mode):
    rows = []
    years = range(2008, 2025, 4) if mode == "onestep" else range(1996, 2025, 4)
    for y in years:
        if mode == "onestep":
            e, rmse = enns(d, y, range(1980, y, 4))
            ds = desart(D, y, range(1996, y, 4))
        else:
            e, rmse = enns(d, y, [t for t in range(1980, 2025, 4) if t != y], final=True)
            ds = desart(D, y, [t for t in range(1996, 2025, 4) if t != y])
        m = ds.merge(e, on="State")
        m["year"], m["rmse"] = y, rmse
        rows.append(m)
    A = pd.concat(rows, ignore_index=True)
    A["avg"] = (A.enns + A.desart) / 2
    return A


def nat(g, col):
    return float((g[col] * g.TOweight).sum() / g.TOweight.sum())


def summary(A, title):
    print(f"\n== {title}: {A.year.nunique()} elections, {len(A)} state results ==")
    print(f"{'':6}{'result':>8}{'approval':>10}{'long-rng':>10}{'Nowcast':>9}   states called of 50 (approval, long-range, Nowcast)   Dem EV of 535: Nowcast, actual")
    for y, g in A.groupby("year"):
        called = [int(((g[c] > 50) == (g.Result > 50)).sum()) for c in ("enns", "desart", "avg")]
        ev, aev = int(g.loc[g.avg > 50, "ecvotes"].sum()), int(g.loc[g.Result > 50, "ecvotes"].sum())
        print(f"{y:6}{nat(g, 'Result'):8.1f}{nat(g, 'enns'):10.1f}{nat(g, 'desart'):10.1f}{nat(g, 'avg'):9.1f}   {called[0]:>3} {called[1]:>3} {called[2]:>3}{'':38}{ev:>4} {aev:>4}")
    for c, name in (("enns", "approval and fundamentals"), ("desart", "long-range"), ("avg", "Nowcast (average)")):
        err = A[c] - A.Result
        ok = (A[c] > 50) == (A.Result > 50)
        nm = np.mean([abs(nat(g, c) - nat(g, "Result")) for _, g in A.groupby("year")])
        # Winner: a majority of the 538 electoral votes, with the District of Columbia's 3 counted as Democratic.
        win = sum(((g.loc[g[c] > 50, "ecvotes"].sum() + 3) >= 270) == ((g.loc[g.Result > 50, "ecvotes"].sum() + 3) >= 270) for _, g in A.groupby("year"))
        print(f"  {name:26} state miss {err.abs().mean():.2f}   called {int(ok.sum())}/{len(A)} ({100 * ok.mean():.1f}%)   national miss {nm:.2f}   winners {win}/{A.year.nunique()}")


def baselines(A):
    print("\n== Baselines, 2008-2024 ==")
    close = (A.Result - 50).abs() < 5
    same = (A.Previous > 50) == (A.Result > 50)
    ok = (A.avg > 50) == (A.Result > 50)
    print(f"  Every state votes as last time:  called {int(same.sum())}/{len(A)} ({100 * same.mean():.1f}%);  Nowcast {int(ok.sum())}/{len(A)} ({100 * ok.mean():.1f}%)")
    print(f"  States decided by under 10 points ({int(close.sum())} results):  as last time {int(same[close].sum())}/{int(close.sum())} ({100 * same[close].mean():.0f}%);  Nowcast {int(ok[close].sum())}/{int(close.sum())} ({100 * ok[close].mean():.0f}%)")
    flipped = ~same
    print(f"  States that changed party ({int(flipped.sum())} results):  Nowcast called {int(ok[flipped].sum())}")
    print(f"  State miss:  last result {(A.Previous - A.Result).abs().mean():.2f} points;  Nowcast {(A.avg - A.Result).abs().mean():.2f}")
    nb = np.mean([abs(nat(g, "Previous") - nat(g, "Result")) for _, g in A.groupby("year")])
    nn = np.mean([abs(nat(g, "avg") - nat(g, "Result")) for _, g in A.groupby("year")])
    print(f"  National miss:  last election's vote {nb:.2f} points;  Nowcast {nn:.2f}")


def calibration(A, n=20000, seed=2028):
    """The site's error model on each back-test forecast: for each of seven draws of the correlation
    (0.70 to 0.97) a shared national error and a state error, total size the approval model's RMSE then."""
    print("\n== How the simulated uncertainty did, 2008-2024 ==")
    rng = np.random.default_rng(seed)
    z = (A.Result - A.avg) / A.rmse
    for lvl, k in ((50, 0.674), (80, 1.282), (90, 1.645)):
        print(f"  Stated {lvl}% range: {100 * (z.abs() < k).mean():.0f}% of the {len(A)} state results fell inside")
    print(f"  Size of the error: the simulation assumes {A.groupby('year').rmse.first().mean():.2f} points per state on average; the Nowcast's actual misses had a root mean square of {np.sqrt(((A.Result - A.avg) ** 2).mean()):.2f}")
    probs, outcome, rows = [], [], []
    for y, g in A.groupby("year"):
        sd, pt, ev = g.rmse.iloc[0], g.avg.values, g.ecvotes.values
        wins, dem = np.zeros(len(g)), 0
        for _ in range(7):
            u = rng.uniform(0.70, 0.97)
            sh = pt + np.sqrt(u) * sd * rng.standard_normal((n, 1)) + np.sqrt(1 - u) * sd * rng.standard_normal((n, len(g)))
            w = sh > 50
            wins += w.sum(axis=0)
            dem += ((w * ev).sum(axis=1) + 3 >= 270).sum()
        p_state = wins / (7 * n)
        probs += list(p_state)
        outcome += list((g.Result > 50).values)
        won = (g.loc[g.Result > 50, "ecvotes"].sum() + 3) >= 270
        rows.append((y, dem / (7 * n), won))
    print("  Chance given to the Democrat, and what happened:")
    for y, p, won in rows:
        print(f"    {y}: {100 * p:.0f} in 100;  the {'Democrat' if won else 'Republican'} won")
    brier = np.mean([(p - won) ** 2 for _, p, won in rows])
    print(f"    Brier score {brier:.3f} (0.25 is a coin flip, 0 is perfect; five elections)")
    probs, outcome = np.array(probs), np.array(outcome)
    fav = np.maximum(probs, 1 - probs)                       # the chance given to whoever was ahead in the state
    hit = (probs > 0.5) == outcome
    print("  State ratings: how often the candidate ahead won")
    for name, lo, hi in (("Toss-up (up to 55 in 100)", 0, 0.55), ("Lean (55 to 75)", 0.55, 0.75), ("Likely (75 to 98)", 0.75, 0.98), ("Solid (over 98)", 0.98, 1.01)):
        m = (fav > lo) & (fav <= hi) if lo else fav <= hi
        if m.sum():
            print(f"    {name:28} {int(m.sum()):>3} states   average chance stated {100 * fav[m].mean():.0f}%   won {int(hit[m].sum())} ({100 * hit[m].mean():.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    d, D = load(sys.argv[1])
    one = frame(d, D, "onestep")
    summary(one, "One-step-ahead back-test, 2008-2024")
    summary(frame(d, D, "loo"), "Leave-one-out test, 1996-2024")
    baselines(one)
    calibration(one)
