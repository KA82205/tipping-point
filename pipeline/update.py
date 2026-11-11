"""Fetch the latest data, build model inputs, run the engine, write site data.

    FRED_API_KEY=... python pipeline/update.py
    python pipeline/update.py --fixtures pipeline/tests/fixtures   # offline test run

Every input is gathered automatically:
    economy      FRED (Philadelphia Fed state coincident indexes)
    approval     VoteHub + PollResults.org national polls; state polls when they exist
    candidates   Wikipedia (nominees, running mates, home states, sitting VP)
    VP gap       VoteHub favorability of the sitting VP and the president

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

import approval  # noqa: E402
import candidates  # noqa: E402
import economy  # noqa: E402

DISTRICTS = {"ME1": "ME", "ME2": "ME", "NE1": "NE", "NE2": "NE", "NE3": "NE"}


def home_code(st, dem, rep):
    return (1 if st == dem else 0) - (1 if st == rep else 0)


def build_inputs(cfg, econ_by_delta, approve_by_state, results, codes, vp_shift):
    el, a = cfg["election"], cfg["approval"]
    states = {k: v for k, v in results.items() if len(k) == 2}
    tot = sum(v["votes"] for v in states.values())
    nat = sum(v["share"] * v["votes"] for v in states.values()) / tot
    sign = 1.0 if el["incumbent_party"] == "D" else -1.0
    main = econ_by_delta[cfg["economy"]["delta"]]
    out = []
    for st, v in states.items():
        out.append({
            "abbr": st, "ev": v["ev"], "pop": v["votes"],
            "inputs": {
                "lagDev": v["share"] - nat,
                "approval": sign * (approve_by_state[st] + vp_shift - a["constant"]),
                "econ": main[st],
                "home": home_code(st, codes["dem_president_home"], codes["rep_president_home"]),
                "homeLag": home_code(st, codes["dem_president_home_lag"], codes["rep_president_home_lag"]),
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

        def fav(subject_slug):
            try:
                return approval.fetch_votehub(cfg["approval"]["votehub_fav_url"].format(slug=subject_slug))
            except Exception as e:
                print(f"WARNING: favorability fetch for {subject_slug} failed ({e})")
                return []
        os.makedirs(cache, exist_ok=True)
        json.dump({"polls": polls}, open(os.path.join(cache, "votehub.json"), "w"))
        json.dump({"results": pr_raw}, open(os.path.join(cache, "pollresults.json"), "w"))

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

    # VP gap: (sitting VP net favorability) - (president net favorability)
    vpc = cfg["vp_adjustment"]
    sitting_vp = detected.get("sitting_vp") or "JD Vance"
    if mode == "official":
        g_lo, g_hi = w_lo, w_hi
    else:
        g_lo, g_hi = today - dt.timedelta(days=vpc.get("trailing_days", 60)), today
    if vpc.get("mode") == "manual" and vpc.get("vp_net") is not None:
        gap, gap_basis = vpc["vp_net"] - vpc["president_net"], "manual values in config.json"
    else:
        gap, gap_basis = candidates.vp_gap(fav(slug(sitting_vp)), fav(slug(cfg["election"]["incumbent_president"])),
                                           g_lo, g_hi, approval._iso)
    applied = (vp_is_nominee or vpc.get("mode") == "manual") and gap is not None
    vp_shift = gap if applied else 0.0

    states, districts, nat_dem, sign = build_inputs(cfg, econ, by_state, results, codes, vp_shift)

    sim_in = {"states": states, "districts": districts,
              "n_per_delta": cfg["simulation"]["n_per_delta"], "seed": cfg["simulation"]["seed"],
              "econ_variants": [econ[d] for d in cfg["economy"]["delta_grid"]]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sim_in, f)
    res = json.loads(subprocess.check_output(["node", os.path.join(HERE, "run_forecast.js"), f.name]))
    os.unlink(f.name)

    by_abbr = {s["abbr"]: s for s in states}
    dem_ev_point = sum(s["ev"] for s in res["states"] if s["demShare"] > 50)
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
        "vp": {"gap": None if gap is None else round(gap, 2), "basis": gap_basis, "applied": applied,
               "window": [g_lo.isoformat(), g_hi.isoformat()]},
        "summary": {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                    "demEvPoint": dem_ev_point, "simulations": res["simulations"]},
        "evHistogram": [round(x, 5) for x in res["evHistogram"]],
        "states": [{**s, "demShare": round(s["demShare"], 2), "pDem": round(s["pDem"], 4),
                    "approve": round(by_abbr[s["abbr"]]["approve"], 1) if s["abbr"] in by_abbr else None,
                    "econ": round(by_abbr[s["abbr"]]["inputs"]["econ"], 4) if s["abbr"] in by_abbr else None}
                   for s in res["states"]],
        # Everything the in-browser matchup builder needs to rerun the model.
        "scenario": {
            "constant": cfg["approval"]["constant"], "sign": sign,
            "homeLag": {"dem": codes["dem_president_home_lag"], "rep": codes["rep_president_home_lag"]},
            "states": [{"abbr": s["abbr"], "ev": s["ev"], "pop": s["pop"], "lagDev": r4(s["inputs"]["lagDev"]),
                        "approve": r4(s["approve"])} for s in states],
            "econVariants": [{k: r4(v) for k, v in econ[d].items()} for d in cfg["economy"]["delta_grid"]],
            "districts": [{**d, "offset": r4(d["offset"])} for d in districts],
            "candidates": registry,
        },
    }
    with open(os.path.join(ROOT, "docs", "nowcast.js"), "w") as f:
        f.write("// Generated by pipeline/update.py. Do not edit.\nwindow.NOWCAST = " + json.dumps(payload) + ";\n")

    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    if not fx:
        hist = [h for h in hist if h["date"] != today.isoformat()]
        hist.append({"date": today.isoformat(), "pDemWin": round(res["pDemWin"], 4),
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
    print(f"Tickets: {who}; sitting VP {sitting_vp}; VP gap {gap} ({gap_basis}), applied={applied}")
    print(f"{today} [{mode}] approval {nat['approve']:.1f}% ({nat['pollsters']} pollsters), "
          f"economy through {econ_last}; Dem win {s['pDemWin']:.1%}, Dem popular {s['demPopular']:.2f}%, "
          f"point EV {dem_ev_point}")


if __name__ == "__main__":
    main()
