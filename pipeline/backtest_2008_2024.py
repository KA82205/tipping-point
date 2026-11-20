"""Reproduces the track record and the checks on the site's Method page from the two papers' replication files.

Download the replication data (not stored in this repository) into one folder:
  Enns, Colner, Kumar & Lagodny (2024), doi:10.7910/DVN/PBGFOF   ->  Forecast2024_Replication.dta
  DeSart (2025), doi:10.7910/DVN/HZGLY9                          ->  DeSart_PS_2024_Long-Range_Forecast_Data.sav
                                                                    DeSart_PS_2024_Forecast_11-5-23.sav
Then:  python pipeline/backtest_2008_2024.py /path/to/that/folder      (needs numpy, pandas, pyreadstat)

What it does
  0. Check against the paper: the approval model's one-step-ahead forecasts of 1984-2020, run exactly as the
     authors' code runs them (NumericalResults2024.do), must reproduce the accuracy the paper reports.
  1. One-step-ahead back-test, 2008-2024: each election is forecast by each model refitted on the elections
     before it only, with that year's inputs; the Nowcast is the plain average of the two, state by state.
     For the approval model these are the authors' own before-the-fact forecasts: their code keeps a term for
     the eleven Southern states in the forecasts of every election through 2020, and their 2024 forecast
     drops it (paper, "third update", and online appendix 3). The site follows that since November 20, 2026;
     until then it left the term out of every year, which called 236 of the 250 state results, not 239.
  2. Leave-one-out test, 1996-2024: each election forecast from all the other elections.
  3. Baselines: every state votes as it did last time; the national vote repeats.
  4. How the simulated uncertainty did: the site simulates the average with the approval model's error
     (a shared national error plus a state error). Here the same error model is applied to each back-test
     forecast, with the error size the approval model had at the time, to see how often results fell inside
     the stated ranges and how often the stated odds came true. Coefficient draws are left out, so the ranges
     here are slightly narrower than the site's.
  5. Other weights: every mix of the two models in steps of five points, on both tests. The best mix in
     hindsight, the best mix in each election, and whether a mix fitted on some elections beats equal weights
     on an election it has not seen.
  6. States moving together: how well each model places states relative to the national vote, two other
     designs for the long-range equation, and where the long-range model's 2020 miss came from.
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
SOUTH_UNTIL = 2020                              # the authors' before-the-fact forecasts keep south_conf through this election


def enns(d, year, train, final=False, south=None):
    """Forecast `year` from the elections in `train`. One-step-ahead uses the approval and economy variables
    the authors built for that forecast year, and their Southern-states term for forecast years through 2020,
    as their code does; `final` uses the 2024 versions (economic weighting 0.55, with 2020 rescaled as in
    their code, no Southern-states term), for the leave-one-out test. `south` overrides the term's use."""
    cols = ENNS + (["south_conf"] if (south if south is not None else (not final and year <= SOUTH_UNTIL)) else [])
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
    a = t[t.year.isin(train)].dropna(subset=cols + ["PerDem2Party"])
    X = np.column_stack([a[cols].astype(float).values, np.ones(len(a))])
    b, *_ = np.linalg.lstsq(X, a.PerDem2Party.values, rcond=None)
    resid = a.PerDem2Party.values - X @ b
    rmse = float(np.sqrt(resid @ resid / (len(a) - X.shape[1])))
    te = t[t.year == year].copy()
    te["APP"] += VP_ADJ.get(year, 0)
    te["enns"] = np.column_stack([te[cols].astype(float).values, np.ones(len(te))]) @ b
    return te[["State", "enns"]], rmse


def paper_check(d):
    """The paper (Historical Accuracy): the model 'correctly predicts the winner in 91% of all states from 1984
    to 2020', with a one-step-ahead mean absolute error of 3.4 points and its largest miss in Arkansas in 1992
    (16 points); 'since 2000' 95% and 2.8 points, which the authors' code computes over 2004-2020. All contests
    count here, the District of Columbia included, as in their code."""
    rows = []
    for y in range(1984, 2021, 4):
        e, _ = enns(d, y, range(1980, y, 4))
        m = e.merge(d.loc[d.year == y, ["State", "PerDem2Party"]], on="State")
        m["year"] = y
        rows.append(m)
    A = pd.concat(rows, ignore_index=True)
    A["ok"], A["miss"] = (A.enns > 50) == (A.PerDem2Party > 50), A.enns - A.PerDem2Party
    late, worst = A[A.year >= 2004], A.loc[A.miss.abs().idxmax()]
    print("== Check against the paper: the approval model's own before-the-fact forecasts, 1984-2020 ==")
    print(f"  1984-2020: called {100 * A.ok.mean():.1f}% of {len(A)} (paper: 91%), average miss {A.miss.abs().mean():.2f} (paper: 3.4)")
    print(f"  2004-2020: called {100 * late.ok.mean():.1f}% of {len(late)} (paper: 95%), average miss {late.miss.abs().mean():.2f} (paper: 2.8)")
    print(f"  Largest miss: {worst.State} {int(worst.year)}, {worst.miss:+.1f} (paper: Arkansas 1992, 16 points too low)")
    print("  2020 misses: " + ", ".join(A.loc[(A.year == 2020) & ~A.ok, "State"]) + " (paper: every state except Georgia)")
    if round(100 * A.ok.mean()) != 91 or round(100 * late.ok.mean()) != 95 or worst.State != "Arkansas" or int(worst.year) != 1992:
        sys.exit("FAIL: the approval model's back-test no longer reproduces the paper's reported accuracy")


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


