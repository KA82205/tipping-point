"""State-by-state Trump approval from Civiqs's public tracker.

Source: "Donald Trump: Job Approval, Second Term", https://civiqs.com/results/approve_president_trump_2025
(registered voters, modeled daily by Civiqs). The results page carries its own numbers inside the page, in
the block that starts `window.__remixContext = {`; each state has Approve, Disapprove and "Neither approve
nor disapprove" as shares of 1. This module reads that page and keeps the approve share.

Civiqs's site turns automatic reads away (HTTP 403) and offers no data service, so the daily run does not ask it. The
copy in pipeline/state_approval.csv is refreshed by hand, every few weeks, from a copy of the page saved from a browser.

The way it is done, with nothing but a browser (docs/civiqs.html, https://ka82205.github.io/tipping-point/civiqs.html):
    1. open the tracker page (the address above), open its source (Ctrl+U; Cmd+Option+U on a Mac) and save that
       (Ctrl+S; any name)
    2. give the saved file to the converter page. It reads the file inside the browser, sends it nowhere, and makes a
       data file: state,approve,as_of,source, fifty lines
    3. the converter's button opens GitHub with that file filled in under pipeline/inbox; commit it
That is all. The commit starts a run, which reads the data file (take_in below), checks it, rewrites the copy and its
date, empties the inbox, runs the models again, publishes, and tells The Margin. A file that fails a check changes
nothing: the run is marked failed and pipeline/inbox/LAST.md says why.

A saved page itself is not taken in, and should not be uploaded. It carries everything Civiqs's site sends a browser,
scripts and settings and the keys for outside services its site uses, and a file committed to a public repository stays
in its history after it is deleted. The inbox removes one unread and says so.

On your own computer, where nothing is uploaded, a saved page can still be read directly:

    python pipeline/civiqs.py "saved page.html"

What the figures must pass before they replace the copy: the data file exactly in its form (read_clean below); all 50
states present with believable figures; it is this tracker and no other Civiqs question; its date is not earlier than the copy's and not in the future; and no state has
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


CLEAN_HEAD = ["state", "approve", "as_of", "source"]
CLEAN_MAX = 8000   # bytes; the real file is about 3,400
CONVERTER = "https://ka82205.github.io/tipping-point/civiqs.html"


def read_clean(path):
    """The data file the converter page makes: state,approve,as_of,source and one line for each of the 50 states, nothing
    else. Everything about it is checked, because it is the only thing the inbox takes: its size, that it is plain text,
    its heading, each state once, a percentage with at most two decimals, one date, and this tracker as the source.
    Raises ValueError with the reason."""
    with open(path, "rb") as f:
        raw = f.read(CLEAN_MAX + 1)
    if len(raw) > CLEAN_MAX:
        raise ValueError("too large to be the data file")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        raise ValueError("not the data file: it has characters a file of codes and figures cannot have")
    if not re.fullmatch(r"[A-Za-z0-9_.,:/\-\r\n]*", text):
        raise ValueError("not the data file: it has characters a file of codes and figures cannot have")
    lines = text.replace("\r\n", "\n").strip("\n").split("\n")
    if lines[0].split(",") != CLEAN_HEAD:
        raise ValueError("not the data file: the first line should be " + ",".join(CLEAN_HEAD))
    out, days = {}, set()
    for line in lines[1:]:
        cells = line.split(",")
        if len(cells) != 4:
            raise ValueError(f"a line does not have four parts: {line[:40]}")
        st, a, day, src = cells
        if st not in STATES.values():
            raise ValueError(f"{st[:12]} is not one of the 50 states")
        if st in out:
            raise ValueError(f"{st} is there twice")
        if not re.fullmatch(r"\d{1,2}(\.\d{1,2})?", a) or not 5 < float(a) < 95:
            raise ValueError(f"the figure for {st} is not a believable percentage with at most two decimals")
        if not re.fullmatch(r"\d{4}-\d\d-\d\d", day):
            raise ValueError(f"the date on the line for {st} is not a date")
        if src != URL:
            raise ValueError("the source named is not the tracker of Trump's job approval")
        out[st] = {"approve": float(a)}
        days.add(day)
    missing = sorted(set(STATES.values()) - set(out))
    if missing:
        raise ValueError(f"{len(missing)} of the 50 states are missing ({', '.join(missing[:5])})")
    if len(days) != 1:
        raise ValueError("the lines do not all carry the same date")
    return {"as_of": days.pop(), "states": out}


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
    """Are these figures fit to replace the copy? Raises ValueError with the reason if not. html is the saved page they
    were read from, or None for the data file, whose source line read_clean has already checked."""
    others = set(re.findall(r"civiqs\.com/results/([a-z0-9_]+)", html or "")) - {SLUG}
    if html is not None and SLUG not in html and others:
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
                         f"typical {moves[len(moves) // 2]:.1f}); if they are right, a person has to put them in: python pipeline/civiqs.py page.html, on a computer")
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
    """Read the data file left in pipeline/inbox. Returns (state, words): 'empty', 'taken' or 'refused'. Only the
    converter's data file (.csv) is read. Anything else, a saved page above all, is removed unread: it should not be in
    a public repository. The inbox is emptied either way and LAST.md keeps what happened, so a bad file cannot fail
    every later run."""
    import shutil
    box = os.path.join(here, "inbox")
    names = sorted(n for n in (os.listdir(box) if os.path.isdir(box) else []) if n not in ("README.md", "LAST.md") and not n.startswith("."))
    if not names:
        return "empty", ""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    with open(os.path.join(here, "config.json"), encoding="utf-8") as f:
        held_as_of = json.load(f)["approval"].get("state_csv_as_of")
    held = held_copy(os.path.join(here, "state_approval.csv"))
    best, why, unread = None, [], 0
    for n in names:
        path = os.path.join(box, n)
        if os.path.isdir(path) or not n.lower().endswith(".csv"):
            unread += 1
            continue
        try:
            data = read_clean(path)
            moves = vet(data, None, held, held_as_of, today)
            if best is None or data["as_of"] > best[0]["as_of"]:
                best = (data, n, moves)
        except ValueError as e:
            why.append(f"{n[:60]}: {e}.")
    for n in names:
        path = os.path.join(box, n)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    raw = ((f"{unread} other file{'s' if unread != 1 else ''} left here {'were' if unread != 1 else 'was'} removed without being read. "
            f"Only the data file is taken in: a saved page carries the site's own scripts and the keys of services it uses, which do "
            f"not belong in a public repository, and deleting it here does not take it out of the repository's history. "
            f"Make the data file at {CONVERTER} and upload that.") if unread else "")
    if best:
        data, n, moves = best
        put(data, here)
        words = (f"Civiqs state approval taken in from {n}: 50 states through {data['as_of']}, two decimals"
                 + (f"; the typical state moved {moves[len(moves) // 2]:.1f} points from the copy of {held_as_of}, the most {moves[-1]:.1f}" if moves else "")
                 + (". " + raw if raw else ""))
        state = "taken"
    else:
        words = ("Nothing left in the inbox was used, and the copy held stays as it was. " + " ".join(why) + (" " if why and raw else "") + raw).strip()
        state = "refused"
    with open(os.path.join(box, "LAST.md"), "w", encoding="utf-8") as f:
        f.write(f"# The last file left here\n\n{stamp}: {'taken in' if state == 'taken' else 'refused'}.\n\n{words}\n")
    return state, words


if __name__ == "__main__":
    # python pipeline/civiqs.py --inbox is what the workflow runs: it takes in the data file uploaded to pipeline/inbox.
    # On a computer, with nothing uploaded, a saved page or a data file can be put in directly:
    #   python pipeline/civiqs.py "path/to/saved page.html"      (or the converter's .csv)
    # This rewrites pipeline/state_approval.csv and the date of the copy in pipeline/config.json.
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
        elif state == "taken" and "removed without being read" in words:
            print("::warning::A file other than the data file was left in the inbox and removed unread. " + CONVERTER + " makes the data file.")
        sys.exit(0)
    if len(sys.argv) != 2:
        sys.exit('usage: python pipeline/civiqs.py "saved page.html"   (or the data file .csv, or --inbox)')
    data = read_clean(sys.argv[1]) if sys.argv[1].lower().endswith(".csv") else read_saved(sys.argv[1])
    put(data, here)
    print(f"Civiqs state approval: 50 states through {data['as_of']}"
          + (", whole percentages" if data.get("rounded") else ""))
