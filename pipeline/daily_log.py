"""A daily record of the Nowcast, kept for later research. Nothing on the site reads it.

Every run of pipeline/update.py that is not a test run writes here:

  pipeline/log/days/YYYY-MM-DD.json   the whole Nowcast as it stood at the end of that day (a later run on the same
                                      day replaces it), with every poll in the approval average, the settings and
                                      a fingerprint of the code and data files that decide the numbers
  pipeline/log/daily.csv              one row a day: the headline numbers and the inputs behind them
  pipeline/log/states.csv             one row a day for every state and district
  pipeline/log/changes.csv            one row for each run in which something changed, saying what in plain words:
                                      polls in or out, a new month of state economies, a new copy of the state
                                      approval figures (refreshed by hand), a setting, the code

Two sets of numbers are kept side by side. The plain columns are what the site shows. The columns that start
with site_run are the site's own runs of the two published models. Until an author's own 2028 forecast is put on
the site (pipeline/put_in.py) the two sets are the same. From then on the plain columns hold the authors' forecast
for that model (approval_model_from / long_range_from say "authors' forecast") and the site_run columns go on
holding the site's own run. After the election that allows three things to be compared with the result: the
authors' forecasts, the site's own runs on the day before each was published, and the site's own runs on the last
day. (Decided November 20, 2026.)
"""
import csv
import datetime as dt
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG_DIR = os.path.join(HERE, "log")

# The files that decide the numbers. A change in any of them is noted in changes.csv.
CODE_FILES = ["pipeline/update.py", "pipeline/approval.py", "pipeline/economy.py", "pipeline/candidates.py",
              "pipeline/run_forecast.js", "docs/engine.js", "docs/combine.js"]
DATA_FILES = ["pipeline/state_approval.csv", "pipeline/adult_population.json", "pipeline/candidates.json"]

FOLDER_NOTE = """# The daily record

Kept for later research. Nothing on the site reads these files. The daily run writes them
(`pipeline/daily_log.py`); do not edit them by hand.

- `daily.csv`: one row a day. The Democrat's chance, the popular vote, the electoral count, each model on its
  own, and the inputs behind them. Opens in Excel.
- `states.csv`: one row a day for every state and district.
- `changes.csv`: one row each time something changed, saying what: polls in or out, a new month of state
  economies, a new copy of the state approval figures, a setting, the code.
- `days/`: the whole Nowcast as it stood at the end of each day.

Days are US Eastern dates. The record starts on November 20, 2026.

Two sets of numbers sit side by side. The plain columns are what the site shows. The columns that start with
`site_run` are the site's own runs of the two models. Until an author's own 2028 forecast is put on the site the
two sets are the same. From then on the plain columns hold the authors' forecast for that model (the columns
`approval_model_from` and `long_range_from` say so) and the `site_run` columns keep the site's own run. After the
election that allows a three-way comparison with the result: the authors' forecasts, the site's own runs on the
day before each was published, and the site's own runs on the last day.
"""

DAILY_FIELDS = ["date", "last_run_utc", "mode", "dem_win", "tie", "dem_popular_vote", "dem_electoral_votes",
                "approval_model_dem_win", "approval_model_dem_popular_vote", "approval_model_from",
                "long_range_dem_win", "long_range_dem_popular_vote", "long_range_from",
                "trump_approve", "trump_disapprove", "approval_pollsters", "approval_polls",
                "approval_window_start", "approval_window_end",
                "head_to_head_dem_average", "head_to_head_matchups", "economy_through",
                "vp_adjustment", "vp_gap_measured", "vp_polls", "vp_weight",
                "state_approval_copy", "state_gap_scale", "dem_nominee", "rep_nominee",
                "site_run_dem_win", "site_run_dem_popular_vote", "site_run_dem_electoral_votes",
                "site_run_approval_model_dem_win", "site_run_approval_model_dem_popular_vote",
                "site_run_long_range_dem_win", "site_run_long_range_dem_popular_vote"]
