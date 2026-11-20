"""Put an author's own published 2028 forecast on the site.

The final forecast is the average of the two forecasts the authors themselves publish (the Method page, "The final
forecast is the authors' own"). When one comes out, its state forecasts go in a small file here, and from the next
daily run they replace the site's own run of that model:

    desart   Jay DeSart's long-range forecast, expected about a year before the election
    enns     Enns and colleagues' approval and fundamentals forecast, expected about 100 days before it

How to use it:

 1. Get the state forecasts into a table with one row per state: the state (name or two letters) and the number.
    A table in the article or a data file can be saved as CSV as it is. A chart has to be read state by state
    first, as pipeline/extract_fig3_2020.py and pipeline/extract_fig_a2.py did for 2020 and 2024.
 2. Run, from the top of the repository:

        python pipeline/put_in.py desart his_table.csv --published 2027-11-14 --url https://...

    The numbers must be the Democratic share of the two-party vote, in percent. If the table gives something
    else, say so: --values rep (the Republican share of the two-party vote), --values margin (Democratic lead in
    points), or --dem-column and --rep-column (two columns of each party's share of all votes).
    Add what the authors give themselves, if they do: --national 51.2 --electoral-votes 289 --chance 0.61
 3. Read what it prints. It checks that all 50 states are there, that the numbers look like Democratic shares
    (they must follow the 2024 results closely), and shows how far they sit from the site's own run.
 4. Commit the file it wrote, pipeline/published/desart_2028.json. The next run uses it.

What happens then (docs/combine.js): that half of every state's number is the published forecast, held at its
published value. The site's own run of the model is still computed and kept in the daily record (pipeline/log),
marked "site run". The District of Columbia and any state the authors leave out keep the site's own number. Maine's
and Nebraska's districts follow their state, as everywhere on the site. Deleting the file takes the forecast out.

After August 6, 2028 the daily update has stopped, but a forecast put in late still replaces the stand-in for it:
the first run after the file is committed redoes the posted forecast from the inputs frozen that day.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DEFAULTS = {
    "desart": {"short": "DeSart", "authors": "Jay A. DeSart",
               "half": "the long-range half"},
    "enns": {"short": "Enns and colleagues", "authors": "Peter K. Enns and colleagues",
             "half": "the approval and fundamentals half"},
}
EXTRA_NAMES = {"dc": "DC", "d c": "DC", "washington dc": "DC", "washington d c": "DC", "district of columbia": "DC"}


def _key(s):
    return re.sub(r"[^a-z ]", " ", str(s).lower()).split()


def state_codes(results):
    """{name as written in a table: two-letter code}."""
    out = {" ".join(_key(v["name"])): k for k, v in results.items() if len(k) == 2}
    out.update({k.lower(): k for k in results if len(k) == 2})
    out.update(EXTRA_NAMES)
    return out


def _num(x):
    try:
        return float(str(x).replace("%", "").replace(",", ".").replace("−", "-").strip())
    except ValueError:
        return None


def read_table(path, results, values="dem", column=None, dem_column=None, rep_column=None):
    """Read a table of state forecasts. Returns ({abbr: Democratic share of the two-party vote, percent}, notes)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        text = f.read()
    delim = max(",\t;", key=lambda d: text.count(d))
    rows = [r for r in csv.reader(text.splitlines(), delimiter=delim) if any(c.strip() for c in r)]
    codes, notes = state_codes(results), []
    head = None if rows and " ".join(_key(rows[0][0])) in codes else [c.strip().lower() for c in rows[0]]
    body = rows[1:] if head else rows

    def col(spec, what):
        if spec is None:
            return None
        if str(spec).isdigit():
            return int(spec) - 1
        if head and spec.strip().lower() in head:
            return head.index(spec.strip().lower())
        raise SystemExit(f"{what}: no column called {spec!r}. Columns: {head or 'none named; give a number, 1 for the first'}")
    ci, di, ri = col(column, "--column"), col(dem_column, "--dem-column"), col(rep_column, "--rep-column")
    if (di is None) != (ri is None):
        raise SystemExit("--dem-column and --rep-column go together")
    out, unknown = {}, []
    for r in body:
        code = codes.get(" ".join(_key(r[0])))
        if not code:
            unknown.append(r[0].strip())
            continue
        if di is not None:
            d, rp = _num(r[di]), _num(r[ri])
            if d is None or rp is None or d + rp <= 0:
                raise SystemExit(f"{r[0]}: cannot read the two shares")
            v = 100 * d / (d + rp)
        else:
            nums = [(i, _num(c)) for i, c in enumerate(r[1:], 1) if _num(c) is not None]
            if ci is None and len(nums) != 1:
                raise SystemExit(f"{r[0]}: {len(nums)} numbers in the row. Say which column holds the forecast with --column")
            v = _num(r[ci]) if ci is not None else nums[0][1]
            if v is None:
                raise SystemExit(f"{r[0]}: no number in that column")
        if code in out:
            raise SystemExit(f"{r[0]}: listed twice")
        out[code] = v
    if unknown:
        notes.append(f"Rows left out, not a state: {', '.join(unknown[:8])}{' ...' if len(unknown) > 8 else ''}")
    if di is None:
        if values != "margin" and out and max(abs(v) for v in out.values()) <= 1:
            out = {k: 100 * v for k, v in out.items()}
            notes.append("The numbers were fractions; read as percent.")
        if values == "rep":
            out = {k: 100 - v for k, v in out.items()}
        elif values == "margin":
            if out and max(abs(v) for v in out.values()) <= 1:
                out = {k: 100 * v for k, v in out.items()}
                notes.append("The margins were fractions; read as points.")
            out = {k: 50 + v / 2 for k, v in out.items()}
    return {k: round(v, 3) for k, v in out.items()}, notes


