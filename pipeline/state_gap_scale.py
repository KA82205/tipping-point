"""How wide are the gaps between states in Civiqs's approval figures, next to the authors' own state estimates?

The approval model was fitted on state approval that its authors estimate themselves from national surveys. The
Nowcast cannot run that estimate, so it takes the gaps between states from Civiqs's tracker instead. This script
measures how the two relate in the two elections where both exist, and what each does to the authors' model run
before the fact. It is where approval.state_gap_scale in config.json comes from.

Needs (none of it is kept in this repository):
  - the authors' replication file, Forecast2024_Replication.dta (doi:10.7910/DVN/PBGFOF)
  - a saved copy of the page source of two Civiqs trackers (open the page, Ctrl+U, save):
      https://civiqs.com/results/approve_president_trump     Trump's first term; the state figures are for January 20, 2021
      https://civiqs.com/results/approve_president_biden     Biden's term; the state figures are for January 20, 2025
    A tracker page gives its state figures for the tracker's last day only, so they are from the end of each
    term, not from the June and July before the election that the authors' estimates describe.

Usage:  python pipeline/state_gap_scale.py /path/to/replication/folder trump_first_term.html biden.html

What it prints (November 20, 2026):
  the authors' gap = 0.56 x Civiqs's gap for Trump in 2020, 0.35 x for Biden in 2024, 0.48 x with both together;
  average state miss of the authors' before-the-fact model, 50 states, national level held the same:
      2020   Civiqs's gaps in full 3.89   at half 3.60   the authors' own numbers 3.75
      2024   Civiqs's gaps in full 1.73   at half 1.16   the authors' own numbers 1.37
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import civiqs  # noqa: E402

BASE = ["lag_PerDem2Party_dev", "Anderson", "Perot2", "democrat_p_state", "lag_democrat_p_state", "democrat_vp_state"]
# The authors' before-the-fact forecast of each year, as in their code (NumericalResults2024.do): fitted on the
# elections before it; the Southern-states term through 2020; approval + 8.2 in 2024 for Vice President Harris.
YEARS = {2020: {"south": True, "vp": 0.0, "baseline": 45.0}, 2024: {"south": False, "vp": 8.2, "baseline": 44.0}}


def fit_and_inputs(R, year):
    spec = YEARS[year]
    cols = BASE + [f"econ_conditions_{year}"] + (["south_conf"] if spec["south"] else [])
    appr = f"pres_approval_{year}"
    tr = R[(R.year >= 1980) & (R.year < year)].dropna(subset=cols + [appr, "PerDem2Party"])
    X = np.column_stack([np.ones(len(tr)), tr[appr].astype(float)] + [tr[c].astype(float) for c in cols])
    b = np.linalg.lstsq(X, tr.PerDem2Party.astype(float).values, rcond=None)[0]
    g = R[(R.year == year) & (R.cstate_initial != "DC")].copy()
    rest = np.column_stack([g[c].astype(float) for c in cols])
    return b, g, rest, appr


def main(folder, pages):
    R = pd.read_stata(os.path.join(folder, "Forecast2024_Replication.dta"))
    pop = json.load(open(os.path.join(HERE, "adult_population.json")))["states"]
    past = json.load(open(os.path.join(HERE, "results_2008_2020.json")))["2020"]
    now = json.load(open(os.path.join(HERE, "results_2024.json")))
    actual = {2020: {a: 100 * v[0] / sum(v) for a, v in past.items()}, 2024: {a: v["share"] for a, v in now.items()}}
    xs, ys = [], []
    for year, path in zip((2020, 2024), pages):
        page = civiqs.read_saved(path)
        civ = {a: v["approve"] for a, v in page["states"].items()}
        b, g, rest, appr = fit_and_inputs(R, year)
        spec, rep = YEARS[year], bool(g.republican_incumbent.iloc[0])
        sign = -1.0 if rep else 1.0                       # the model reads approval signed toward the Democrat
        own = spec["baseline"] + sign * g[appr].astype(float).values    # the authors' approval of the president, in percent
        w = g.cstate_initial.map(pop).values
        mean = lambda v: float((v * w).sum() / w.sum())  # noqa: E731
        c = g.cstate_initial.map(civ).values
        own_gap, civ_gap = own - mean(own), c - mean(c)
        xs.append(civ_gap); ys.append(own_gap)
        print(f"{year}: Civiqs figures for {page['as_of']} | spread across the 50 states: authors {own_gap.std(ddof=1):.2f}, "
              f"Civiqs {civ_gap.std(ddof=1):.2f} | authors' gap = {np.polyfit(civ_gap, own_gap, 1)[0]:.2f} x Civiqs's gap "
              f"(correlation {np.corrcoef(civ_gap, own_gap)[0, 1]:.2f})")
        act = g.cstate_initial.map(actual[year]).values
        lean = g.lag_PerDem2Party_dev.astype(float).values

        def run(label, approval):                          # approval in percent, one value per state
            var = sign * (approval - spec["baseline"]) + spec["vp"]
            fc = b[0] + b[1] * var + rest @ b[2:]
            err = fc - act
            wrong = [a for a, f, r in zip(g.cstate_initial, fc, act) if (f > 50) != (r > 50)]
            print(f"   {label:<34} average state miss {np.abs(err).mean():.2f} | called {50 - len(wrong)} of 50 {' '.join(wrong)}"
                  f" | tilt {np.polyfit(lean, err, 1)[0]:+.3f}")

        run("the authors' own state numbers", own)
        for k in (1.0, 0.5):
            run(f"Civiqs's gaps x {k:g}", mean(own) + k * civ_gap)
    x, y = np.concatenate(xs), np.concatenate(ys)
    print(f"both elections together: the authors' gap = {(x @ y) / (x @ x):.2f} x Civiqs's gap (correlation {np.corrcoef(x, y)[0, 1]:.2f})")
    print("tilt: how much too Democratic the forecast runs for each point a state leans Democratic; above zero means")
    print("Democratic states come out too Democratic and Republican states too Republican.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: python pipeline/state_gap_scale.py /path/to/replication/folder trump_first_term.html biden.html")
    main(sys.argv[1], sys.argv[2:])
