"""Recover Enns and Lagodny's published 2020 state forecasts from Figure 3 of their article.

Enns, Peter K., and Julius Lagodny. 2021. "Forecasting the 2020 Electoral College Winner: The State
Presidential Approval/State Economy Model." PS: Political Science & Politics 54 (1). doi:10.1017/S1049096520001407

The article prints its state forecasts only as a chart (Figure 3, "Simulated 2020 Forecast by State"). The chart is
vector graphics: every simulated outcome is a dot, drawn state by state from the bottom row up, with about 1,146
dots for each electoral vote. For each state this script takes the dots' average (the point forecast), their 5th
and 95th percentiles and the share above 50% (the state's chance of going Democratic).

Figure 2 is a histogram of the simulated electoral votes; the share of its bars to the right of the 269 line is
the published chance of a Democratic win.

Checks against the article's text, all of which pass:
  - the 25 rows drawn in dark blue are the 25 with an average above 50%, and they add up to 290 electoral votes;
  - weighted by turnout the averages give a national vote of 54.5%;
  - the histogram gives a Biden win in 59% of simulations ("slightly less than 60%") and 19% of simulations at
    exactly 268 electoral votes ("almost one in five");
  - the rows come out in the order the chart lists them, to within the noise of a few thousand dots (0.1 points).

The District of Columbia runs off the right edge of the chart at 100%, so only part of it is drawn. Its forecast is
worked out from the part that shows, assuming the bell shape of the other rows, and is marked as an estimate.

    pip install pymupdf
    python pipeline/extract_fig3_2020.py article.pdf > pipeline/forecast_2020_fig3.json
"""
import json
import sys
from statistics import NormalDist

import pymupdf

# Rows of Figure 3 from the top, and each one's electoral votes as printed beside it.
ROWS = ("DC MA HI CA VT MD NY IL DE RI CT NJ WA ME NH OR NM CO MI MN PA VA NV WI AZ FL IA OH AK GA NC MT TX KS SC "
        "MO TN LA NE IN SD MS ND UT AL WV KY AR OK ID WY").split()
EV = dict(DC=3, MA=11, HI=4, CA=55, VT=3, MD=10, NY=29, IL=20, DE=3, RI=4, CT=7, NJ=14, WA=12, ME=4, NH=4, OR=7, NM=5,
          CO=9, MI=16, MN=10, PA=20, VA=13, NV=6, WI=10, AZ=11, FL=29, IA=6, OH=18, AK=3, GA=16, NC=15, MT=3, TX=38,
          KS=6, SC=9, MO=10, TN=11, LA=8, NE=5, IN=11, SD=3, MS=6, ND=3, UT=6, AL=9, WV=5, KY=8, AR=6, OK=7, ID=4, WY=3)
BLUE, RED = (0.224, 0.325, 0.643), (0.949, 0.4, 0.404)
X0, X100 = 235.94, 409.86      # page x of the 0 and 100 ticks of Figure 3
H0, H500, H269 = 169.36, 436.87, 313.28   # page x of the 0 and 500 ticks and of the 269 line of Figure 2


def pct(v, q):
    return v[min(len(v) - 1, int(q * len(v)))]


def states(page):
    dots = []
    for d in page.get_drawings():
        c = tuple(round(v, 3) for v in (d.get("color") or ()))
        r = d["rect"]
        if c in (BLUE, RED) and r.x1 - r.x0 < 0.1:        # the wide marks are the dashed 269 lines
            dots.append((c == BLUE, ((r.x0 + r.x1) / 2 - X0) / (X100 - X0) * 100))
    rows, cur = [], [dots[0]]
    for d in dots[1:]:
        if d[1] < cur[-1][1] - 0.6:                        # x starts again from the left: the next state up
            rows.append(cur)
            cur = []
        cur.append(d)
    rows.append(cur)
    assert len(rows) == 51, len(rows)
    out, per_ev = {}, []
    for st, row in zip(reversed(ROWS), rows):
        xs = sorted(x for _, x in row)
        blue = row[0][0]
        assert all(b == blue for b, _ in row), st
        mean = sum(xs) / len(xs)
        cell = {"fc": round(mean, 2), "lo": round(pct(xs, 0.05), 1), "hi": round(pct(xs, 0.95), 1),
                "pDem": round(sum(x > 50 for x in xs) / len(xs), 3), "blue": blue, "dots": len(xs)}
        if st != "DC":
            per_ev.append(len(xs) / EV[st])
            assert blue == (mean > 50), st
        out[st] = cell
    # The District of Columbia: only the part of its bell below 100% is drawn.
    k = sum(per_ev) / len(per_ev)
    shown = out["DC"]["dots"] / (k * EV["DC"])
    nd = NormalDist()
    a = nd.inv_cdf(shown)
    sd = (100 - out["DC"]["fc"]) / (a + nd.pdf(a) / shown)
    mu = 100 - a * sd
    out["DC"].update(fc=round(mu, 1), lo=round(mu - 1.645 * sd, 1), hi=100.0, pDem=1.0, estimated=True)
    assert max(per_ev) / min(per_ev) < 1.06, (min(per_ev), max(per_ev))
    assert sum(EV[s] for s, c in out.items() if c["blue"]) == 290
    return out, round(k, 1)


def chance(page):
    bars = []
    for d in page.get_drawings():
        f = tuple(round(v, 3) for v in (d.get("fill") or ()))
        r = d["rect"]
        if f == (0.137, 0.122, 0.125) and d.get("type") == "f" and 656 < r.y1 < 657 and r.x1 - r.x0 < 1.2 and r.y0 > 440:
            bars.append((r.x0, r.x1, r.y1 - r.y0))
    total = sum(h for _, _, h in bars)
    win = sum(h for x0, _, h in bars if x0 >= H269 - 0.01) / total
    tie_side = max(bars, key=lambda b: b[2])
    ev_of = lambda x: (x - H0) / (H500 - H0) * 500   # noqa: E731
    return round(win, 4), round(tie_side[2] / total, 4), round(ev_of(tie_side[1]))


def main(path):
    doc = pymupdf.open(path)
    st, per_ev = states(doc[3])
    p_win, p_268, at = chance(doc[2])
    assert at == 269 and 0.58 < p_win < 0.60 and 0.18 < p_268 < 0.20, (p_win, p_268, at)
    json.dump({
        "_comment": "Enns and Lagodny's published 2020 forecast (PS 2021, doi:10.1017/S1049096520001407). national and "
                    "electoral_votes are the article's own figures. p_dem_win is the share of the simulations in its "
                    "Figure 2 with 270 or more Democratic electoral votes. states are read from the dots of its Figure 3 "
                    "by pipeline/extract_fig3_2020.py: fc the average, lo and hi the 5th and 95th percentiles, pDem the "
                    "share above 50. They are accurate to about a tenth of a point. DC is an estimate (see the script).",
        "national": 54.5, "electoral_votes": 290, "p_dem_win": p_win, "p_268": p_268, "dots_per_electoral_vote": per_ev,
        "states": {s: {k: v for k, v in c.items() if k not in ("blue", "dots")} for s, c in sorted(st.items())},
    }, sys.stdout, indent=0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
