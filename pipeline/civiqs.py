"""State-by-state Trump approval from Civiqs's public tracker.

Source: "Donald Trump: Job Approval, Second Term", https://civiqs.com/results/approve_president_trump_2025
(registered voters, modeled daily by Civiqs). The results page carries its own numbers inside the page, in
the block that starts `window.__remixContext = {`; each state has Approve, Disapprove and "Neither approve
nor disapprove" as shares of 1. This module reads that page and keeps the approve share.

Civiqs's site turns automatic reads away (HTTP 403), so the daily run does not ask it. The copy in
pipeline/state_approval.csv is refreshed by hand instead, from a copy of the page saved from a browser:

    python pipeline/civiqs.py "saved page.html"

Save the page's source (Ctrl+U in the browser, then save): it still carries the data block, with the figures to
two decimals. A copy of the page as shown has no data block, only whole percentages; that is read too.

How the Nowcast uses it (pipeline/approval.py, state_source "csv"): only the differences between states are
kept, and each counts at approval.state_gap_scale (one half: the model was fitted on state estimates that sit
about half as far apart, see pipeline/state_gap_scale.py). They are re-centered on the national poll average,
so the national level never comes from Civiqs.
The District of Columbia is not in the tracker and is assumed to sit 24 points below the average of the
50 states (pipeline/update.py).

Used with credit and a link back to the original page, as Civiqs's site terms ask of any reference to its
results (https://civiqs.com/content/terms-of-service). Civiqs licenses what it publishes under Creative Commons
BY-NC-SA 3.0 (https://civiqs.com/survey-terms-of-service). A personal, non-commercial project.
"""
import csv
import json
import os
import re
import sys
import urllib.request

URL = "https://civiqs.com/results/approve_president_trump_2025"
ROUTE = "routes/_app.results_.$question"
MARK = "window.__remixContext = "
STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def fetch(url=URL, timeout=40):
    """One request for the public results page."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "tipping-point-nowcast/1.0 (personal non-commercial project; one request a day; "
                      "https://github.com/KA82205/tipping-point)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(html):
    """Return {"as_of": "YYYY-MM-DD", "states": {abbr: {"approve": %, "disapprove": %}}} for all 50 states.
    Raises ValueError if the page no longer looks the way this expects."""
    i = html.find(MARK)
    if i < 0:
        raise ValueError("Civiqs page: data block not found")
    try:
        ctx, _ = json.JSONDecoder().raw_decode(html, i + len(MARK))
        q = ctx["state"]["loaderData"][ROUTE]
        by_name = q["crosstabs"]["map"]
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Civiqs page: data block not in the expected shape ({e})")
    out = {}
    for name, abbr in STATES.items():
        row = by_name.get(name)
        if not row:
            raise ValueError(f"Civiqs page: no figures for {name}")
        a, d = float(row["Approve"]), float(row["Disapprove"])
        if not (0.05 < a < 0.95 and 0.05 < d < 0.95):
            raise ValueError(f"Civiqs page: implausible figures for {name}")
        out[abbr] = {"approve": round(100 * a, 2), "disapprove": round(100 * d, 2)}
    return {"as_of": str(q.get("end_date") or ""), "states": out}


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def parse_shown(html):
    """The same figures from a copy of the page saved from a browser. A saved copy carries no data block, only
    what the page shows: under "state: <Name>", the shares that approve and disapprove as whole percentages,
    and the day the figures run through. A whole number sits within half a point of the page's own figure.
    Raises ValueError if the copy does not look the way this expects."""
    parts = re.split(r'<span class="font-bold capitalize">state:</span><span>\s*([^<]+?)\s*</span>', html)
    shown = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        row = {}
        for k, v in re.findall(r'<span>(Approve|Disapprove)</span><span class="float-right">(\d+(?:\.\d+)?)%</span>',
                               body[:2500]):
            row.setdefault(k, float(v))
        shown.setdefault(name, row)
    out = {}
    for name, abbr in STATES.items():
        row = shown.get(name) or {}
        if "Approve" not in row or "Disapprove" not in row:
            raise ValueError(f"Civiqs saved page: no figures for {name}")
        a, d = row["Approve"], row["Disapprove"]
        if not (5 < a < 95 and 5 < d < 95 and a + d <= 101):
            raise ValueError(f"Civiqs saved page: implausible figures for {name}")
        out[abbr] = {"approve": a, "disapprove": d}
    day = r'([A-Z][a-z]+) (\d{1,2}), (\d{4})'
    m = (re.search(r'data-testid="crosstabs".{0,600}?<span class="font-light">' + day + '</span>', html, flags=re.S)
         or re.search(r'[\u2014\u2013-]\s*' + day, html))
    if not m or m.group(1) not in MONTHS:
        raise ValueError("Civiqs saved page: the day the figures run through was not found")
    as_of = f"{int(m.group(3)):04d}-{MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    return {"as_of": as_of, "states": out, "rounded": True}


def read_saved(path):
    """A copy of the tracker page saved by hand: its data block if it has one (two decimals), otherwise what
    the page shows (whole percentages)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()
    try:
        return parse(html)
    except ValueError:
        return parse_shown(html)


def write_csv(data, csv_path):
    """state,approve for the 50 states and DC. DC is not in the tracker: it is assumed to sit 24 points below
    the average of the 50 states."""
    rows = {st: v["approve"] for st, v in data["states"].items()}
    rows["DC"] = round(sum(rows.values()) / len(rows) - 24.0, 2)
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "approve"])
        for st in sorted(rows):
            w.writerow([st, rows[st]])


if __name__ == "__main__":
    # Refreshing the copy by hand:
    #   1. open the tracker page (URL above) in a browser, open its source (Ctrl+U) and save that (Ctrl+S)
    #   2. python pipeline/civiqs.py "path/to/saved page.html"
    # This rewrites pipeline/state_approval.csv and the date of the copy in pipeline/config.json.
    if len(sys.argv) != 2:
        sys.exit('usage: python pipeline/civiqs.py "saved page.html"')
    here = os.path.dirname(os.path.abspath(__file__))
    data = read_saved(sys.argv[1])
    write_csv(data, os.path.join(here, "state_approval.csv"))
    with open(os.path.join(here, "config.json"), encoding="utf-8") as f:
        cfg = f.read()
    cfg, n = re.subn(r'("state_csv_as_of"\s*:\s*")[^"]*(")', lambda m: m.group(1) + data["as_of"] + m.group(2), cfg)
    if n != 1:
        sys.exit("config.json: state_csv_as_of not found")
    with open(os.path.join(here, "config.json"), "w", encoding="utf-8") as f:
        f.write(cfg)
    print(f"Civiqs state approval: 50 states through {data['as_of']}"
          + (", whole percentages" if data.get("rounded") else ""))