STATE_FIELDS = ["date", "state", "electoral_votes", "nowcast_dem_share", "dem_win", "rating",
                "approval_model_dem_share", "approval_model_dem_win", "long_range_dem_share", "long_range_dem_win",
                "trump_approval_used", "economy",
                "site_run_nowcast_dem_share", "site_run_dem_win",
                "site_run_approval_model_dem_share", "site_run_long_range_dem_share"]
CHANGE_FIELDS = ["time_utc", "date", "dem_win_before", "dem_win_after", "what_changed"]


def settings(cfg, prefix=""):
    """The settings as one flat {name: value}, without the notes (keys that start with an underscore)."""
    out = {}
    for k, v in cfg.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            out.update(settings(v, prefix + k + "."))
        else:
            out[prefix + k] = v
    return out


def file_ids(root=ROOT, names=tuple(CODE_FILES + DATA_FILES)):
    """{file: a short fingerprint of its contents} for the files that decide the numbers."""
    out = {}
    for n in names:
        p = os.path.join(root, n)
        if os.path.exists(p):
            with open(p, "rb") as f:
                out[n] = hashlib.sha1(f.read()).hexdigest()[:10]
    return out


def _day(iso, year=False):
    d = dt.date.fromisoformat(str(iso)[:10])
    return f"{d:%B} {d.day}, {d.year}" if year else f"{d:%b} {d.day}"


def _month(ym):
    return f"{dt.date.fromisoformat(ym + '-15'):%B %Y}"


def _some(items, limit=4):
    items = list(items)
    return ", ".join(items[:limit]) + (f" and {len(items) - limit} more" if len(items) > limit else "")


def _pct(x):
    return "none" if x is None else f"{x:.1f}%"


def _in_out(came, went):
    return "".join(f"; {word}: {_some(names)}" for word, names in (("in", came), ("out", went)) if names)


