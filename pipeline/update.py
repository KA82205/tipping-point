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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import urllib.request

import approval  # noqa: E402
import candidates  # noqa: E402
import economy  # noqa: E402


def refresh_morris_state_approval(csv_path):
    """Fetch the latest state-level Trump approval estimates from G. Elliott Morris's
    Trump Approval Explorer (projects.gelliottmorris.com/trump-approval) and write them
    to state_approval.csv.  Falls back silently if the fetch fails so that the previous
    CSV is kept.  Returns True on success."""
    try:
        url = "https://projects.gelliottmorris.com/trump-approval/assets/index-BHx_LEl6.js"
        req = urllib.request.Request(url, headers={"User-Agent": "tipping-point-forecast/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            js = r.read().decode("utf-8", errors="replace")
        # Extract abbrev/approval pairs: abbrev:"AK",approval:40.3
        pairs = re.findall(r'abbrev:"([A-Z]{2})",approval:([0-9]+(?:\.[0-9]+)?)', js)
        if len(pairs) < 40:
            print(f"WARNING: Morris data fetch only returned {len(pairs)} states; keeping previous CSV")
            return False
        import csv as _csv
        state_map = {abbr: float(appr) for abbr, appr in pairs}
        if "DC" not in state_map:
            # Not in the source. Keep the value already in the CSV (an assumed 15.0 to begin with).
            state_map["DC"] = 15.0
            if os.path.exists(csv_path):
                for row in _csv.DictReader(open(csv_path)):
                    if row.get("state") == "DC":
                        state_map["DC"] = float(row["approve"])
        with open(csv_path, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["state", "approve"])
            for st in sorted(state_map):
                w.writerow([st, state_map[st]])
        print(f"Morris state approval updated: {len(state_map)} states written to {os.path.basename(csv_path)}")
        return True
    except Exception as e:
        print(f"WARNING: Morris state approval refresh failed ({e}); keeping previous CSV")

DISTRICTS = {"ME1": "ME", "ME2": "ME", "NE1": "NE", "NE2": "NE", "NE3": "NE"}


def home_code(st, dem, rep):
    return (1 if st == dem else 0) - (1 if st == rep else 0)


def home_lag_weights(cfg):
    """Share of the previous nominees' home-state fade that is applied (the paper uses 1)."""
    c = cfg["candidates"]
    return {"dem": c.get("dem_president_home_lag_weight", 1), "rep": c.get("rep_president_home_lag_weight", 1)}


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
    ap.add_argument("--today", help="YYYY-MM-DD, defaults to today (UTC)")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "config.json")))
    results = json.load(open(os.path.join(HERE, "results_2024.json")))
    registry = json.load(open(os.path.join(HERE, "candidates.json")))["candidates"]
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    cache = os.path.join(HERE, "cache")
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
        wiki = None

        def _subject(kind, key):
            def get(subject_slug):
                try:
                    return approval.fetch_votehub(cfg["approval"][key].format(slug=subject_slug))
                except Exception as e:
                    print(f"WARNING: {kind} fetch for {subject_slug} failed ({e})")
                    return []
            return get
        fav = _subject("favorability", "votehub_fav_url")
        appr = _subject("approval", "votehub_subject_approval_url")
        try:
            pres_raw = approval.fetch_pollresults(cfg["approval"]["pollresults_president_url"], max_pages=4)
        except Exception as e:  # only used to order the candidate list
            print(f"WARNING: PollResults 2028 primary polls fetch failed ({e})")
            pres_raw = []
        os.makedirs(cache, exist_ok=True)
        json.dump({"polls": polls}, open(os.path.join(cache, "votehub.json"), "w"))
        json.dump({"results": pr_raw}, open(os.path.join(cache, "pollresults.json"), "w"))
        json.dump({"results": pres_raw}, open(os.path.join(cache, "pollresults_president.json"), "w"))

    # Refresh Morris state-level approval estimates (CSV source)
    if cfg["approval"].get("state_source") == "csv":
        csv_path = os.path.join(HERE, "state_approval.csv")
        refresh_morris_state_approval(csv_path)

    # Economy and approval
    econ, econ_last, _ = economy.build_economy(cfg, None if fx else key, cache, fetch=fred)
    w_lo, w_hi, mode = approval.window_for(cfg, today)
    national_polls, state_polls = approval.merge_polls(polls, pr_raw)
    if pr_raw and not any(p.get("source") == "pollresults" for p in national_polls) and not state_polls:
        print(f"WARNING: could not read any of {len(pr_raw)} PollResults records; check pipeline/cache/pollresults.json")
    nat = approval.national_average(national_polls, w_lo, w_hi)
    by_state, state_used = approval.state_approval(cfg, nat["approve"], results, state_polls=state_polls, window=(w_lo, w_hi))

    # Who is running, home states, sitting VP
    detected = candidates.detect(cfg, fetch=wiki)
    codes, tickets, vp_is_nominee = candidates.resolve(cfg, detected)
    for n in detected["notes"]:
        print("WARNING:", n)

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
            lo = g_lo if usual else today - dt.timedelta(days=days)
            g, basis = candidates.vp_gap(*sources[kind], lo, g_hi, approval._iso, kind, min_vp=need)
            if g is not None:
                gap, gap_kind, g_lo = g, kind, lo
                gap_basis = basis if usual else f"{basis} from the last {days} days"
                break
    # ASSUMPTION (not in the paper): a gap measured from few polls is counted only in part.
    # It reaches full weight at full_weight_polls polls of the vice president.
    gap_raw, gap_polls, gap_weight = gap, None, 1.0
    if gap is not None and vpc.get("mode") != "manual":
        m = re.search(r"\d+", gap_basis)
        gap_polls = int(m.group()) if m else 0
        full = vpc.get("full_weight_polls", 20)
        gap_weight = min(1.0, gap_polls / full) if full else 1.0
        if gap_weight < 1:
            gap = gap_raw * gap_weight
            gap_basis += f"; counted at {gap_weight:.0%} of {gap_raw:+.1f} until there are {full} polls"
    applied = (vp_is_nominee or vpc.get("mode") == "manual") and gap is not None
    vp_shift = gap if applied else 0.0

    states, districts, nat_dem, sign = build_inputs(cfg, econ, by_state, results, codes, vp_shift)

    # National head-to-head polls between listed candidates, for the second model (DeSart 2025).
    hh = cfg.get("head_to_head", {})
    h_lo = today - dt.timedelta(days=hh.get("window_days", 180))
    matchups, h_skipped = candidates.general_matchups(pres_raw, h_lo, today, approval._iso, registry)
    terms = (1 if cfg["election"]["incumbent_party"] == "D" else -1) * cfg["election"].get("incumbent_party_terms", 1)

    by_abbr = {s["abbr"]: s for s in states}
    r4 = lambda x: round(x, 4)  # noqa: E731
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "as_of": today.isoformat(),
        "mode": mode,
        "fixture_run": bool(fx),
        "approval": {"approve": round(nat["approve"], 1), "disapprove": round(nat["disapprove"], 1),
                     "window": [w_lo.isoformat(), w_hi.isoformat()], "pollsters": nat["pollsters"],
                     "polls": nat["polls"][:25], "state_source": cfg["approval"]["state_source"],
                     "state_polls_used": state_used},
        "economy": {"through": econ_last, "delta": cfg["economy"]["delta"]},
        "tickets": tickets,
        "sitting_vp": sitting_vp,
        "vp": {"gap": None if gap is None else round(gap, 2), "kind": gap_kind, "basis": gap_basis, "applied": applied,
               "raw_gap": None if gap_raw is None else round(gap_raw, 2), "polls": gap_polls, "weight": round(gap_weight, 2),
               "window": [g_lo.isoformat(), g_hi.isoformat()]},
        "h2h": {"window": [h_lo.isoformat(), today.isoformat()], "days": hh.get("window_days", 180),
                "min_polls": hh.get("min_polls", 3), "terms": terms, "polls": matchups, "skipped": h_skipped},
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

    with open(os.path.join(ROOT, "docs", "nowcast.js"), "w") as f:
        f.write("// Generated by pipeline/update.py. Do not edit.\nwindow.NOWCAST = " + json.dumps(payload) + ";\n")

    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    if not fx:
        # v4: average of three models. Earlier days used fewer models and are dropped.
        hist = [h for h in hist if h.get("v") == 4 and h["date"] != today.isoformat()]
        hist.append({"v": 4, "date": today.isoformat(), "pDemWin": round(res["pDemWin"], 4),
                     "demPopular": round(res["demPopular"], 2), "approve": round(nat["approve"], 1),
                     "econThrough": econ_last})
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