# ---- other weights than half each ----
MIXES = [round(0.05 * i, 2) for i in range(21)]      # the approval and fundamentals model's share of the average


def mix_scores(A):
    """For every mix and election: average state miss, national miss, and whether the winner was called."""
    S = {}
    for w in MIXES:
        fc = w * A.enns + (1 - w) * A.desart
        S[w] = {}
        for y, g in A.groupby("year"):
            f = fc.loc[g.index]
            natl = abs(float((f * g.TOweight).sum() / g.TOweight.sum()) - nat(g, "Result"))
            won = ((g.loc[f > 50, "ecvotes"].sum() + 3) >= 270) == ((g.loc[g.Result > 50, "ecvotes"].sum() + 3) >= 270)
            S[w][int(y)] = {"state": float((f - g.Result).abs().mean()), "natl": natl, "won": bool(won)}
    return S


def mix_avg(S, w, measure, years=None):
    return float(np.mean([S[w][y][measure] for y in (years or sorted(S[w]))]))


def best_mix(S, measure, years=None):
    return min(MIXES, key=lambda w: mix_avg(S, w, measure, years))


def weights(S, title):
    """Every mix from the long-range model alone (0) to the approval and fundamentals model alone (1)."""
    years = sorted(S[0.5])
    wrong = lambda w: ", ".join(str(y) for y in years if not S[w][y]["won"]) or "none"  # noqa: E731
    print(f"\n== Other weights, {title} ==")
    print(f"  {'mix':>5}{'state miss':>12}{'national miss':>15}{'winners':>9}     (mix = the approval and fundamentals model's share; 0.50 is the Nowcast)")
    for w in MIXES:
        print(f"  {w:5.2f}{mix_avg(S, w, 'state'):12.3f}{mix_avg(S, w, 'natl'):15.3f}{sum(S[w][y]['won'] for y in years):>7}/{len(years)}")
    for measure, name in (("state", "state results"), ("natl", "the national vote")):
        b = best_mix(S, measure)
        print(f"  Best mix in hindsight for {name}: {b:.2f}, a miss of {mix_avg(S, b, measure):.3f} against {mix_avg(S, 0.5, measure):.3f} at equal weights")
        print(f"    winner called wrong: {wrong(b)} (at equal weights: {wrong(0.5)})")
        print("    best mix in each election: " + ", ".join(f"{y} {best_mix(S, measure, [y]):.2f}" for y in years))


