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
    pipeline/log/        a fuller record of every day, kept for later research (pipeline/daily_log.py)

Reads, when they exist:
    pipeline/published/desart_2028.json, enns_2028.json    the authors' own published 2028 forecasts, put in by
                         hand with pipeline/put_in.py. Each replaces the site's own run of that model.
"""
import argparse
import datetime as dt
import hashlib
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
import daily_log  # noqa: E402
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
            mid = len(ch) // 2
            median = ch[mid] if len(ch) % 2 else (ch[mid - 1] + ch[mid]) / 2   # 50 states: halfway between the middle two
            monthly.append({"m": m, "median": round(median, 3), "up": sum(1 for c in ch if c > 0), "n": len(ch)})
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


# ---- the authors' own published forecasts (pipeline/published/, put in by hand with pipeline/put_in.py) ----
MODELS = ("enns", "desart")


def load_published(cfg, results, folder=None):
    """{"desart": {...}, "enns": {...}} for the authors' published forecasts that have been put in; {} before any.
    Each has "states": {abbr: Democratic share of the two-party vote} and what is known about the publication.
    A file that cannot be used is skipped with a warning, and the site's own run of that model stays in."""
    out, need = {}, [k for k in results if len(k) == 2 and k != "DC"]
    for model in MODELS:
        path = os.path.join(folder or os.path.join(HERE, "published"), f"{model}_{cfg['election']['year']}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            st = {k: float(v) for k, v in d["states"].items() if k in results and len(k) == 2}
            missing = [k for k in need if k not in st]
            odd = [k for k, v in st.items() if not 0 < v < 100]
            if missing or odd:
                raise ValueError(f"missing {missing}" if missing else f"not a share of the vote: {odd}")
            dt.date.fromisoformat(d["published"])
            out[model] = {**{k: v for k, v in d.items() if not k.startswith("_") and k != "states"}, "states": st}
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: {os.path.relpath(path, ROOT)} was not used ({e}); the site's own run of that model stays in")
    return out


def published_id(published):
    """A fingerprint of the published forecasts in use, to tell when one is added, corrected or taken out."""
    return hashlib.sha1(json.dumps(published, sort_keys=True).encode()).hexdigest()[:12] if published else ""


def sources_of(published):
    return {m: "authors' forecast" if m in published else "site run" for m in MODELS}


def run_models(sim_in):
    """Run both models with the same code the site uses (docs/combine.js), so the numbers agree."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sim_in, f)
    out = json.loads(subprocess.check_output(["node", os.path.join(HERE, "run_forecast.js"), f.name]))
    os.unlink(f.name)
    return out


def brief(m):
    """A model's headline figures, exactly as the run gave them. Nothing the site prints is rounded here: the pages
    round once, when they print, so a figure reads the same on every page. (Rounded here to two decimals and then
    again on the page to one, 49.846 came out as 49.9 on one page and 49.8 on another.)"""
    return m and {"pDemWin": m["pDemWin"], "pTie": m["pTie"], "demPopular": m["demPopular"]}


def state_rows(res, extra):
    """One row per state and district, as the site reads them, with the run's figures unrounded (see brief).
    extra: {abbr: {"approve", "econ"}} for the states."""
    return [{**s,
             "approve": extra[s["abbr"]]["approve"] if s["abbr"] in extra else None,
             "econ": extra[s["abbr"]]["econ"] if s["abbr"] in extra else None}
            for s in res["states"]]


def results_into(payload, out, extra):
    """Put a run's results into the payload. Returns (the combined result, electoral votes with each state to
    whoever is ahead in it)."""
    res = out["combined"]
    dem_ev_point = sum(s["ev"] for s in res["states"] if s["demShare"] > 50)
    payload["summary"] = {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                          "demEvPoint": dem_ev_point, "simulations": res["simulations"]}
    payload["models"] = {"enns": brief(out["enns"]), "desart": brief(out["desart"]),
                         "polls": out["info"]["polls"] and {"avg": out["info"]["polls"]["avg"], "n": out["info"]["polls"]["n"]}}
    payload["evHistogram"] = [round(x, 5) for x in res["evHistogram"]]
    payload["states"] = state_rows(res, extra)
    return res, dem_ev_point


def own_runs(out, extra):
    """The site's own runs of both models, when an author's published forecast has replaced one of them on the
    site. They go to the daily record only (pipeline/log), so the two can be compared after the election."""
    o = out.get("own")
    if not o:
        return None
    res = o["combined"]
    return {"summary": {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                        "demEvPoint": sum(s["ev"] for s in res["states"] if s["demShare"] > 50)},
            "models": {"enns": brief(o["enns"]), "desart": brief(o["desart"])},
            "states": state_rows(res, extra)}


def final_forecast(payload, out, tickets, desart_final, day, published, updated=None):
    """The forecast as posted: the Nowcast as it stands on the publish day. Each half is the authors' own published
    forecast or, where that is not out, the site's own run standing in for it; "sources" says which."""
    res = out["combined"]
    final = {"published": day, "tickets": tickets,
             "approval": payload["approval"], "economy": payload["economy"], "vp": payload["vp"],
             "desart_polls": {"window": desart_final["window"], "n": len(desart_final["polls"]),
                              "avg": out["info"]["polls"] and out["info"]["polls"]["avg"]},
             "summary": {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                         "demEvPoint": sum(s["ev"] for s in res["states"] if s["demShare"] > 50)},
             "models": {"enns": brief(out["enns"]), "desart": brief(out["desart"])},
             "evHistogram": [round(x, 5) for x in res["evHistogram"]],
             "states": [dict(s) for s in res["states"]],
             "sources": sources_of(published),
             "authors": {m: {k: v for k, v in p.items() if k != "states"} for m, p in published.items()},
             "published_id": published_id(published)}
    if updated:
        final["updated"] = updated
    return final