def check(states, results):
    """Raise if the numbers cannot be state forecasts of the Democratic two-party share. Returns notes."""
    need = [k for k in results if len(k) == 2 and k != "DC"]
    missing = [k for k in need if k not in states]
    if missing:
        raise SystemExit(f"Missing {len(missing)} of the 50 states: {', '.join(missing)}")
    odd = [k for k, v in states.items() if not 0 < v < 100]
    if odd:
        raise SystemExit(f"Not a share of the vote: {', '.join(f'{k} {states[k]}' for k in odd)}")
    xs, ys = [results[k]["share"] for k in need], [states[k] for k in need]
    mx, my = sum(xs) / 50, sum(ys) / 50
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    if r < -0.5:
        raise SystemExit(f"These run opposite to the 2024 results (correlation {r:.2f}), so they look like Republican "
                         "shares. Use --values rep, or --values margin if they are leads.")
    if r < 0.8:
        raise SystemExit(f"These do not follow the 2024 results (correlation {r:.2f}; published forecasts are near 0.98). "
                         "Check the column and the kind of number (--column, --values).")
    notes = [f"Follows the 2024 results closely (correlation {r:.2f}), as a state forecast should."]
    if "DC" not in states:
        notes.append("No number for the District of Columbia: it keeps the site's own.")
    return notes


def summary(states, results, model=None):
    """Plain lines describing the forecast as the site will read it."""
    st = [k for k in results if len(k) == 2 and k in states]
    tot = sum(results[k]["votes"] for k in st)
    nat = sum(states[k] * results[k]["votes"] for k in st) / tot
    ev = sum(results[k]["ev"] for k in st if states[k] > 50)
    for d in (k for k in results if len(k) == 3):          # Maine's and Nebraska's districts follow their state
        parent = d[:2]
        if parent in states and states[parent] + results[d]["share"] - results[parent]["share"] > 50:
            ev += results[d]["ev"]
    if "DC" not in states:
        ev += results["DC"]["ev"]
    close = sorted((abs(states[k] - 50), k) for k in st)[:6]
    lines = [f"National vote, states added up by their 2024 turnout: {nat:.2f}% Democratic",
             f"Electoral votes with each state to whoever is ahead: {ev} Democratic, {538 - ev} Republican",
             "Closest states: " + ", ".join(f"{k} {states[k]:.1f}" for _, k in close)]
    now = os.path.join(ROOT, "docs", "nowcast.js")
    if os.path.exists(now):
        try:
            text = open(now, encoding="utf-8").read()
            N = json.loads(text[text.index("{"):text.rindex("}") + 1])
            for key, label in (("desart", "long-range"), ("enns", "approval")):
                if model and key != model or (N.get("published") or {}).get(key):
                    continue        # only the model being put in, and only while the site still shows its own run of it
                own = {s["abbr"]: s.get(key) for s in N["states"] if len(s["abbr"]) == 2 and s.get(key) is not None}
                both = [k for k in st if k in own]
                if both:
                    diff = sorted(((states[k] - own[k]), k) for k in both)
                    lines.append(f"Against the site's own {label} run today: {sum(abs(d) for d, _ in diff) / len(both):.1f} points apart in "
                                 f"the average state; furthest {diff[0][1]} {diff[0][0]:+.1f} and {diff[-1][1]} {diff[-1][0]:+.1f}")
        except Exception:  # noqa: BLE001
            pass
    return lines


