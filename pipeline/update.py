"""Fetch the latest data, build model inputs, run the engine, write site data.

    FRED_API_KEY=... python pipeline/update.py
    python pipeline/update.py --fixtures pipeline/tests/fixtures   # offline test run

Writes:
    docs/nowcast.js      window.NOWCAST, read by the 2028 page
    docs/history.js      window.NOWCAST_HISTORY, one row per day
    pipeline/history.json
    pipeline/cache/      raw FRED and VoteHub responses from the last run
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import approval  # noqa: E402
import economy  # noqa: E402

DISTRICTS = {"ME1": "ME", "ME2": "ME", "NE1": "NE", "NE2": "NE", "NE3": "NE"}


def home_code(st, dem, rep):
    return (1 if st == dem else 0) - (1 if st == rep else 0)


def build_inputs(cfg, econ_by_delta, approve_by_state, results):
    c, el, a = cfg["candidates"], cfg["election"], cfg["approval"]
    states = {k: v for k, v in results.items() if len(k) == 2}
    tot = sum(v["votes"] for v in states.values())
    nat = sum(v["share"] * v["votes"] for v in states.values()) / tot
    sign = 1.0 if el["incumbent_party"] == "D" else -1.0
    vp = cfg["vp_adjustment"]
    vp_shift = (vp["vp_net"] - vp["president_net"]) if vp.get("enabled") else 0.0
    main = econ_by_delta[cfg["economy"]["delta"]]
    out = []
    for st, v in states.items():
        out.append({
            "abbr": st, "ev": v["ev"], "pop": v["votes"],
            "inputs": {
                "lagDev": v["share"] - nat,
                "approval": sign * (approve_by_state[st] + vp_shift - a["constant"]),
                "econ": main[st],
                "home": home_code(st, c["dem_president_home"], c["rep_president_home"]),
                "homeLag": home_code(st, c["dem_president_home_lag"], c["rep_president_home_lag"]),
                "vpHome": home_code(st, c["dem_vp_home"], c["rep_vp_home"]),
                "anderson": 0, "perot": 0,
            },
            "approve": approve_by_state[st],
        })
    districts = [{"abbr": d, "parent": p, "ev": 1,
                  "offset": results[d]["share"] - results[p]["share"]} for d, p in DISTRICTS.items()]
    return out, districts, nat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", help="read FRED/VoteHub responses from this folder instead of the network")
    ap.add_argument("--today", help="YYYY-MM-DD, defaults to today (UTC)")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "config.json")))
    results = json.load(open(os.path.join(HERE, "results_2024.json")))
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    cache = os.path.join(HERE, "cache")

    if args.fixtures:
        fred = lambda sid, key, start: json.load(open(os.path.join(args.fixtures, f"{sid}.json")))  # noqa: E731
        polls = json.load(open(os.path.join(args.fixtures, "votehub.json")))["polls"]
        pr_path = os.path.join(args.fixtures, "pollresults.json")
        pr_raw = json.load(open(pr_path))["results"] if os.path.exists(pr_path) else []
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
        os.makedirs(cache, exist_ok=True)
        json.dump({"polls": polls}, open(os.path.join(cache, "votehub.json"), "w"))
        json.dump({"results": pr_raw}, open(os.path.join(cache, "pollresults.json"), "w"))

    econ, econ_last, _ = economy.build_economy(cfg, None if args.fixtures else key, cache, fetch=fred)
    w_lo, w_hi, mode = approval.window_for(cfg, today)
    national_polls, state_polls = approval.merge_polls(polls, pr_raw)
    if pr_raw and not any(p.get("source") == "pollresults" for p in national_polls) and not state_polls:
        print(f"WARNING: could not read any of {len(pr_raw)} PollResults records; check pipeline/cache/pollresults.json")
    nat = approval.national_average(national_polls, w_lo, w_hi)
    by_state, state_used = approval.state_approval(cfg, nat["approve"], results, state_polls=state_polls, window=(w_lo, w_hi))
    states, districts, nat_dem = build_inputs(cfg, econ, by_state, results)

    sim_in = {"states": states, "districts": districts,
              "n_per_delta": cfg["simulation"]["n_per_delta"], "seed": cfg["simulation"]["seed"],
              "econ_variants": [econ[d] for d in cfg["economy"]["delta_grid"]]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sim_in, f)
    res = json.loads(subprocess.check_output(["node", os.path.join(HERE, "run_forecast.js"), f.name]))
    os.unlink(f.name)

    by_abbr = {s["abbr"]: s for s in states}
    dem_ev_point = sum(s["ev"] for s in res["states"] if s["demShare"] > 50)
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "as_of": today.isoformat(),
        "mode": mode,
        "fixture_run": bool(args.fixtures),
        "approval": {"approve": round(nat["approve"], 1), "disapprove": round(nat["disapprove"], 1),
                     "window": [w_lo.isoformat(), w_hi.isoformat()], "pollsters": nat["pollsters"],
                     "polls": nat["polls"][:25], "state_source": cfg["approval"]["state_source"],
                     "state_polls_used": state_used},
        "economy": {"through": econ_last, "delta": cfg["economy"]["delta"]},
        "candidates": cfg["candidates"],
        "summary": {"pDemWin": res["pDemWin"], "pTie": res["pTie"], "demPopular": res["demPopular"],
                    "demEvPoint": dem_ev_point, "simulations": res["simulations"]},
        "evHistogram": [round(x, 5) for x in res["evHistogram"]],
        "states": [{**s, "demShare": round(s["demShare"], 2), "pDem": round(s["pDem"], 4),
                    "approve": round(by_abbr[s["abbr"]]["approve"], 1) if s["abbr"] in by_abbr else None,
                    "econ": round(by_abbr[s["abbr"]]["inputs"]["econ"], 4) if s["abbr"] in by_abbr else None}
                   for s in res["states"]],
    }
    with open(os.path.join(ROOT, "docs", "nowcast.js"), "w") as f:
        f.write("// Generated by pipeline/update.py. Do not edit.\nwindow.NOWCAST = " + json.dumps(payload) + ";\n")

    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    if not args.fixtures:
        hist = [h for h in hist if h["date"] != today.isoformat()]
        hist.append({"date": today.isoformat(), "pDemWin": round(res["pDemWin"], 4),
                     "demPopular": round(res["demPopular"], 2), "approve": round(nat["approve"], 1),
                     "econThrough": econ_last})
        hist.sort(key=lambda h: h["date"])
        json.dump(hist, open(hist_path, "w"), indent=1)
    with open(os.path.join(ROOT, "docs", "history.js"), "w") as f:
        f.write("window.NOWCAST_HISTORY = " + json.dumps(hist) + ";\n")

    s = payload["summary"]
    print(f"{today} [{mode}] approval {nat['approve']:.1f}% ({nat['pollsters']} pollsters), "
          f"economy through {econ_last}; Dem win {s['pDemWin']:.1%}, Dem popular {s['demPopular']:.2f}%, "
          f"point EV {dem_ev_point}")


if __name__ == "__main__":
    main()
