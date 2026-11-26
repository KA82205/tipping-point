"""State-by-state Trump approval from Civiqs's public tracker.

Source: "Donald Trump: Job Approval, Second Term", https://civiqs.com/results/approve_president_trump_2025
(registered voters, modeled daily by Civiqs). The results page carries its own numbers inside the page, in
the block that starts `window.__remixContext = {`; each state has Approve, Disapprove and "Neither approve
nor disapprove" as shares of 1. This module reads that page and keeps the approve share.

Civiqs's site turns automatic reads away (HTTP 403) and offers no data service, so the daily run does not ask it. The
copy in pipeline/state_approval.csv is refreshed by hand, every few weeks, from a copy of the page saved from a browser.

The easy way, with nothing but a browser:
    1. open the tracker page (the address above), open its source (Ctrl+U; Cmd+Option+U on a Mac) and save that
       (Ctrl+S; any name)
    2. on GitHub, open pipeline/inbox in this repository, choose "Add file", then "Upload files", drop the saved file
       in and commit
That is all. The commit starts a run, which reads the page (take_in below), checks it, rewrites the copy and its date,
empties the inbox, runs the models again, publishes, and tells The Margin. A page that fails a check changes nothing:
the run is marked failed and pipeline/inbox/LAST.md says why.

From a command line the same thing is:

    python pipeline/civiqs.py "saved page.html"

Either kind of saved copy is read. The page's source (Ctrl+U, then save) carries the data block, with the figures to
two decimals. A copy of the page as shown has no data block, only whole percentages.

What a saved page must pass before it replaces the copy: all 50 states present with believable figures; it is this
tracker and no other Civiqs question; its date is not earlier than the copy's and not in the future; and no state has
moved more than MOVE points from the copy, nor the typical state more than TYPICAL (a different question, or a page
from another presidency, fails these at once).

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
import datetime
import json
import os
import re
import sys
import urllib.request

URL = "https://civiqs.com/results/approve_president_trump_2025"
SLUG = URL.rsplit("/", 1)[1]
MOVE, TYPICAL = 15.0, 6.0   # points a single state, and the typical state, may differ from the copy held and still be believed
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


def held_copy(csv_path):
    """{state: approve} from the copy in the repository."""
    with open(csv_path, newline="") as f:
        return {r["state"]: float(r["approve"]) for r in csv.DictReader(f)}


def vet(data, html, held, held_as_of, today):
    """Is this saved page fit to replace the copy? Raises ValueError with the reason if not."""
    others = set(re.findall(r"civiqs\.com/results/([a-z0-9_]+)", html)) - {SLUG}
    if SLUG not in html and others:
        raise ValueError(f"this is another Civiqs page ({sorted(others)[0]}), not the tracker of Trump's job approval ({SLUG})")
    try:
        day = datetime.date.fromisoformat(data["as_of"])
    except (TypeError, ValueError):
        raise ValueError("the day the figures run through could not be read from the page")
    if held_as_of and day < datetime.date.fromisoformat(held_as_of):
        raise ValueError(f"the page runs through {day}, earlier than the copy already held ({held_as_of})")
    if day > today + datetime.timedelta(days=1):
        raise ValueError(f"the page says it runs through {day}, which has not come yet")
    moves = sorted(abs(v["approve"] - held[st]) for st, v in data["states"].items() if st in held)
    if moves and (moves[-1] > MOVE or moves[len(moves) // 2] > TYPICAL):
        raise ValueError(f"the figures are too far from the copy held to be the same tracker (largest move {moves[-1]:.1f} points, "
                         f"typical {moves[len(moves) // 2]:.1f}); if they are right, use the command line: python pipeline/civiqs.py page.html")
    return moves


def put(data, here):
    """Write the copy and its date."""
    write_csv(data, os.path.join(here, "state_approval.csv"))
    with open(os.path.join(here, "config.json"), encoding="utf-8") as f:
        cfg = f.read()
    cfg, n = re.subn(r'("state_csv_as_of"\s*:\s*")[^"]*(")', lambda m: m.group(1) + data["as_of"] + m.group(2), cfg)
    if n != 1:
        raise ValueError("config.json: state_csv_as_of not found")
    with open(os.path.join(here, "config.json"), "w", encoding="utf-8") as f:
        f.write(cfg)


def take_in(here, today=None):
    """Read whatever page has been left in pipeline/inbox. Returns (state, words): 'empty', 'taken' or 'refused'. The inbox
    is emptied either way, and LAST.md keeps what happened, so a bad page cannot fail every later run."""
    box = os.path.join(here, "inbox")
    names = sorted(n for n in (os.listdir(box) if os.path.isdir(box) else []) if n not in ("README.md", "LAST.md") and not n.startswith("."))
    if not names:
        return "empty", ""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    with open(os.path.join(here, "config.json"), encoding="utf-8") as f:
        held_as_of = json.load(f)["approval"].get("state_csv_as_of")
    held = held_copy(os.path.join(here, "state_approval.csv"))
    best, why = None, []
    for n in names:   # usually one file; a browser's "complete" save adds a folder of images and scripts, which is passed over
        path = os.path.join(box, n)
        if os.path.isdir(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                html = f.read()
            data = read_saved(path)
            moves = vet(data, html, held, held_as_of, today)
            if best is None or data["as_of"] > best[0]["as_of"]:
                best = (data, n, moves)
        except ValueError as e:
            why.append(f"{n}: {e}")
    for n in names:
        path = os.path.join(box, n)
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if best:
        data, n, moves = best
        put(data, here)
        words = (f"Civiqs state approval taken in from {n}: 50 states through {data['as_of']}"
                 + (", whole percentages" if data.get("rounded") else ", two decimals")
                 + (f"; the typical state moved {moves[len(moves) // 2]:.1f} points from the copy of {held_as_of}, the most {moves[-1]:.1f}" if moves else ""))
        state = "taken"
    else:
        words = "The page left in the inbox was not used, and the copy held stays as it was. " + " ".join(why)
        state = "refused"
    with open(os.path.join(box, "LAST.md"), "w", encoding="utf-8") as f:
        f.write(f"# The last page left here\n\n{stamp}: {'taken in' if state == 'taken' else 'refused'}.\n\n{words}\n")
    return state, words


if __name__ == "__main__":
    # Refreshing the copy from a command line:
    #   1. open the tracker page (URL above) in a browser, open its source (Ctrl+U) and save that (Ctrl+S)
    #   2. python pipeline/civiqs.py "path/to/saved page.html"
    # This rewrites pipeline/state_approval.csv and the date of the copy in pipeline/config.json.
    # python pipeline/civiqs.py --inbox is what the workflow runs: it takes in a page uploaded to pipeline/inbox.
    here = os.path.dirname(os.path.abspath(__file__))
    if sys.argv[1:] == ["--inbox"]:
        state, words = take_in(here)
        print(words or "Nothing in the inbox.")
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"state={state}\n")
        if state == "refused":
            print(f"::error::{words}")
        elif state == "taken" and "whole percentages" in words:
            print("::warning::The page was saved as shown, which gives whole percentages. For Civiqs's figures to two decimals, "
                  "save the page's source next time (Ctrl+U, then Ctrl+S).")
        sys.exit(0)
    if len(sys.argv) != 2:
        sys.exit('usage: python pipeline/civiqs.py "saved page.html"   (or --inbox)')
    data = read_saved(sys.argv[1])
    put(data, here)
    print(f"Civiqs state approval: 50 states through {data['as_of']}"
          + (", whole percentages" if data.get("rounded") else ""))