def build(model, states, published, url=None, title=None, authors=None, short=None, national=None,
          electoral_votes=None, chance=None, read_from="table", note=None, put_in=None):
    dt.date.fromisoformat(published)
    d = DEFAULTS[model]
    out = {"_comment": "An author's own published forecast, put in by hand with pipeline/put_in.py. states: the Democratic "
                       "share of the two-party vote in percent. It replaces the site's own run of this model; deleting "
                       "this file takes it out again.",
           "model": model, "short": short or d["short"], "authors": authors or d["authors"], "title": title,
           "published": published, "put_in": put_in or dt.date.today().isoformat(), "url": url, "read_from": read_from,
           "national": national, "electoral_votes": electoral_votes, "p_dem_win": chance, "note": note,
           "states": dict(sorted(states.items()))}
    return {k: v for k, v in out.items() if v is not None}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Put an author's own published forecast on the site.")
    ap.add_argument("model", choices=sorted(DEFAULTS), help="desart (long-range) or enns (approval and fundamentals)")
    ap.add_argument("table", help="CSV or tab-separated file: the state, then the forecast")
    ap.add_argument("--published", required=True, help="the day the authors made it public, YYYY-MM-DD")
    ap.add_argument("--url", help="where it was published")
    ap.add_argument("--title", help="the title of the article or post")
    ap.add_argument("--authors", help="the authors, as the site should name them in full")
    ap.add_argument("--short", help="how to name them in a sentence (default: DeSart; Enns and colleagues)")
    ap.add_argument("--values", choices=["dem", "rep", "margin"], default="dem",
                    help="what the numbers are: the Democratic two-party share (default), the Republican one, or the Democratic lead")
    ap.add_argument("--column", help="which column holds the forecast, by name or number, when the table has several")
    ap.add_argument("--dem-column", help="with --rep-column: each party's share of all votes, turned into a two-party share")
    ap.add_argument("--rep-column")
    ap.add_argument("--national", type=float, help="the authors' own national Democratic two-party share, if they give one")
    ap.add_argument("--electoral-votes", type=int, help="the authors' own Democratic electoral votes, if they give them")
    ap.add_argument("--chance", type=float, help="the authors' own chance of a Democratic win, 0 to 1, if they give one")
    ap.add_argument("--read-from", choices=["table", "data file", "chart"], default="table")
    ap.add_argument("--note", help="one plain sentence for the Method page, if something needs saying")
    ap.add_argument("--year", type=int)
    ap.add_argument("--out", help="write here instead of pipeline/published/")
    a = ap.parse_args(argv)
    if a.chance is not None and not 0 <= a.chance <= 1:
        sys.exit("--chance is between 0 and 1")

    results = json.load(open(os.path.join(HERE, "results_2024.json")))
    year = a.year or json.load(open(os.path.join(HERE, "config.json")))["election"]["year"]
    states, notes = read_table(a.table, results, a.values, a.column, a.dem_column, a.rep_column)
    notes += check(states, results)
    doc = build(a.model, states, a.published, a.url, a.title, a.authors, a.short, a.national, a.electoral_votes,
                a.chance, a.read_from, a.note)
    path = a.out or os.path.join(HERE, "published", f"{a.model}_{year}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print(f"The {year} forecast by {doc['short']}, published {a.published}: 50 states{' and DC' if 'DC' in states else ''} "
          f"read from {os.path.basename(a.table)}")
    for line in notes + summary(states, results, a.model):
        print("  " + line)
    if a.national is not None or a.electoral_votes is not None or a.chance is not None:
        print("  The authors' own figures: " + ", ".join(x for x in (
            a.national is not None and f"{a.national}% national", a.electoral_votes is not None and f"{a.electoral_votes} electoral votes",
            a.chance is not None and f"{round(100 * a.chance)} in 100") if x))
    print(f"Wrote {a.out or os.path.relpath(path, ROOT)}. Commit it to the repository: from the next run it is "
          f"{DEFAULTS[a.model]['half']} of the Nowcast, and the site's own run stays in the daily record.")


if __name__ == "__main__":
    main()
