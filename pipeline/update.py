"""Fetch the latest data, build model inputs, run the engine, write site data.

    FRED_API_KEY=... python pipeline/update.py
    python pipeline/update.py --fixtures pipeline/tests/fixtures   # offline test run

Every input is gathered automatically:
    economy      FRED (Philadelphia Fed state coincident indexes)
    approval     VoteHub + PollResults.org national polls; state polls when they exist
    candidates   Wikipedia (nominees, running mates, home states, sitting VP);
                 PollResults.org 2028 primary polls (who is being polled, and how they stand)
    VP gap       VoteHub approval of the sitting VP and the president (favorability as fallback)

Writes:
    docs/nowcast.js      window.NOWCAST, read by the site (incl. inputs for the matchup builder)
    docs/history.js      window.NOWCAST_HISTORY, one row per day
    pipeline/history.json
    pipeline/cache/      raw responses from the last run
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import urllib.request

import approval  # noqa: E402
import civiqs  # noqa: E402
import candidates  # noqa: E402
import economy  # noqa: E402


def refresh_civiqs_state_approval(csv_path, cache_path, offline=False, fixture=None):
    """State approval from Civiqs's public tracker (pipeline/civiqs.py), written to state_approval.csv.
    If today's read fails, the last good read (pipeline/cache) is used, and failing that the CSV in the
    repository, so the run never stops for this. Returns {"name", "url", "as_of", "live"}."""
    data, live = None, False
    try:
        if offline:           # a test run: the saved fixture, never the network
            data = fixture
        else:
            data, live = civiqs.parse(civiqs.fetch()), True
        if live:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            json.dump(data, open(cache_path, "w"))
            print(f"Civiqs state approval read: 50 states through {data['as_of']}")
    except Exception as e:
        print(f"WARNING: Civiqs state approval not read today ({e}); using the last good copy")
        if cache_path and os.path.exists(cache_path):
            data = json.load(open(cache_path))
    info = {"name": "Civiqs", "url": civiqs.URL, "as_of": None, "live": live}
    if data:
        civiqs.write_csv(data, csv_path)   # the 50 states, and DC by the rule kept there
        info["as_of"] = data.get("as_of") or None
    else:   # the CSV kept in the repository: a Civiqs snapshot, dated in config.json
        info["as_of"] = None
    return info


DISTRICTS = {"ME1": "ME", "ME2": "ME", "NE1": "NE", "NE2": "NE", "NE3": "NE"}


def home_code(st, dem, rep):
    return (1 if st == dem else 0) - (1 if st == rep else 0)


def home_lag_weights(cfg):
    """Share of the previous nominees' home-state fade that is applied (the paper uses 1)."""
    c = cfg["candidates"]
    return {"dem": c.get("dem_president_home_lag_weight", 1), "rep": c.get("rep_president_home_lag_weight", 1)}


