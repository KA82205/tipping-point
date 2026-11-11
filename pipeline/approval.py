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
                  Its state differences are kept and re-centred on the national average.
"""
import csv
import datetime as dt
import json
import math
import os
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
    holds questions -> answers [{politician, yes, no}]. Prefer the all-adults question, as the
    paper's surveys were of adults, then registered, then likely voters. Returns a
    VoteHub-shaped dict or None."""
    best = None
    rank = {"a": 0, "rv": 1, "lv": 2, "v": 3}
    for q in _first(res, "questions") or []:
        for a in _first(q, "answers") or []:
            who = str(_first(a, "politician", "subject") or "")
            if who and "trump" not in who.lower():
                continue
            yes, no = _first(a, "yes", "approve", "pct"), _first(a, "no", "disapprove")
            if yes is None or no is None:
                continue
            pop = str(_first(q, "population") or "").lower()
            cand = (rank.get(pop, 9), {"choice_yes": float(yes), "choice_no": float(no), "q": q, "pop": pop})
            if best is None or cand[0] < best[0]:
                best = cand
    if not best:
        return None
    b = best[1]
    state = str(_first(res, "state") or "").upper()
    return {
        "pollster": _first(res, "pollster", "displayName") or "?",
        "end_date": _iso(_first(res, "endDate", "end_date")),
        "sample_size": _first(b["q"], "sampleSize", "sample_size"),
        "population": b["pop"],
        "internal": bool(_first(res, "internal")),
        "partisan": _first(res, "partisan"),
        "url": _first(res, "url"),
        "state": state if state and state not in ("US", "USA", "NATIONAL") else None,
        "answers": [{"choice": "Approve", "pct": b["choice_yes"]}, {"choice": "Disapprove", "pct": b["choice_no"]}],
        "source": "pollresults",
    }


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


def merge_polls(votehub, pollresults_raw):
    """National polls from both sources, de-duplicated on (pollster, end date); plus state polls."""
    seen, national, state = set(), [], []
    for p in votehub:
        seen.add((str(p.get("pollster", "")).lower(), _iso(p.get("end_date"))))
        national.append(p)
    for raw in pollresults_raw:
        p = _normalize_pollresults(raw)
        if not p:
            continue
        if p["state"]:
            state.append(p)
            continue
        key = (p["pollster"].lower(), p["end_date"])
        if key not in seen:
            seen.add(key); national.append(p)
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


def national_average(polls, start, end, half_life_days=14.0):
    latest = {}
    for p in polls:
        if p.get("internal") or p.get("partisan"):
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
        key = p.get("pollster", "?")
        if key not in latest or d > latest[key]["date"]:
            n = float(p.get("sample_size") or 600)
            latest[key] = {"date": d, "approve": ap, "disapprove": dis, "n": n,
                           "pollster": key, "url": p.get("url"), "population": p.get("population")}
    if not latest:
        raise RuntimeError(f"No usable approval polls between {start} and {end}")
    num_a = num_d = den = 0.0
    for e in latest.values():
        age = (end - e["date"]).days
        w = math.sqrt(min(e["n"], 3000)) * 0.5 ** (age / half_life_days)
        num_a += w * e["approve"]; num_d += w * e["disapprove"]; den += w
    rows = sorted(latest.values(), key=lambda e: e["date"], reverse=True)
    for r in rows:
        r["date"] = r["date"].isoformat()
    return {"approve": num_a / den, "disapprove": num_d / den,
            "pollsters": len(rows), "polls": rows}


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
        mean = sum(raw[s] * states[s]["votes"] for s in states) / tot
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