def describe_changes(prev, cur):
    """What differs between two records, in plain sentences. Empty when nothing that matters changed."""
    a, b = prev["nowcast"], cur["nowcast"]
    out = []

    # The approval average: which polls are in it, and where it stands.
    key = lambda p: (p.get("pollster"), p.get("date"), p.get("population"), p.get("approve"), p.get("disapprove"), p.get("n"))  # noqa: E731
    pa = prev.get("approval_polls") or a["approval"].get("polls") or []
    pb = cur.get("approval_polls") or b["approval"].get("polls") or []
    name = lambda p: f"{p.get('pollster')} to {_day(p['date'])}"  # noqa: E731
    came = [name(p) for p in pb if key(p) not in {key(q) for q in pa}]
    went = [name(p) for p in pa if key(p) not in {key(q) for q in pb}]
    la, lb = a["approval"].get("approve"), b["approval"].get("approve")
    if came or went or la != lb:
        level = f"{_pct(lb)} approve (was {_pct(la)})" if la != lb else f"still {_pct(lb)} approve"
        out.append(f"Approval average: {level}{_in_out(came, went) or ', same polls a day older'}.")

    # Head-to-head polls.
    key = lambda p: (p.get("pollster"), p.get("date"), p.get("d"), p.get("r"), p.get("share"))  # noqa: E731
    ha, hb = (a.get("h2h") or {}).get("polls") or [], (b.get("h2h") or {}).get("polls") or []
    name = lambda p: f"{p.get('pollster')} {_day(p['date'])} ({p.get('d')} v {p.get('r')})"  # noqa: E731
    came = [name(p) for p in hb if key(p) not in {key(q) for q in ha}]
    went = [name(p) for p in ha if key(p) not in {key(q) for q in hb}]
    ma, mb = (a.get("models") or {}).get("polls") or {}, (b.get("models") or {}).get("polls") or {}
    if came or went or ma != mb:
        now = f"Democrats average {_pct(mb.get('avg'))} in {mb.get('n', 0)} matchups" if mb else "none in the window"
        was = f"{_pct(ma.get('avg'))} in {ma.get('n', 0)}" if ma else "none"
        out.append(f"Head-to-head polls: {now} (was {was}){_in_out(came, went)}.")

    # State economies.
    ea, eb = (a.get("economy") or {}).get("through"), (b.get("economy") or {}).get("through")
    econ = lambda n: {s["abbr"]: s.get("econ") for s in n.get("states") or []}  # noqa: E731
    if ea != eb:
        out.append(f"State economies: now through {_month(eb)} (was {_month(ea)}).")
    elif econ(a) != econ(b):
        out.append("State economy figures revised by their source, same month.")

    # The copy of the state approval figures, which is refreshed by hand.
    sa, sb = a["approval"].get("state_data") or {}, b["approval"].get("state_data") or {}
    if sa.get("as_of") != sb.get("as_of") or sa.get("name") != sb.get("name"):
        out.append(f"State approval figures refreshed: {sb.get('name') or 'no source'} copy of "
                   f"{_day(sb['as_of'], True) if sb.get('as_of') else 'no date'} "
                   f"(was {_day(sa['as_of'], True) if sa.get('as_of') else 'none'}).")
    elif prev.get("files", {}).get("pipeline/state_approval.csv") != cur.get("files", {}).get("pipeline/state_approval.csv"):
        out.append("State approval figures changed without a new date.")

    # The vice-president adjustment.
    va, vb = a.get("vp") or {}, b.get("vp") or {}
    pick = lambda v: tuple(v.get(k) for k in ("gap", "raw_gap", "polls", "weight", "kind", "applied"))  # noqa: E731
    gap = lambda v: "none" if v.get("gap") is None else f"{v['gap']:+.1f}"  # noqa: E731
    if pick(va) != pick(vb):
        out.append(f"Vice-president adjustment: {gap(vb)} points (was {gap(va)}); {vb.get('basis') or 'no polls'}.")

    # Who is running.
    if a.get("tickets") != b.get("tickets"):
        who = lambda side, role: (((b.get("tickets") or {}).get(side) or {}).get(role) or {}).get("name") or "not chosen"  # noqa: E731
        out.append(f"Tickets: Democrats {who('dem', 'president')} and {who('dem', 'vp')}; "
                   f"Republicans {who('rep', 'president')} and {who('rep', 'vp')}.")
    if a.get("sitting_vp") != b.get("sitting_vp"):
        out.append(f"Sitting vice president: {b.get('sitting_vp')} (was {a.get('sitting_vp')}).")
    ca = {c["name"]: c for c in (a.get("scenario") or {}).get("candidates") or []}
    cb = {c["name"]: c for c in (b.get("scenario") or {}).get("candidates") or []}
    if set(cb) - set(ca):
        out.append(f"Candidates added: {_some(sorted(set(cb) - set(ca)))}.")
    if set(ca) - set(cb):
        out.append(f"Candidates dropped: {_some(sorted(set(ca) - set(cb)))}.")
    if any(ca[n].get("primary") != cb[n].get("primary") for n in set(ca) & set(cb)):
        vp, note = b.get("sitting_vp"), ""
        if vp in ca and vp in cb and ca[vp].get("primary") != cb[vp].get("primary"):
            note = f": {vp} at {_pct(cb[vp].get('primary'))} of his party's field (was {_pct(ca[vp].get('primary'))})"
        out.append(f"Primary polling updated{note}.")

    # The calendar switches.
    if a.get("mode") != b.get("mode"):
        out.append("The approval model now uses the paper's window, polls conducted June 1 to July 30, 2028."
                   if b.get("mode") == "official" else f"Mode: {b.get('mode')} (was {a.get('mode')}).")
    if not (a.get("desart_final") or {}).get("frozen") and (b.get("desart_final") or {}).get("frozen"):
        out.append("The long-range model's polls are now fixed: those conducted in October 2027.")
    # An author's own published forecast put in, corrected or taken out.
    half = {"desart": "long-range", "enns": "approval"}
    pa, pb = a.get("published") or {}, b.get("published") or {}
    for m in ("desart", "enns"):
        who = (pb.get(m) or pa.get(m) or {}).get("short") or (pb.get(m) or pa.get(m) or {}).get("authors") or m
        if m in pb and m not in pa:
            out.append(f"The {half[m]} half is now the forecast {who} published on {_day(pb[m]['published'], True)}, "
                       "put in by hand; the site's own run of that model stays in the site_run columns.")
        elif m in pa and m not in pb:
            out.append(f"The forecast {who} published was taken out; the {half[m]} half is the site's own run again.")
        elif m in pa and pa[m] != pb[m]:
            out.append(f"The forecast {who} published was corrected.")

    # Settings, code and data files.
    s0, s1 = prev.get("settings") or {}, cur.get("settings") or {}
    diff = [f"{k} {json.dumps(s0.get(k)) if k in s0 else '(not set)'} to {json.dumps(s1.get(k)) if k in s1 else '(removed)'}"
            for k in sorted(set(s0) | set(s1)) if s0.get(k) != s1.get(k) or (k in s0) != (k in s1)]
    if diff:
        out.append(f"Settings changed: {_some(diff, 6)}.")
    f0, f1 = prev.get("files") or {}, cur.get("files") or {}
    code = [n for n in CODE_FILES if f0.get(n) != f1.get(n)]
    data = [n for n in DATA_FILES if f0.get(n) != f1.get(n) and n != "pipeline/state_approval.csv"]
    if code:
        out.append(f"Code changed: {_some(code, 8)}.")
    if data:
        out.append(f"Data file changed: {_some(data, 8)}.")

    if not out and (a.get("summary") or {}).get("pDemWin") != (b.get("summary") or {}).get("pDemWin"):
        out.append("No new data: the polls are a day older, which shifts their weights a little."
                   if prev.get("date") != cur.get("date") else
                   "The numbers moved with none of the listed inputs changing; most likely a correction in one of the feeds.")
    return out


