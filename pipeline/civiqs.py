"""State-by-state Trump approval from Civiqs's public tracker.

Source: "Donald Trump: Job Approval, Second Term", https://civiqs.com/results/approve_president_trump_2025
(registered voters, modeled daily by Civiqs). The results page carries its own numbers inside the page, in
the block that starts `window.__remixContext = {`; each state has Approve, Disapprove and "Neither approve
nor disapprove" as shares of 1. This module reads that page once a day and keeps the approve share.

How the Nowcast uses it (pipeline/approval.py, state_source "csv"): only the differences between states are
kept. They are re-centered on the national poll average, so the national level never comes from Civiqs.
The District of Columbia is not in the tracker and is assumed to sit 24 points below the average of the
50 states (pipeline/update.py).

Used with credit and a link back to the original page, as Civiqs's site terms ask of any reference to its
results (https://civiqs.com/content/terms-of-service). A personal, non-commercial project.
"""
import json
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