def write_js(name, comment, var, obj):
    with open(os.path.join(ROOT, "docs", name), "w") as f:
        f.write(f"// {comment}\nwindow.{var} = " + json.dumps(obj) + ";\n")


def late_put_in(cfg, results, today, log_dir=None):
    """After the forecast is posted the daily update stops. One thing can still change it: an author's forecast
    that comes out late replaces the site's own run that stood in for it. The inputs stay as they were frozen.
    Returns True when the posted forecast was redone."""
    frozen_dir = os.path.join(HERE, "frozen")
    fc_path, in_path = os.path.join(frozen_dir, "forecast_2028.json"), os.path.join(frozen_dir, "nowcast_2028.json")
    final = json.load(open(fc_path))
    published = load_published(cfg, results)
    if published_id(published) == final.get("published_id", ""):
        return False
    if not os.path.exists(in_path):
        print("WARNING: a published forecast was put in after the final forecast was posted, but the frozen inputs "
              "(pipeline/frozen/nowcast_2028.json) are missing, so the posted forecast was left as it is")
        return False
    kept = json.load(open(in_path))
    payload, sim = kept["payload"], kept["sim"]
    payload.pop("published", None)
    payload.pop("model_sources", None)
    if published:
        payload["published"], payload["model_sources"] = published, sources_of(published)
    out = run_models({"N": payload, **sim, "own": bool(published)})
    extra = {s["abbr"]: {"approve": s.get("approve"), "econ": s.get("econ")} for s in payload["states"] if len(s["abbr"]) == 2}
    res, _ = results_into(payload, out, extra)
    final = final_forecast(payload, out, payload["tickets"], payload["desart_final"], final["published"], published,
                           updated=today.isoformat())
    json.dump(final, open(fc_path, "w"), indent=1)
    json.dump({"sim": sim, "payload": payload}, open(in_path, "w"))
    write_js("forecast.js", "The final 2028 forecast, frozen on its publish day. Do not edit.", "FORECAST", final)
    write_js("nowcast.js", "Generated by pipeline/update.py. Do not edit.", "NOWCAST", payload)
    try:
        noted = daily_log.record(payload, cfg, today, own=own_runs(out, extra), log_dir=log_dir or daily_log.LOG_DIR)
        print("Daily record: " + (" ".join(noted) if noted else "nothing changed since the last run"))
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: the daily record was not written ({e})")
    print(f"The posted 2028 forecast was redone with the published forecasts now in ({', '.join(sorted(published)) or 'none'}): "
          f"Dem win {res['pDemWin']:.1%}, Dem popular {res['demPopular']:.2f}%")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", help="read every source from this folder instead of the network")
    ap.add_argument("--today", help="YYYY-MM-DD, defaults to today in US Eastern time")
    ap.add_argument("--log-dir", help="write the daily record here (a test run writes none unless this is given)")
    ap.add_argument("--freeze-in-test", action="store_true",
                    help="let a test run fix and post the forecast on its days, to try those days in a scratch copy")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "config.json")))
    live = not args.fixtures or args.freeze_in_test      # a test run fixes and posts nothing unless asked to
    results = json.load(open(os.path.join(HERE, "results_2024.json")))
    # The day is the US Eastern date, not UTC's: a run on a US evening belongs to that day, and the cutoff
    # days (the poll windows, the freeze days, the publish day) start at midnight Eastern.
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(ZoneInfo("America/New_York")).date()
    # Once the final forecast is posted (Aug 6, 2028), nothing updates again: the last Nowcast is the forecast.
    # The one exception is an author's forecast that comes out after that day (late_put_in).
    if live and os.path.exists(os.path.join(HERE, "frozen", "forecast_2028.json")):
        if not late_put_in(cfg, results, today, args.log_dir):
            print("The final 2028 forecast is published; the Nowcast is frozen with it. Nothing to update.")
        return
    registry = json.load(open(os.path.join(HERE, "candidates.json")))["candidates"]
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
        state_info["gap_scale"] = float(cfg["approval"].get("state_gap_scale", 1.0))   # the size each state's gap counts at

    # Economy and approval
    econ_stale = []
    econ, econ_last, econ_raw = economy.build_economy(cfg, None if fx else key, cache, fetch=fred, stale=econ_stale)
    if econ_stale:
        degraded.append("FRED state indexes")
    w_lo, w_hi, mode = approval.window_for(cfg, today)
    national_polls, state_polls = approval.merge_polls(polls, pr_raw)
    if pr_raw and not any(p.get("source") == "pollresults" for p in national_polls) and not state_polls:
        print(f"WARNING: could not read any of {len(pr_raw)} PollResults records; check pipeline/cache/pollresults.json")
    # The paper's window (June 1 - July 30, 2028) opens with no polls in it. While it is still open and fewer
    # than official_min_pollsters have a poll in it, the Nowcast keeps its trailing window, so the first days
    # of June do not rest on one or two polls. Once the window has closed it is used whatever it holds.
    trailing = cfg["approval"]["nowcast_window_days"]
    # Which polls count, by who was surveyed. The paper estimates approval among all adults, so only polls of
    # all adults count (config: approval.national_populations).
    pops = cfg["approval"].get("national_populations") or None
    official_wait = None
    if mode == "official" and today <= dt.date.fromisoformat(cfg["election"]["approval_window"][1]):
        need = cfg["approval"].get("official_min_pollsters", 10)
        try:
            have = approval.national_average(national_polls, w_lo, w_hi, populations=pops)["pollsters"]
        except RuntimeError:
            have = 0
        if have < need:
            official_wait = {"pollsters": have, "needed": need}
            w_lo, w_hi, mode = today - dt.timedelta(days=trailing), today, "nowcast"
    # On the paper's window (June 1 - July 30, 2028) every poll in it counts, by its sample size alone: the paper
    # pools every survey answer from June and July. Before that, the daily Nowcast takes each pollster's latest
    # poll from the last 30 days and lets newer polls count more.
    pooled = mode == "official"
    nat = approval.national_average(national_polls, w_lo, w_hi, populations=pops, pooled=pooled)
    # For the site's "latest data" page only: the same average with every poll counted, voters included.
    nat_all = None
    if pops:
        try:
            nat_all = approval.national_average(national_polls, w_lo, w_hi, pooled=pooled)
        except RuntimeError:
            pass
    # For the site's "latest data" page only: the approval average as it stood each week of the term, as a
    # trailing 30-day average. The models read only today's value.
    appr_trend, span = [], trailing
    t_day = dt.date.fromisoformat(cfg["election"]["term_start_month"] + "-01") + dt.timedelta(days=span)
    while t_day < w_hi:
        try:
            a_t = approval.national_average(national_polls, t_day - dt.timedelta(days=span), t_day, populations=pops)
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

    # VP gap: (sitting VP net approval) - (president net approval), from surveys that asked about both among the
    # same group of people; favorability if no approval polls
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
            g, basis = candidates.vp_gap(*sources[kind], lo, g_hi, approval._iso, kind, min_vp=need, who=approval.pollster_key)
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
    if os.path.exists(ds_path) and live:
        desart_final = json.load(open(ds_path))
    elif today >= ds_lo:
        ds_rows, ds_skipped = candidates.general_matchups(pres_raw, ds_lo, ds_hi, approval._iso, registry, exclude=barred)
        desart_final = {"window": [ds_lo.isoformat(), ds_hi.isoformat()], "polls": ds_rows, "skipped": ds_skipped,
                        "people": off_list(ds_rows), "terms": terms, "as_of": today.isoformat(), "frozen": False}
        if live and today >= dt.date.fromisoformat(el["desart_freeze_day"]):
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
                     "populations": pops, "pooled": pooled,
                     "all_polls": nat_all and {"approve": round(nat_all["approve"], 1), "disapprove": round(nat_all["disapprove"], 1),
                                               "pollsters": nat_all["pollsters"]},
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

    # An author's own published 2028 forecast, once it is out and has been put in (pipeline/put_in.py), replaces
    # the site's own run of that model: DeSart's the long-range half, Enns and colleagues' the approval half.
    # The site's own runs are still computed and go to the daily record, so the two can be compared later.
    published = load_published(cfg, results)
    if published:
        payload["published"], payload["model_sources"] = published, sources_of(published)
        print("Published forecasts in use: " + "; ".join(f"{m} ({p.get('short') or p.get('authors')}, published {p['published']})"
                                                           for m, p in published.items()))

    # Run both models on the payload with the same code the site uses, so the numbers agree.
    def pick(role, side, key):
        t = tickets[side].get(key) or {}
        return {"name": t.get("name") or "", "state": codes[role]} if codes[role] else None
    sim = {"n": cfg["simulation"]["n_per_delta"], "seed": cfg["simulation"]["seed"],
           "picks": {"dp": pick("dem_president_home", "dem", "president"), "rp": pick("rep_president_home", "rep", "president"),
                     "dv": pick("dem_vp_home", "dem", "vp"), "rv": pick("rep_vp_home", "rep", "vp")},
           "force_vp_shift": gap if vpc.get("mode") == "manual" and gap is not None else None}
    out = run_models({"N": payload, **sim, "own": bool(published)})
    extra = {a: {"approve": round(s["approve"], 1), "econ": round(s["inputs"]["econ"], 4)} for a, s in by_abbr.items()}
    res, dem_ev_point = results_into(payload, out, extra)

    # The final forecast: the Nowcast as it stands on publish_day (Aug 6, 2028), frozen and never changed after.
    # By then its approval half uses polls conducted June 1 - July 30 (the paper's window) and its polls half the
    # frozen October 2027 set, so the Nowcast that day is each paper's forecast.
    fc_path = os.path.join(frozen_dir, "forecast_2028.json")
    if live and os.path.exists(fc_path):
        final = json.load(open(fc_path))
    elif (live and today >= dt.date.fromisoformat(el["publish_day"]) and desart_final and desart_final.get("frozen")
          and degraded and (today - dt.date.fromisoformat(el["publish_day"])).days < el.get("publish_retry_days", 3)):
        # A source could not be read today. The forecast is frozen for good, so it waits for a clean read
        # (the next run, or tomorrow's); after publish_retry_days it is published with what there is.
        print(f"WARNING: the final forecast was NOT published today: could not read {', '.join(sorted(set(degraded)))}; will retry")
        final = None
    elif live and today >= dt.date.fromisoformat(el["publish_day"]) and desart_final and desart_final.get("frozen"):
        # The Nowcast already runs the frozen October 2027 polls as DeSart publishes them, and any published
        # forecast that has been put in. The inputs are kept too, so that an author's forecast that comes out
        # after today can still replace the site's own run that stood in for it (late_put_in).
        final = final_forecast(payload, out, tickets, desart_final, today.isoformat(), published)
        os.makedirs(frozen_dir, exist_ok=True)
        json.dump(final, open(fc_path, "w"), indent=1)
        json.dump({"sim": sim, "payload": payload}, open(os.path.join(frozen_dir, "nowcast_2028.json"), "w"))
        print(f"Published the final 2028 forecast: Dem win {res['pDemWin']:.1%}, Dem popular {res['demPopular']:.2f}%")
    else:
        final = None
    if final is not None:
        write_js("forecast.js", "The final 2028 forecast, frozen on its publish day. Do not edit.", "FORECAST", final)

    write_js("nowcast.js", "Generated by pipeline/update.py. Do not edit.", "NOWCAST", payload)

    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    if not fx:
        # v5, from November 20, 2026: the national approval average counts polls of all adults only. Days before
        # that counted polls of voters too; they are kept in pipeline/history_v4.json and are not part of this series.
        # Today's row is replaced; a row dated after today (written by a run stamped with the wrong day) is dropped.
        hist = [h for h in hist if h.get("v") == 5 and h["date"] < today.isoformat()]
        mp = payload["models"]
        # The run's figures go in unrounded, like the day's own page, so the log prints what the page printed.
        hist.append({"v": 5, "date": today.isoformat(), "pDemWin": res["pDemWin"],
                     "demPopular": res["demPopular"], "approve": round(nat["approve"], 1),
                     "econThrough": econ_last,
                     # Added Nov 2026 for the "latest data" page; earlier days lack them.
                     "enns": mp["enns"] and mp["enns"]["pDemWin"], "desart": mp["desart"] and mp["desart"]["pDemWin"],
                     "pollAvg": mp["polls"] and mp["polls"]["avg"], "h2hN": len(matchups),
                     "apprN": nat["pollsters"], "ev": dem_ev_point})
        hist.sort(key=lambda h: h["date"])
        json.dump(hist, open(hist_path, "w"), indent=1)
    with open(os.path.join(ROOT, "docs", "history.js"), "w") as f:
        f.write("window.NOWCAST_HISTORY = " + json.dumps(hist) + ";\n")

    # A fuller record of the day, kept for later research: the whole Nowcast, a row of headline numbers, a row for
    # every state, and what changed since the last run in plain words (pipeline/daily_log.py). Nothing on the site
    # reads it, and a problem writing it never stops the run.
    # When an author's published forecast has been put in, the site's own runs of the two models are still
    # computed (out["own"]) and recorded here, marked "site run", so the two can be compared after the election.
    if not fx or args.log_dir:
        try:
            noted = daily_log.record(payload, cfg, today, approval_polls=nat["polls"], own=own_runs(out, extra),
                                     log_dir=args.log_dir or daily_log.LOG_DIR)
            print("Daily record: " + (" ".join(noted) if noted else "nothing changed since the last run"))
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: the daily record was not written ({e})")

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
