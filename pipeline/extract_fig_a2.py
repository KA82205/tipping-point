"""Recover the 2024 state forecasts from Figure A-2 of the supplementary appendix.

The figure is vector graphics: each state's simulated distribution is one path drawn
bottom row first. We rebuild each curve, measure its height above the row baseline,
and take the area-weighted mean (point forecast), 5th/95th percentiles and the share of
area above 50% (Democratic win probability).

Checks against the paper: all 56 calls match Figure 2; ratings match (Virginia sits on
the 75% line); 17 states within 5 points and 10 within 2.5 points of 50%, as the text
says; 312 Trump electoral votes.

    pip install pymupdf
    python pipeline/extract_fig_a2.py supplement.pdf > pipeline/forecast_2024_figA2.json
"""
import json
import sys

import pymupdf

ORDER = ("NE3 WV WY ND OK ID AR KY SD AL TN UT NE LA MO IN KS NE1 MT MS SC OH AK IA ME2 TX FL NC "
         "AZ WI PA GA NV MI MN NH NE2 ME DE NM VA OR CO IL NJ RI CT WA ME1 NY HI MD MA VT CA DC").split()
X0, X100 = 253.65, 436.0   # page x of the 0 and 100 tick labels


def main(path):
    page = pymupdf.open(path)[6]
    dots, base = [], []
    for d in page.get_drawings():
        c = tuple(round(v, 2) for v in (d.get("color") or (9,)))
        r = d["rect"]
        if c in ((1.0, 0.4, 0.4), (0.0, 0.0, 1.0)):
            dots.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        elif c == (0.5, 0.5, 0.5):
            base.append(round(r.y0, 2))
    bl = sorted(set(base))
    curves, cur = [], []
    for x, y in dots:
        if cur and (x < cur[-1][0] - 1.0 or x > cur[-1][0] + 5):
            curves.append(cur); cur = []
        cur.append((x, y))
    curves.append(cur)
    curves = [c for c in curves if len(c) > 100]
    out = {}
    for k, (st, c) in enumerate(zip(ORDER, curves)):
        b = bl[len(bl) - 1 - k]
        pts = sorted(((x - X0) / (X100 - X0) * 100, max(0.0, b - y)) for x, y in c)
        area = mom = 0.0; cdf = []
        for (x0, h0), (x1, h1) in zip(pts, pts[1:]):
            a = (x1 - x0) * (h0 + h1) / 2
            area += a; mom += a * (x0 + x1) / 2; cdf.append((x1, area))
        q = lambda p: next(x for x, ca in cdf if ca >= p * area)  # noqa: E731
        below50 = next((ca for x, ca in cdf if x >= 50), area)
        out[st] = {"mean": round(mom / area, 2), "lo": round(q(0.05), 1), "hi": round(q(0.95), 1),
                   "pDem": round(1 - below50 / area, 3)}
    json.dump(out, sys.stdout, indent=0)


if __name__ == "__main__":
    main(sys.argv[1])