def econ_summary(raw, last):
    """Monthly picture of the state economies for the site's "latest data" page (the models use the
    weighted averages from economy.py, not this): how many states grew each month, the median state's
    monthly change in its coincident index, and each state's change in the newest month."""
    series = {st: dict(v) for st, v in (raw or {}).items() if v}
    months = sorted({m for v in series.values() for m in v if not last or m <= last})
    monthly = []
    for prev, m in zip(months, months[1:]):
        ch = sorted(100 * (v[m] / v[prev] - 1) for v in series.values() if m in v and prev in v and v[prev])
        if len(ch) >= 40:
            monthly.append({"m": m, "median": round(ch[len(ch) // 2], 3), "up": sum(1 for c in ch if c > 0), "n": len(ch)})
    latest = {}
    if len(months) >= 2:
        prev, m = months[-2], months[-1]
        latest = {st: round(100 * (v[m] / v[prev] - 1), 3) for st, v in series.items() if m in v and prev in v and v[prev]}
    return {"monthly": monthly, "latest": latest}


def build_inputs(cfg, econ_by_delta, approve_by_state, results, codes, vp_shift):
    el, a = cfg["election"], cfg["approval"]
    states = {k: v for k, v in results.items() if len(k) == 2}
    tot = sum(v["votes"] for v in states.values())
    nat = sum(v["share"] * v["votes"] for v in states.values()) / tot
    sign = 1.0 if el["incumbent_party"] == "D" else -1.0
    main = econ_by_delta[cfg["economy"]["delta"]]
    lag_w = home_lag_weights(cfg)
    out = []
    for st, v in states.items():
        out.append({
            "abbr": st, "ev": v["ev"], "pop": v["votes"],
            "inputs": {
                "lagDev": v["share"] - nat,
                "approval": sign * (approve_by_state[st] + vp_shift - a["constant"]),
                "econ": main[st],
                "home": home_code(st, codes["dem_president_home"], codes["rep_president_home"]),
                "homeLag": (lag_w["dem"] if st == codes["dem_president_home_lag"] else 0)
                           - (lag_w["rep"] if st == codes["rep_president_home_lag"] else 0),
                "vpHome": home_code(st, codes["dem_vp_home"], codes["rep_vp_home"]),
                "anderson": 0, "perot": 0,
            },
            "approve": approve_by_state[st],
        })
    districts = [{"abbr": d, "parent": p, "ev": 1,
                  "offset": results[d]["share"] - results[p]["share"]} for d, p in DISTRICTS.items()]
    return out, districts, nat, sign


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", help="read every source from this folder instead of the network")
    ap.add_argument("--today", help="YYYY-MM-DD, defaults to today in US Eastern time")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "config.json")))
    # Once the final forecast is published (Aug 6, 2028), nothing updates again: the last Nowcast is the forecast.
    if not args.fixtures and os.path.exists(os.path.join(HERE, "frozen", "forecast_2028.json")):
        print("The final 2028 forecast is published; the Nowcast is frozen with it. Nothing to update.")
        return
    results = json.load(open(os.path.join(HERE, "results_2024.json")))
    registry = json.load(open(os.path.join(HERE, "candidates.json")))["candidates"]
    # The day is the US Eastern date, not UTC's: a run on a US evening belongs to that day, and the cutoff
    # days (the poll windows, the freeze days, the publish day) start at midnight Eastern.
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(ZoneInfo("America/New_York")).date()
    cache = os.path.join(HERE, "cache")
    pres_stale = False   # True when the 2028 polls come from the last good copy, not today's read
    degraded = []        # sources that could not be read fresh today; nothing is frozen for good on such a day
    fx = args.fixtures

    def fx_json(name, default=None):
        p = os.path.join(fx, name)
        return json.load(open(p)) if os.path.exists(p) else default

    if fx:
        fred = lambda sid, key, start: json.load(open(os.path.join(fx, f"{sid}.json")))  # noqa: E731
        vh = fx_json("votehub.json", [])
        polls = vh["polls"] if isinstance(vh, dict) else vh
        pr_raw = (fx_json("pollresults.json", {}) or {}).get("results", [])

        def wiki(title):
            p = os.path.join(fx, "wiki_" + slug(title) + ".txt")
            return open(p).read() if os.path.exists(p) else ""

        def fav(subject_slug):
            return fx_json(f"fav_{subject_slug}.json", [])

        def appr(subject_slug):
            return fx_json(f"appr_{subject_slug}.json", [])
        pres_raw = (fx_json("pollresults_president.json", {}) or {}).get("results", [])
        cache = None
    else:
        key = os.environ.get("FRED_API_KEY")
        if not key:
            sys.exit("FRED_API_KEY is not set. On GitHub: Settings -> Secrets and variables -> Actions.")
        fred = economy.fetch_fred
        polls = approval.fetch_votehub(cfg["approval"]["votehub_url"])
        try:
            pr_raw = approval.fetch_pollresults(cfg["approval"]["pollresults_url"])
        except Exception as e:  # second source is optional
            print(f"WARNING: PollResults fetch failed ({e}); continuing with VoteHub only")
            pr_raw = []
            degraded.append("PollResults approval polls")
        wiki = None

        def _subject(kind, key):
            def get(subject_slug):
                try:
                    return approval.fetch_votehub(cfg["approval"][key].format(slug=subject_slug))
                except Exception as e:
                    print(f"WARNING: {kind} fetch for {subject_slug} failed ({e})")
                    degraded.append(f"VoteHub {kind} polls")
                    return []
            return get
        fav = _subject("favorability", "votehub_fav_url")
        appr = _subject("approval", "votehub_subject_approval_url")
        # 2028 primary and head-to-head polls. Up to 3,000 records are read (the feed holds about 200 today).
        # If today's read fails or comes back empty, yesterday's copy is used, so the polls model does not
        # drop out of the Nowcast for a day; polls still age out of the window as usual.
        pres_cache = os.path.join(cache, "pollresults_president.json")
        try:
            pres_raw = approval.fetch_pollresults(cfg["approval"]["pollresults_president_url"], max_pages=30)
            if len(pres_raw) >= 3000:
                print("WARNING: the PollResults 2028 feed filled all 30 pages; older polls may be missing")
        except Exception as e:
            print(f"WARNING: PollResults 2028 polls fetch failed ({e})")
            pres_raw = []
        if not pres_raw and os.path.exists(pres_cache):
            pres_raw = (json.load(open(pres_cache)) or {}).get("results", [])
            pres_stale = bool(pres_raw)
            print(f"WARNING: using the last good copy of the PollResults 2028 polls ({len(pres_raw)} records)")
        if pres_stale or not pres_raw:
            degraded.append("PollResults 2028 polls")
        os.makedirs(cache, exist_ok=True)
        json.dump({"polls": polls}, open(os.path.join(cache, "votehub.json"), "w"))
        json.dump({"results": pr_raw}, open(os.path.join(cache, "pollresults.json"), "w"))
        json.dump({"results": pres_raw}, open(os.path.join(cache, "pollresults_president.json"), "w"))

    # State-by-state approval from Civiqs's public tracker (CSV source)
    state_info = None
    if cfg["approval"].get("state_source") == "csv":
        if fx or cfg["approval"].get("state_live_read", False):
            state_info = refresh_civiqs_state_approval(os.path.join(HERE, "state_approval.csv"),
                                                       os.path.join(cache, "civiqs_state_approval.json") if cache else None,
                                                       offline=bool(fx),
                                                       fixture=fx_json("civiqs_state_approval.json") if fx else None)
        else:   # no daily request: Civiqs's site turns automatic reads away (HTTP 403), so the dated copy in the
            # repository is used. It is refreshed by hand from a saved copy of the page (pipeline/civiqs.py).
            state_info = {"name": "Civiqs", "url": civiqs.URL, "as_of": None, "live": False}
        if not state_info["as_of"]:
            state_info["as_of"] = cfg["approval"].get("state_csv_as_of")

    # Economy and approval
    econ, econ_last, econ_raw = economy.build_economy(cfg, None if fx else key, cache, fetch=fred)
    w_lo, w_hi, mode = approval.window_for(cfg, today)
    national_polls, state_polls = approval.merge_polls(polls, pr_raw)
    if pr_raw and not any(p.get("source") == "pollresults" for p in national_polls) and not state_polls:
        print(f"WARNING: could not read any of {len(pr_raw)} PollResults records; check pipeline/cache/pollresults.json")
    # The paper's window (June 1 - July 30, 2028) opens with no polls in it. While it is still open and fewer
    # than official_min_pollsters have a poll in it, the Nowcast keeps its trailing window, so the first days
    # of June do not rest on one or two polls. Once the window has closed it is used whatever it holds.
    trailing = cfg["approval"]["nowcast_window_days"]
    official_wait = None
    if mode == "official" and today <= dt.date.fromisoformat(cfg["election"]["approval_window"][1]):
        need = cfg["approval"].get("official_min_pollsters", 10)
        try:
            have = approval.national_average(national_polls, w_lo, w_hi)["pollsters"]
        except RuntimeError:
            have = 0
        if have < need:
            official_wait = {"pollsters": have, "needed": need}
            w_lo, w_hi, mode = today - dt.timedelta(days=trailing), today, "nowcast"
    nat = approval.national_average(national_polls, w_lo, w_hi)
    # For the site's "latest data" page only: the approval average as it stood each week of the term, as a
    # trailing 30-day average. The models read only today's value.
    appr_trend, span = [], trailing
    t_day = dt.date.fromisoformat(cfg["election"]["term_start_month"] + "-01") + dt.timedelta(days=span)
    while t_day < w_hi:
        try:
            a_t = approval.national_average(national_polls, t_day - dt.timedelta(days=span), t_day)
            appr_trend.append({"d": t_day.isoformat(), "a": round(a_t["approve"], 1), "dis": round(a_t["disapprove"], 1)})
        except RuntimeError:
            pass
        t_day += dt.timedelta(days=7)
    appr_trend.append({"d": w_hi.isoformat(), "a": round(nat["approve"], 1), "dis": round(nat["disapprove"], 1)})
    by_state, state_used = approval.state_approval(cfg, nat["approve"], results, state_polls=state_polls, window=(w_lo, w_hi))

    # Who is running, home states, sitting VP
    detected = candidates.detect(cfg, fetch=wiki)
    codes, tickets, vp_is_nominee = candidates.resolve(cfg, detected)
    for n in detected["notes"]:
        print("WARNING:", n)
    if detected["notes"]:
        degraded.append("Wikipedia")

    # Possible candidates, ordered by 2028 primary polling; new names are added automatically.
    cc = cfg["candidates"]
    p_lo = today - dt.timedelta(days=cc.get("primary_window_days", 120))
    standing = candidates.primary_standing(pres_raw, p_lo, today, approval._iso)
    registry = candidates.merge_registry(registry, standing, fetch=wiki, min_pct=cc.get("primary_min_pct", 3),
                                         exclude=[cfg["election"]["incumbent_president"]])

    # VP gap: (sitting VP net approval) - (president net approval); favorability if no approval polls
    vpc = cfg["vp_adjustment"]
    sitting_vp = detected.get("sitting_vp") or "JD Vance"
    if mode == "official":
        g_lo, g_hi = w_lo, w_hi
    else:
        g_lo, g_hi = today - dt.timedelta(days=vpc.get("trailing_days", 60)), today
    gap_kind = None
    if vpc.get("mode") == "manual" and vpc.get("vp_net") is not None:
        gap, gap_basis, gap_kind = vpc["vp_net"] - vpc["president_net"], "manual values in config.json", "approval"
    else:
        vp_slug, pres_slug = slug(sitting_vp), slug(cfg["election"]["incumbent_president"])
        sources = {"approval": (appr(vp_slug), national_polls), "favorability": (fav(vp_slug), fav(pres_slug))}
        gap, gap_basis = None, "no approval or favorability polls of the vice president in the window"
        # Prefer job approval with 3 or more polls of the vice president, looking further back if
        # the usual window is thin; then favorability the same way; then whatever there is.
        spans = [vpc.get("trailing_days", 120), 240, 365]
        tries = [(k, d, 3) for k in ("approval", "favorability") for d in spans]
        tries += [("approval", spans[-1], 1), ("favorability", spans[-1], 1)]
        for kind, days, need in tries:
            usual = days == spans[0]
            lo = g_lo if usual else g_hi - dt.timedelta(days=days)   # counted back from the window's end, not from today
            g, basis = candidates.vp_gap(*sources[kind], lo, g_hi, approval._iso, kind, min_vp=need)
            if g is not None:
                gap, gap_kind, g_lo = g, kind, lo
                gap_basis = basis if usual else f"{basis} from the last {days} days"
                break
    # ASSUMPTION (not in the paper), daily Nowcast only: a gap measured from few polls is counted only in
    # part, reaching full weight at full_weight_polls polls of the vice president. In the paper's own window
    # (June 1 - July 30, 2028), and so in the final forecast, the gap is applied in full, as the authors do.
    gap_raw, gap_polls, gap_weight = gap, None, 1.0
    if gap is not None and vpc.get("mode") != "manual":
        m = re.search(r"\d+", gap_basis)
        gap_polls = int(m.group()) if m else 0
        full = vpc.get("full_weight_polls", 20)
        gap_weight = min(1.0, gap_polls / full) if full and mode != "official" else 1.0
        if gap_weight < 1:
            gap = gap_raw * gap_weight
            gap_basis += f"; counted at {gap_weight:.0%} of {gap_raw:+.1f} until there are {full} polls"
    applied = (vp_is_nominee or vpc.get("mode") == "manual") and gap is not None
    vp_shift = gap if applied else 0.0

    states, districts, nat_dem, sign = build_inputs(cfg, econ, by_state, results, codes, vp_shift)

    # National head-to-head polls between listed candidates, for the second model (DeSart 2025).
    hh = cfg.get("head_to_head", {})
    # Head-to-head polls stop at the forecast day, by the date they were conducted: one conducted by then
    # still counts if it is published later. The 180-day window ends there too.
    h_hi = min(today, dt.date.fromisoformat(cfg["election"]["forecast_day"]))
    h_lo = h_hi - dt.timedelta(days=hh.get("window_days", 180))
    # Two-term presidents cannot be nominees, so hypothetical matchups naming them are left out.
    barred = [cfg["election"]["incumbent_president"]] + hh.get("cannot_run", [])
    matchups, h_skipped = candidates.general_matchups(pres_raw, h_lo, h_hi, approval._iso, registry, exclude=barred)
    # People in those matchups who are not on the candidate list still count, as in DeSart's average.
    # Their home states (from Wikipedia) let the polls model spread the home-state effect to them too.
    listed = {(c["party"], c["name"]) for c in registry}
    h2h_people = None   # filled in below, once off_list is defined
    terms = (1 if cfg["election"]["incumbent_party"] == "D" else -1) * cfg["election"].get("incumbent_party_terms", 1)

    # People in matchups who are off the candidate list, with home states for the home-state effect.
    def off_list(rows):
        out = []
        for party, key in (("D", "d"), ("R", "r")):
            for name in sorted({m[key] for m in rows} - {n for p, n in listed if p == party}):
                st = hh.get("home_states", {}).get(name)   # set by hand where Wikipedia's infobox misleads
                if not st:
                    st, _src = candidates.home_state_of(name, [], wiki)
                out.append({"name": name, "party": party, "state": st})
        return out
    h2h_people = off_list(matchups)

    # The polls model's half of the final forecast, as DeSart publishes it: head-to-head polls conducted in
    # October 2027, frozen a week later (Nov 7, 2027). Until then it is provisional; after, it never changes.
    el = cfg["election"]
    frozen_dir = os.path.join(HERE, "frozen")
    ds_lo, ds_hi = (dt.date.fromisoformat(d) for d in el["desart_poll_window"])
    ds_path = os.path.join(frozen_dir, "desart_2028.json")
    desart_final = None
    if os.path.exists(ds_path) and not fx:
        desart_final = json.load(open(ds_path))
    elif today >= ds_lo:
        ds_rows, ds_skipped = candidates.general_matchups(pres_raw, ds_lo, ds_hi, approval._iso, registry, exclude=barred)
        desart_final = {"window": [ds_lo.isoformat(), ds_hi.isoformat()], "polls": ds_rows, "skipped": ds_skipped,
                        "people": off_list(ds_rows), "terms": terms, "as_of": today.isoformat(), "frozen": False}
        if not fx and today >= dt.date.fromisoformat(el["desart_freeze_day"]):
            # Not frozen from a stale copy of the polls, unless the feed has been unreadable for a week.
            late = (today - dt.date.fromisoformat(el["desart_freeze_day"])).days >= el.get("freeze_retry_days", 7)
            if ds_rows and pres_raw and (not pres_stale or late):
                desart_final["frozen"] = True
                os.makedirs(frozen_dir, exist_ok=True)
                json.dump(desart_final, open(ds_path, "w"), indent=1)
                print(f"Froze the polls model's half of the final forecast: {len(ds_rows)} polls from {ds_lo} to {ds_hi}")
            else:
                print("WARNING: freeze day for the polls model passed, but the October 2027 polls could not be read fresh; will retry")

    by_abbr = {s["abbr"]: s for s in states}
    r4 = lambda x: round(x, 4)  # noqa: E731
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "as_of": today.isoformat(),
        "mode": mode,
        "fixture_run": bool(fx),
        "approval": {"approve": round(nat["approve"], 1), "disapprove": round(nat["disapprove"], 1),
                     "window": [w_lo.isoformat(), w_hi.isoformat()], "pollsters": nat["pollsters"],
                     "polls": nat["polls"][:25], "trend": appr_trend, "official_wait": official_wait, "state_source": cfg["approval"]["state_source"],
                     "state_data": state_info, "state_polls_used": state_used},
        "economy": {"through": econ_last, "delta": cfg["economy"]["delta"], **econ_summary(econ_raw, econ_last)},
        "tickets": tickets,
        "sitting_vp": sitting_vp,
        "vp": {"gap": None if gap is None else round(gap, 2), "kind": gap_kind, "basis": gap_basis, "applied": applied,
               "raw_gap": None if gap_raw is None else round(gap_raw, 2), "polls": gap_polls, "weight": round(gap_weight, 2),
               "window": [g_lo.isoformat(), g_hi.isoformat()]},
        "h2h": {"window": [h_lo.isoformat(), h_hi.isoformat()], "days": hh.get("window_days", 180),
                "min_polls": hh.get("min_polls", 3), "terms": terms, "polls": matchups, "skipped": h_skipped,
                "people": h2h_people, "stale": pres_stale},
        "desart_final": desart_final,
        # Everything the in-browser ticket picker needs to rerun both models (docs/combine.js).
        "scenario": {
            "constant": cfg["approval"]["constant"], "sign": sign,
            "homeLag": {"dem": codes["dem_president_home_lag"], "rep": codes["rep_president_home_lag"]},
            "homeLagWeight": home_lag_weights(cfg),
            "states": [{"abbr": s["abbr"], "ev": s["ev"], "pop": s["pop"], "lagDev": r4(s["inputs"]["lagDev"]),
                        "approve": r4(s["approve"]), "prior": results[s["abbr"]]["share"]} for s in states],
            "econVariants": [{k: r4(v) for k, v in econ[d].items()} for d in cfg["economy"]["delta_grid"]],
            "districts": [{**d, "offset": r4(d["offset"])} for d in districts],
            "candidates": registry,
        },
    }

    # Run both models on the payload with the same code the site uses, so the numbers agree.
    def pick(role, side, key):
        t = tickets[side].get(key) or {}
        return {"name": t.get("name") or "", "state": codes[role]} if codes[role] else None
    sim_in = {"N": payload, "n": cfg["simulation"]["n_per_delta"], "seed": cfg["simulation"]["seed"],
              "picks": {"dp": pick("dem_president_home", "dem", "president"), "rp": pick("rep_president_home", "rep", "president"),
                        "dv": pick("dem_vp_home", "dem", "vp"), "rv": pick("rep_vp_home", "rep", "vp")},
              "force_vp_shift": gap if vpc.get("mode") == "manual" and gap is not None else None}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sim_in, f)
    out = json.loads(subprocess.check_output(["node", os.path.join(HERE, "run_forecast.js"), f.name]))
    os.unlink(f.name)
    res = out["combined"]
    dem_ev_point = sum(s["ev"] for s in res["states"] if s["demShare"] > 50)
    brief = lambda m: m and {"pDemWin": round(m["pDemWin"], 4), "pTie": round(m["pTie"], 4),  # noqa: E731
                             "demPopular": round(m["demPopular"], 2)}
    payload["summary"] = {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                          "demEvPoint": dem_ev_point, "simulations": res["simulations"]}
    payload["models"] = {"enns": brief(out["enns"]), "desart": brief(out["desart"]),
                         "polls": out["info"]["polls"] and {"avg": round(out["info"]["polls"]["avg"], 2), "n": out["info"]["polls"]["n"]}}
    payload["evHistogram"] = [round(x, 5) for x in res["evHistogram"]]
    payload["states"] = [{**{k: (round(v, 2) if k in ("demShare", "enns", "desart") else v) for k, v in s.items()},
                          "pDem": round(s["pDem"], 4),
                          "approve": round(by_abbr[s["abbr"]]["approve"], 1) if s["abbr"] in by_abbr else None,
                          "econ": round(by_abbr[s["abbr"]]["inputs"]["econ"], 4) if s["abbr"] in by_abbr else None}
                         for s in res["states"]]

    # The final forecast: the Nowcast as it stands on publish_day (Aug 6, 2028), frozen and never changed after.
    # By then its approval half uses polls conducted June 1 - July 30 (the paper's window) and its polls half the
    # frozen October 2027 set, so the Nowcast that day is each paper's forecast.
    fc_path = os.path.join(frozen_dir, "forecast_2028.json")
    if not fx and os.path.exists(fc_path):
        final = json.load(open(fc_path))
    elif (not fx and today >= dt.date.fromisoformat(el["publish_day"]) and desart_final and desart_final.get("frozen")
          and degraded and (today - dt.date.fromisoformat(el["publish_day"])).days < el.get("publish_retry_days", 3)):
        # A source could not be read today. The forecast is frozen for good, so it waits for a clean read
        # (the next run, or tomorrow's); after publish_retry_days it is published with what there is.
        print(f"WARNING: the final forecast was NOT published today: could not read {', '.join(sorted(set(degraded)))}; will retry")
        final = None
    elif not fx and today >= dt.date.fromisoformat(el["publish_day"]) and desart_final and desart_final.get("frozen"):
        fo, fr = out, res   # the Nowcast already runs the frozen October 2027 polls as DeSart publishes them
        final = {"published": today.isoformat(), "tickets": tickets,
                 "approval": payload["approval"], "economy": payload["economy"], "vp": payload["vp"],
                 "desart_polls": {"window": desart_final["window"], "n": len(desart_final["polls"]),
                                  "avg": fo["info"]["polls"] and round(fo["info"]["polls"]["avg"], 2)},
                 "summary": {"pDemWin": fr["pDemWin"], "pTie": fr["pTie"], "demPopular": fr["demPopular"],
                             "demEvPoint": sum(s["ev"] for s in fr["states"] if s["demShare"] > 50)},
                 "models": {"enns": brief(fo["enns"]), "desart": brief(fo["desart"])},
                 "evHistogram": [round(x, 5) for x in fr["evHistogram"]],
                 "states": [{**{k: (round(v, 2) if k in ("demShare", "enns", "desart") else v) for k, v in s.items()},
                             "pDem": round(s["pDem"], 4)} for s in fr["states"]]}
        os.makedirs(frozen_dir, exist_ok=True)
        json.dump(final, open(fc_path, "w"), indent=1)
        print(f"Published the final 2028 forecast: Dem win {fr['pDemWin']:.1%}, Dem popular {fr['demPopular']:.2f}%")
    else:
        final = None
    if final is not None:
        with open(os.path.join(ROOT, "docs", "forecast.js"), "w") as f:
            f.write("// The final 2028 forecast, frozen on its publish day. Do not edit.\nwindow.FORECAST = " + json.dumps(final) + ";\n")

    with open(os.path.join(ROOT, "docs", "nowcast.js"), "w") as f:
        f.write("// Generated by pipeline/update.py. Do not edit.\nwindow.NOWCAST = " + json.dumps(payload) + ";\n")

    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    if not fx:
        # v4: average of three models. Earlier days used fewer models and are dropped.
        # Today's row is replaced; a row dated after today (written by a run stamped with the wrong day) is dropped.
        hist = [h for h in hist if h.get("v") == 4 and h["date"] < today.isoformat()]
        mp = payload["models"]
        hist.append({"v": 4, "date": today.isoformat(), "pDemWin": round(res["pDemWin"], 4),
                     "demPopular": round(res["demPopular"], 2), "approve": round(nat["approve"], 1),
                     "econThrough": econ_last,
                     # Added Nov 2026 for the "latest data" page; earlier days lack them.
                     "enns": mp["enns"] and mp["enns"]["pDemWin"], "desart": mp["desart"] and mp["desart"]["pDemWin"],
                     "pollAvg": mp["polls"] and mp["polls"]["avg"], "h2hN": len(matchups),
                     "apprN": nat["pollsters"], "ev": dem_ev_point})
        hist.sort(key=lambda h: h["date"])
        json.dump(hist, open(hist_path, "w"), indent=1)
    with open(os.path.join(ROOT, "docs", "history.js"), "w") as f:
        f.write("window.NOWCAST_HISTORY = " + json.dumps(hist) + ";\n")

    s = payload["summary"]
    n_pr = sum(1 for p in national_polls if p.get("source") == "pollresults")
    who = {side: (tickets[side].get("president", {}).get("name"), tickets[side].get("vp", {}).get("name")) for side in tickets}
    print(f"Polls: {len(polls)} from VoteHub, {n_pr} more national from PollResults, {len(state_polls)} state polls")
    print(f"Tickets: {who}; sitting VP {sitting_vp}; VP gap {gap} ({gap_kind}: {gap_basis}), applied={applied}")
    lead = {p: [(r["name"], r["pct"]) for r in rows[:3]] for p, rows in standing.items()}
    print(f"2028 primary polls: {len(pres_raw)} records; leaders {lead}; {sum(1 for c in registry if c.get('auto'))} candidates added")
    print(f"{today} [{mode}] approval {nat['approve']:.1f}% ({nat['pollsters']} pollsters), "
          f"economy through {econ_last}; Dem win {s['pDemWin']:.1%}, Dem popular {s['demPopular']:.2f}%, "
          f"point EV {dem_ev_point}")
    m = payload["models"]
    print(f"Models: approval/economy {m['enns']['pDemWin']:.1%}; head-to-head polls "
          + (f"{m['desart']['pDemWin']:.1%} from {m['polls']['n']} polls averaging {m['polls']['avg']:.1f}% Democratic"
             if m["desart"] else "not run (no polls)") + f"; {len(matchups)} matchups in window, {h_skipped} skipped")


if __name__ == "__main__":
    main()
