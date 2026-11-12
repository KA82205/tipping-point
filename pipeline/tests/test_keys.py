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
