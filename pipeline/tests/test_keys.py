"""The keys model: history fit and economy scoring."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import keys  # noqa: E402


def test_fit_matches_history():
    a, b, see, n = keys.fit(keys.load_history())
    assert n == 41
    assert abs(a - 58.26) < 0.01 and abs(b + 2.892) < 0.01


def test_economy_keys():
    fx = os.path.join(HERE, "fixtures")
    gdp = json.load(open(os.path.join(fx, "A939RX0Q048SBEA.json")))
    sahm = json.load(open(os.path.join(fx, "SAHMREALTIME.json")))
    k5, k6 = keys.score_economy(gdp, sahm, "2025-01")
    assert k5["false"] is False and k6["false"] is False
    # a recession signal turns the short-term key false
    k5b, _ = keys.score_economy(gdp, sahm + [["2026-11", 0.6]], "2025-01")
    assert k5b["false"] is True


def test_build_counts_pending_as_half():
    cfg = json.load(open(os.path.join(os.path.dirname(HERE), "config.json")))
    fx = os.path.join(HERE, "fixtures")
    out = keys.build(cfg, lambda sid, k, s: json.load(open(os.path.join(fx, sid + ".json"))), None, 49.25)
    assert out["false"] == 3.0 and out["pending"] == 2
    assert 50.3 < out["demNational"] < 50.5


def _poll(day, pollster, others):
    ans = [{"candidateName": "A Dem", "pct": 45, "party": "DEM"}, {"candidateName": "A Rep", "pct": 40, "party": "REP"},
           {"candidateName": "Don't know", "pct": 5, "party": "NONE"}]
    return {"endDate": day, "pollster": pollster, "state": "US",
            "questions": [{"stage": "general", "answers": ans + [{"candidateName": n, "pct": p, "party": "IND"}
                                                                for n, p in others]}]}


def test_third_party_key_follows_lichtman_rule():
    import datetime as dt
    iso = lambda s: dt.datetime.strptime(s, "%m/%d/%y").date().isoformat()
    today = dt.date(2026, 11, 12)
    # one pollster, under 10%: the key stays true
    weak = [_poll("10/14/26", "YouGov", [("Aaron Rodgers", 7), ("Aaron Rodgers", 6)])]
    k = keys.score_third_party(weak, today, iso)
    assert k["false"] is False and "Aaron Rodgers" in k["why"]
    # 10%+ but only from one pollster, or too old: still true
    one = [_poll(d, "Big Data Poll", [("Thomas Massie", 11)]) for d in ("9/1/26", "10/1/26", "11/1/26")]
    assert keys.score_third_party(one, today, iso)["false"] is False
    old = [_poll("2/18/26", p, [("Thomas Massie", 11)]) for p in ("A", "B", "C")]
    assert keys.score_third_party(old, today, iso) is None
    # 10%+ consistently, 3 polls from 2+ pollsters: the key turns false
    strong = [_poll("9/1/26", "A", [("X Indy", 12)]), _poll("10/1/26", "B", [("X Indy", 10)]),
              _poll("11/1/26", "C", [("X Indy", 9)])]
    assert keys.score_third_party(strong, today, iso)["false"] is True


def test_primary_note():
    note = keys.primary_note({"R": [{"name": "JD Vance", "pct": 48.0}, {"name": "Marco Rubio", "pct": 12.0}]}, "R")
    assert "JD Vance leads with 48%" in note and "two-thirds" in note