def _upsert(path, fields, rows, day):
    """Rewrite a table with this day's rows replacing any it already had. Columns added later go on the right."""
    header, old = list(fields), []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            have = list(r.fieldnames or [])
            header = have + [c for c in fields if c not in have]
            old = [x for x in r if x.get("date") != day]
    rows = old + [{k: ("" if v is None else v) for k, v in row.items()} for row in rows]
    rows.sort(key=lambda x: x["date"])          # a stable sort: the states keep their order within a day
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def record(payload, cfg, today, approval_polls=None, own=None, log_dir=LOG_DIR, root=ROOT):
    """Write the day's record. Returns what changed since the last record, as sentences (empty: nothing changed).
    own: the site's own runs ({"summary", "models", "states"}) when an author's published forecast has replaced
    one of them on the site; left out, the site's own runs are what the site shows."""
    day = today.isoformat()
    days_dir = os.path.join(log_dir, "days")
    os.makedirs(days_dir, exist_ok=True)
    cur = {"date": day, "nowcast": payload, "settings": settings(cfg), "files": file_ids(root)}
    if approval_polls is not None and len(approval_polls) > len(payload["approval"].get("polls") or []):
        cur["approval_polls"] = approval_polls       # the site's copy shows the first 25 only
    if own:
        cur["own"] = own

    earlier = sorted(f for f in glob.glob(os.path.join(days_dir, "*.json")) if os.path.basename(f)[:10] <= day)
    prev = None
    if earlier:
        with open(earlier[-1], encoding="utf-8") as f:
            prev = json.load(f)
    changes = ["Record starts."] if prev is None else describe_changes(prev, cur)

    with open(os.path.join(days_dir, day + ".json"), "w", encoding="utf-8") as f:
        json.dump(cur, f, separators=(",", ":"))

    N, s, m, ap, vp = payload, payload["summary"], payload.get("models") or {}, payload["approval"], payload.get("vp") or {}
    sd, src = ap.get("state_data") or {}, payload.get("model_sources") or {}
    polls_avg = m.get("polls") or {}
    who = lambda side: (((N.get("tickets") or {}).get(side) or {}).get("president") or {}).get("name")  # noqa: E731
    model = lambda k, f: (m.get(k) or {}).get(f)  # noqa: E731
    # The site's own runs: given separately once an author's forecast is in, otherwise what the site shows.
    o = own or {"summary": s, "models": m, "states": N.get("states") or []}
    os_, om = o["summary"], o.get("models") or {}
    omodel = lambda k, f: (om.get(k) or {}).get(f)  # noqa: E731
    own_state = {x["abbr"]: x for x in o.get("states") or []}
    _upsert(os.path.join(log_dir, "daily.csv"), DAILY_FIELDS, [{
        "date": day, "last_run_utc": N.get("generated_at"), "mode": N.get("mode"),
        "dem_win": round(s["pDemWin"], 4), "tie": round(s["pTie"], 4),
        "dem_popular_vote": round(s["demPopular"], 2), "dem_electoral_votes": s["demEvPoint"],
        "approval_model_dem_win": model("enns", "pDemWin"), "approval_model_dem_popular_vote": model("enns", "demPopular"),
        "approval_model_from": src.get("enns", "site run"),
        "long_range_dem_win": model("desart", "pDemWin"), "long_range_dem_popular_vote": model("desart", "demPopular"),
        "long_range_from": src.get("desart", "site run"),
        "trump_approve": ap.get("approve"), "trump_disapprove": ap.get("disapprove"),
        "approval_pollsters": ap.get("pollsters"), "approval_polls": len(cur.get("approval_polls") or ap.get("polls") or []),
        "approval_window_start": (ap.get("window") or [None, None])[0], "approval_window_end": (ap.get("window") or [None, None])[1],
        "head_to_head_dem_average": polls_avg.get("avg"), "head_to_head_matchups": polls_avg.get("n"),
        "economy_through": (N.get("economy") or {}).get("through"),
        "vp_adjustment": vp.get("gap"), "vp_gap_measured": vp.get("raw_gap"), "vp_polls": vp.get("polls"), "vp_weight": vp.get("weight"),
        "state_approval_copy": sd.get("as_of"), "state_gap_scale": sd.get("gap_scale"),
        "dem_nominee": who("dem"), "rep_nominee": who("rep"),
        "site_run_dem_win": round(os_["pDemWin"], 4), "site_run_dem_popular_vote": round(os_["demPopular"], 2),
        "site_run_dem_electoral_votes": os_["demEvPoint"],
        "site_run_approval_model_dem_win": omodel("enns", "pDemWin"), "site_run_approval_model_dem_popular_vote": omodel("enns", "demPopular"),
        "site_run_long_range_dem_win": omodel("desart", "pDemWin"), "site_run_long_range_dem_popular_vote": omodel("desart", "demPopular"),
    }], day)
    r4 = lambda x: None if x is None else round(x, 4)  # noqa: E731
    _upsert(os.path.join(log_dir, "states.csv"), STATE_FIELDS, [{
        "date": day, "state": x["abbr"], "electoral_votes": x.get("ev"), "nowcast_dem_share": x.get("demShare"),
        "dem_win": r4(x.get("pDem")), "rating": x.get("rating"),
        "approval_model_dem_share": x.get("enns"), "approval_model_dem_win": r4(x.get("ennsP")),
        "long_range_dem_share": x.get("desart"), "long_range_dem_win": r4(x.get("desartP")),
        "trump_approval_used": x.get("approve"), "economy": x.get("econ"),
        "site_run_nowcast_dem_share": (own_state.get(x["abbr"]) or {}).get("demShare"),
        "site_run_dem_win": r4((own_state.get(x["abbr"]) or {}).get("pDem")),
        "site_run_approval_model_dem_share": (own_state.get(x["abbr"]) or {}).get("enns"),
        "site_run_long_range_dem_share": (own_state.get(x["abbr"]) or {}).get("desart"),
    } for x in N.get("states") or []], day)

    if changes:
        path = os.path.join(log_dir, "changes.csv")
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CHANGE_FIELDS)
            if new:
                w.writeheader()
            w.writerow({"time_utc": N.get("generated_at"), "date": day,
                        "dem_win_before": "" if prev is None else round(prev["nowcast"]["summary"]["pDemWin"], 4),
                        "dem_win_after": round(s["pDemWin"], 4), "what_changed": " ".join(changes)})

    note, have = os.path.join(log_dir, "README.md"), None
    if os.path.exists(note):
        with open(note, encoding="utf-8") as f:
            have = f.read()
    if have != FOLDER_NOTE:
        with open(note, "w", encoding="utf-8") as f:
            f.write(FOLDER_NOTE)
    return changes
