"""State economic conditions, as in Enns et al. (2024) Appendix 2.

Monthly percent change in the Philadelphia Fed State Coincident Index, each month
weighted delta**(15 - q) where q is the quarter of the presidency (q = 1 is the
first quarter, q = 14 the April-June quarter of the election year). The value is
the weighted average of the monthly changes.
"""
import json
import os
import urllib.parse
import urllib.request

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY",
          "LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND",
          "OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"]

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def month_index(ym):
    y, m = map(int, ym[:7].split("-"))
    return y * 12 + (m - 1)


def fetch_fred(series_id, api_key, start="2024-12-01"):
    """Return [(YYYY-MM, value)] for a FRED series. Missing values ('.') are skipped."""
    qs = urllib.parse.urlencode({"series_id": series_id, "api_key": api_key,
                                 "file_type": "json", "observation_start": start})
    with urllib.request.urlopen(f"{FRED_URL}?{qs}", timeout=30) as r:
        obs = json.load(r)["observations"]
    return [(o["date"][:7], float(o["value"])) for o in obs if o["value"] not in (".", "")]


def weighted_change(series, term_start, end_month, delta, nowcast=True):
    """series: [(YYYY-MM, index)] sorted, including the month before term_start.

    Returns (value, last_month_used). If data stop before end_month and nowcast is
    True, quarters are shifted so the latest available quarter gets the top weight
    (delta**1), i.e. 'as if the election-year June were the latest month'.
    """
    s = dict(series)
    t0, t_end = month_index(term_start), month_index(end_month)
    months = sorted(m for m in s if t0 <= month_index(m) <= t_end)
    if not months:
        raise ValueError("no data in window")
    last_q = (month_index(months[-1]) - t0) // 3 + 1
    shift = (14 - last_q) if nowcast else 0
    num = den = 0.0
    for m in months:
        prev_i = month_index(m) - 1
        prev = next((v for k, v in s.items() if month_index(k) == prev_i), None)
        if prev is None:
            continue
        pct = 100.0 * (s[m] / prev - 1.0)
        q = (month_index(m) - t0) // 3 + 1 + shift
        w = delta ** (15 - q)
        num += w * pct
        den += w
    return num / den, months[-1]


def build_economy(cfg, api_key=None, cache_dir=None, fetch=fetch_fred):
    """Return {delta: {state: value}}, last_month, raw series. Signed toward the Democrat if configured."""
    e, el = cfg["economy"], cfg["election"]
    start = f"{int(el['term_start_month'][:4]) - 1}-12-01"
    raw = {}
    for st in STATES:
        sid = e["fred_series_template"].format(state=st)
        raw[st] = fetch(sid, api_key, start)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            with open(os.path.join(cache_dir, f"{sid}.json"), "w") as f:
                json.dump(raw[st], f)
    sign = -1.0 if (e.get("signed_by_incumbent_party") and el["incumbent_party"] == "R") else 1.0
    out, last = {}, None
    for d in e["delta_grid"]:
        vals = {}
        for st in STATES:
            v, last_m = weighted_change(raw[st], el["term_start_month"], el["economy_end_month"], d)
            vals[st] = sign * v
            last = last_m if last is None or last_m < last else last
        a, b = e["dc_from"]
        vals["DC"] = (vals[a] + vals[b]) / 2
        out[d] = vals
    return out, last, raw
