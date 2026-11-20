"""Presidential approval inputs.

National level: an average of public polls from the VoteHub Polling API
(api.votehub.com, CC BY 4.0). One entry per pollster (its latest poll in the
window), weighted by sample size and recency. Internal and partisan polls are
dropped.

State level: the paper uses MRP on survey microdata. No free, automatable feed of
state MRP approval exists, so the source is pluggable:
  - "vote_swing": state = national + k * (Trump 2024 two-party share in state - national)
  - "csv":        pipeline/state_approval.csv (state,approve), e.g. Civiqs or Morning
                  Consult estimates you are licensed to use, or your own MRP output.
                  Its state differences are kept and re-centred on the national average
                  (the states weighted by adult population, pipeline/adult_population.json).
"""
import csv
import datetime as dt
import json
import math
import os
import re
import urllib.parse
import urllib.request


def fetch_votehub(url):
    """VoteHub returns a plain list of polls (older docs show {"polls": [...]}); accept both."""
    req = urllib.request.Request(url, headers={"User-Agent": "100-days-out-forecast/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["polls"] if isinstance(data, dict) else data


def _iso(d):
    """'2026-11-09', '2026-11-09T..' or PollResults' '11/9/26' -> '2026-11-09' (or '')."""
    d = str(d or "").strip()
    if "/" in d:
        try:
            m, day, y = (int(x) for x in d.split()[0].split("/"))
            return dt.date(y + 2000 if y < 100 else y, m, day).isoformat()
        except ValueError:
            return ""
    return d[:10]


def _first(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def _normalize_pollresults(res):
    """PollResults.org (NYT poll data): camelCase fields, dates like '11/9/26', and each poll
    holds questions -> answers [{politician, yes, no}]. A poll often reports the same question for more
    than one group of people. Returns one VoteHub-shaped dict per group, all adults first (the group the
    paper's surveys describe), then registered, then likely voters; [] if there is nothing to read.
    A question put to part of the sample only (one party's voters, say) is not a national figure and is skipped."""
    rank = {"a": 0, "rv": 1, "lv": 2, "v": 3}
    by_pop = {}
    for q in _first(res, "questions") or []:
        if str(_first(q, "subpopulation") or "").strip():
            continue
        for a in _first(q, "answers") or []:
            who = str(_first(a, "politician", "subject") or "")
            if who and "trump" not in who.lower():
                continue
            yes, no = _first(a, "yes", "approve", "pct"), _first(a, "no", "disapprove")
            if yes is None or no is None:
                continue
            pop = str(_first(q, "population") or "").lower()
            by_pop.setdefault(pop, {"choice_yes": float(yes), "choice_no": float(no), "q": q})
    state = str(_first(res, "state") or "").upper()
    out = []
    for pop in sorted(by_pop, key=lambda p: rank.get(p, 9)):
        b = by_pop[pop]
        out.append({
            "pollster": _first(res, "pollster", "displayName") or "?",
            "end_date": _iso(_first(res, "endDate", "end_date")),
            "sample_size": _first(b["q"], "sampleSize", "sample_size"),
            "population": pop,
            "internal": bool(_first(res, "internal")),
            "partisan": _first(res, "partisan"),
            "url": _first(res, "url"),
            "created_at": _iso(_first(res, "createdAt", "created_at")),
            "state": state if state and state not in ("US", "USA", "NATIONAL") else None,
            "answers": [{"choice": "Approve", "pct": b["choice_yes"]}, {"choice": "Disapprove", "pct": b["choice_no"]}],
            "source": "pollresults",
        })
    return out


def fetch_pollresults(url, max_pages=10):
    """Follow the cursor through up to max_pages pages of 100 polls (newest first)."""
    out, cursor = [], None
    for _ in range(max_pages):
        full = f"{url}?limit=100" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        req = urllib.request.Request(full, headers={"User-Agent": "100-days-out-forecast/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.load(r)
        out.extend(page.get("results", []))
        cursor = page.get("cursor")
        if not cursor:
            break
    return out


# Words that do not tell one pollster from another: the two feeds write "Marist College" and "Marist University",
# "HarrisX/Harris" and "HarrisX/Harris Poll" for the same pollster.
_NAME_FILLER = {"the", "of", "and", "for", "at", "college", "university", "poll", "polls", "polling", "research",
                "center", "centre", "survey", "surveys", "institute", "strategies", "strategy", "group", "news", "inc",
                "co", "company", "llc", "insights", "opinion", "public", "department", "school", "law"}


def pollster_key(name):
    """A pollster's name with the spelling differences between feeds taken out, for counting each pollster once."""
    words = sorted({w for w in re.findall(r"[a-z0-9]+", str(name or "").lower()) if w not in _NAME_FILLER})
    return " ".join(words) or str(name or "").strip().lower()


def _same_poll(p, q):
    """True when two entries are one poll's figures for one group of people.
    Same end date is required. Under one pollster's name: the same group and either the same sample size or the
    same result; or the same sample size AND result under two group labels (the feeds sometimes label one
    sample differently; the entry already kept stands). Under two different names (one feed names the sponsor,
    the other the firm): the same group, result and sample size together."""
    if _iso(p.get("end_date")) != _iso(q.get("end_date")):
        return False
    pa, pd, qa, qd = (_pct(x.get("answers", []), c) for x in (p, q) for c in ("approve", "disapprove"))
    if None in (pa, pd, qa, qd):
        return False
    same_result = abs(pa - qa) <= 0.6 and abs(pd - qd) <= 0.6
    n1, n2 = float(p.get("sample_size") or 0), float(q.get("sample_size") or 0)
    same_size = n1 > 0 and n1 == n2
    same_group = str(p.get("population") or "").lower() == str(q.get("population") or "").lower()
    if pollster_key(p.get("pollster")) == pollster_key(q.get("pollster")):
        return (same_size or same_result) if same_group else (same_size and same_result)
    return same_group and same_result and same_size


def merge_polls(votehub, pollresults_raw):
    """National polls from both sources, plus state polls. A poll is kept once for each group of people it
    reports (all adults, registered voters, likely voters), so its all-adults figures are never lost because
    one feed lists only its voters. A PollResults entry is left out when VoteHub already has that poll for
    that group, whichever way the two feeds spell the pollster's name (see _same_poll)."""
    national, state, kept = [], [], {}

    def add(p):
        national.append(p)
        kept.setdefault(_iso(p.get("end_date")), []).append(p)

    for p in votehub:
        add(p)
    for raw in pollresults_raw:
        rows = _normalize_pollresults(raw)
        if rows and rows[0]["state"]:
            state.append(rows[0])
            continue
        for p in rows:
            if not any(_same_poll(p, q) for q in kept.get(p["end_date"], [])):
                add(p)
    return national, state


def _pct(answers, choice):
    for a in answers or []:
        if str(a.get("choice", "")).lower().startswith(choice) and a.get("pct") is not None:
            return float(a["pct"])
    return None


def window_for(cfg, today):
    """Official window (June 1 - July 30 of the election year) once it opens; otherwise trailing N days."""
    lo, hi = (dt.date.fromisoformat(d) for d in cfg["election"]["approval_window"])
    if today >= lo:
        return lo, min(today, hi), "official"
    return today - dt.timedelta(days=cfg["approval"]["nowcast_window_days"]), today, "nowcast"


def national_average(polls, start, end, half_life_days=14.0, populations=None, pooled=False):
    """The latest poll from each pollster in the window, weighted by sample size and by age.
    A pollster is counted once however the feeds spell its name (pollster_key).
    populations: when given, only polls of those groups count, e.g. ["a"] for polls of all adults,
    the group the paper's approval figures describe ("rv" registered voters, "lv" likely voters).
    pooled: every poll in the window counts, each by its sample size and nothing else, the way the paper
    pools every survey answer from June and July. Used once the model is on the paper's window."""
    want = {str(x).lower() for x in populations} if populations else None
    latest = {}
    for p in polls:
        if p.get("internal") or p.get("partisan"):
            continue
        if want is not None and str(p.get("population") or "").lower() not in want:
            continue
        try:
            d = dt.date.fromisoformat(_iso(p.get("end_date") or p.get("endDate")))
        except (KeyError, ValueError, TypeError):
            continue
        if not (start <= d <= end):
            continue
        ap, dis = _pct(p.get("answers", []), "approve"), _pct(p.get("answers", []), "disapprove")
        if ap is None or dis is None:
            continue
        name = p.get("pollster", "?")
        who = pollster_key(name)      # one pollster, however the feeds spell its name
        n = float(p.get("sample_size") or 600)
        # Pooled: every poll counts once. Two polls by one pollster that end on the same day are two polls when
        # they differ in size or result; the same entry listed twice is one. With no group chosen a poll's
        # figures for adults and for voters would each count, so there it is one entry per pollster and day.
        key = ((who, d, round(n), ap, dis) if want is not None else (who, d)) if pooled else who
        if key not in latest or (not pooled and d > latest[key]["date"]):
            latest[key] = {"date": d, "approve": ap, "disapprove": dis, "n": n,
                           "pollster": name, "url": p.get("url"), "population": p.get("population"),
                           "added": _iso(p.get("created_at") or p.get("createdAt")) or None}
    if not latest:
        raise RuntimeError(f"No usable approval polls between {start} and {end}")
    num_a = num_d = den = 0.0
    for e in latest.values():
        if pooled:
            w = e["n"]
        else:
            age = (end - e["date"]).days
            w = math.sqrt(min(e["n"], 3000)) * 0.5 ** (age / half_life_days)
        num_a += w * e["approve"]; num_d += w * e["disapprove"]; den += w
    rows = sorted(latest.values(), key=lambda e: e["date"], reverse=True)
    for r in rows:
        r["date"] = r["date"].isoformat()
    return {"approve": num_a / den, "disapprove": num_d / den,
            "pollsters": len({pollster_key(r["pollster"]) for r in rows}), "polls": rows}


def adult_population(path=None):
    """{state: people aged 18 and over}, from pipeline/adult_population.json."""
    with open(path or os.path.join(os.path.dirname(__file__), "adult_population.json")) as f:
        return {k: float(v) for k, v in json.load(f)["states"].items()}


def state_approval(cfg, national, results2024, csv_path=None, state_polls=None, window=None):
    """Return ({state: approve %}, {state: n polls used}).

    results2024: {abbr: {"share": Dem two-party %, "votes": n}}.
    state_source "state_polls": start from vote_swing, then pull each state toward its own
    approval polls in the window (each poll weighted by sample size, capped at 1,500; the
    vote-swing estimate counts as 1,500 respondents)."""
    a = cfg["approval"]
    states = {k: v for k, v in results2024.items() if len(k) == 2}
    tot = sum(v["votes"] for v in states.values())
    nat_dem = sum(v["share"] * v["votes"] for v in states.values()) / tot
    if a["state_source"] == "csv":
        path = csv_path or os.path.join(os.path.dirname(__file__), "state_approval.csv")
        with open(path) as f:
            raw = {r["state"].strip().upper(): float(r["approve"]) for r in csv.DictReader(f)}
        if "DC" not in raw:
            raise ValueError("state_approval.csv needs all 50 states and DC")
        # The national figure is an average of polls of all adults, and a national poll of adults is the average
        # of the states weighted by their adult populations. So that is the average the state figures are centred
        # on, not the one weighted by votes cast (which sat 0.14 points higher in November 2026).
        pop = adult_population()
        mean = sum(raw[s] * pop[s] for s in states) / sum(pop[s] for s in states)
        out = {s: national + (raw[s] - mean) for s in states}
    else:
        k = a["vote_swing_k"]
        out = {s: national + k * ((100 - v["share"]) - (100 - nat_dem)) for s, v in states.items()}
    used = {}
    if a["state_source"] == "state_polls" and state_polls:
        lo, hi = window if window else (dt.date.min, dt.date.max)
        lo = lo - dt.timedelta(days=a.get("state_poll_extra_days", 60))
        prior_n = a.get("state_prior_n", 1500)
        for st in states:
            num, den = prior_n * out[st], float(prior_n)
            for p in state_polls:
                if str(p["state"]).upper() != st or p.get("internal") or p.get("partisan"):
                    continue
                try:
                    d = dt.date.fromisoformat(_iso(p["end_date"]))
                except ValueError:
                    continue
                if not (lo <= d <= hi):
                    continue
                ap = _pct(p["answers"], "approve")
                n = min(float(p.get("sample_size") or 600), 1500)
                num += n * ap; den += n
                used[st] = used.get(st, 0) + 1
            out[st] = num / den
    return {s: max(1.0, min(99.0, v)) for s, v in out.items()}, used