def fitted_weights(scores):
    """Would weights fitted to past results have beaten equal weights? The mix is chosen on some elections and
    scored on one it has not seen: chosen from all the other elections, or from the earlier ones only."""
    print("\n== Fitted weights against equal weights ==")
    tally = {"worse": 0, "the same": 0, "better": 0}
    for title, S in scores:
        years = sorted(S[0.5])
        for how in ("all the other elections", "the earlier elections only"):
            for measure, name in (("state", "state miss"), ("natl", "national miss")):
                fit, equal, used = [], [], []
                for i, y in enumerate(years):
                    pool = [t for t in years if t != y] if how.startswith("all") else years[:i]
                    if pool:
                        w = best_mix(S, measure, pool)
                        fit.append(S[w][y][measure])
                        equal.append(S[0.5][y][measure])
                        used.append(f"{y} {w:.2f}")
                gap = np.mean(fit) - np.mean(equal)
                verdict = "the same" if abs(gap) < 0.01 else "worse" if gap > 0 else "better"
                tally[verdict] += 1
                print(f"  {title}, mix chosen from {how}, {name}: fitted {np.mean(fit):.3f}, equal weights {np.mean(equal):.3f}: {verdict}")
                print(f"      mix used: {', '.join(used)}")
    print(f"  Fitted weights did worse than equal weights in {tally['worse']} of {sum(tally.values())} comparisons, the same (within 0.01 points) in {tally['the same']} and better in {tally['better']}")
    title, S = scores[-1]                                 # the longer test: fitted on its first half, scored on its second
    years = sorted(S[0.5])
    early, late = years[:len(years) // 2], years[len(years) // 2:]
    w = best_mix(S, "state", early)
    print(f"  {title}: the best mix on {early[0]}-{early[-1]} was {w:.2f}; on {late[0]}-{late[-1]} its state miss is {mix_avg(S, w, 'state', late):.2f} against {mix_avg(S, 0.5, 'state', late):.2f} at equal weights")


# ---- states moving together ----
def map_miss(A, col):
    """How far each state's position relative to the national vote was off, on average: the miss in the map,
    leaving out the miss in the national vote."""
    return float(np.mean([((g[col] - nat(g, col)) - (g.Result - nat(g, "Result"))).abs().mean() for _, g in A.groupby("year")]))


def moving_together(d, D, tests):
    """The long-range model moves every state by nearly the same amount from its last result. Is that beaten?"""
    print("\n== States moving together ==")
    print("  Miss in each state's position relative to the national vote (points):")
    for title, A in tests:
        print(f"    {title}: same swing in every state {map_miss(A, 'Previous'):.2f};  long-range {map_miss(A, 'desart'):.2f};  approval and fundamentals {map_miss(A, 'enns'):.2f};  Nowcast {map_miss(A, 'avg'):.2f}")
    spread = D.assign(swing=D.Result - D.Previous).groupby("Year").swing.std()
    print("  Spread of state swings since the previous election (standard deviation, points): " + ", ".join(f"{int(y)} {s:.2f}" for y, s in spread.items()))
    # Two other designs for the long-range equation, fitted and scored the same way. Results two elections back
    # come from the approval model's data, which starts in 1980.
    share = {(s, int(y)): v for s, y, v in zip(d.State, d.year, d.PerDem2Party)}
    E = D.copy()
    E["Previous2"] = [share[(s, int(y) - 8)] for s, y in zip(E.State, E.Year)]
    E["Last2"] = (E.Previous + E.Previous2) / 2
    rest = ["NatlPoll", "Home", "RegimeAge"]
    designs = (("as published: the last result", ["Previous"] + rest),
               ("adding the result two elections back", ["Previous", "Previous2"] + rest),
               ("starting from the average of the last two results", ["Last2"] + rest))
    for title, A in tests:
        years = sorted(A.year.unique())
        print(f"  Long-range equation, {title}:")
        for name, cols in designs:
            X = lambda t: np.column_stack([np.ones(len(t))] + [t[c].values for c in cols])  # noqa: E731
            rows, second = [], []
            for y in years:
                # the one-step test starts in 2008 and fits on earlier elections only; the other fits on all the rest
                train = range(1996, y, 4) if years[0] == 2008 else [t for t in range(1996, 2025, 4) if t != y]
                a, te = E[E.Year.isin(train)], E[E.Year == y].copy()
                b, *_ = np.linalg.lstsq(X(a), a.Result.values, rcond=None)
                te["fc"], te["year"] = X(te) @ b, y
                rows.append(te)
                second.append(b[2])
            F = pd.concat(rows, ignore_index=True)
            nm = np.mean([abs(nat(g, "fc") - nat(g, "Result")) for _, g in F.groupby("year")])
            note = f"   (fitted weight on the result two elections back: {min(second):+.2f} to {max(second):+.2f})" if "Previous2" in cols else ""
            print(f"    {name:50} state miss {(F.fc - F.Result).abs().mean():.2f}   called {int(((F.fc > 50) == (F.Result > 50)).sum())}/{len(F)}   national miss {nm:.2f}   map miss {map_miss(F, 'fc'):.2f}{note}")
    # Where the long-range model's 2020 miss came from (its back-test forecast for 2020 is the one DeSart published).
    one = tests[0][1]
    g = one[one.year == 2020]
    err = g.desart - g.Result
    a = D[D.Year.isin(range(1996, 2020, 4))]
    b, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(a)), a.Previous, a.NatlPoll, a.Home, a.RegimeAge]), a.Result.values, rcond=None)
    poll, fc, res = float(D.loc[D.Year == 2020, "NatlPoll"].iloc[0]), nat(g, "desart"), nat(g, "Result")
    print(f"  2020, long-range model: national forecast {fc:.1f}, result {res:.1f}; {100 * err.mean() ** 2 / (err ** 2).mean():.0f}% of its squared state error was a miss shared by every state")
    print(f"    Its October 2019 polls had the Democrat at {poll:.1f}. Had they shown the result, the forecast would have been {fc - b[2] * (poll - res):.1f}: the polls account for {b[2] * (poll - res):.1f} of the {fc - res:.1f} points")


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
    paper_check(d)
    one, loo = frame(d, D, "onestep"), frame(d, D, "loo")
    summary(one, "One-step-ahead back-test, 2008-2024")
    summary(loo, "Leave-one-out test, 1996-2024")
    baselines(one)
    tests = (("One-step-ahead back-test, 2008-2024", one), ("Leave-one-out test, 1996-2024", loo))
    scores = [(title, mix_scores(A)) for title, A in tests]
    for title, S in scores:
        weights(S, title)
    fitted_weights(scores)
    moving_together(d, D, tests)
    calibration(one)
