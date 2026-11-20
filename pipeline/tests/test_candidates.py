"""Nominee detection against real Wikipedia infobox text (2024 filled in; 2028 empty)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import candidates  # noqa: E402

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config.json")))

BOX_2024 = """{{Infobox election
| nominee1 = '''[[Donald Trump]]'''
| party1 = Republican Party (United States)
| home_state1 = [[Florida]]
| running_mate1 = '''[[JD Vance]]'''
| nominee2 = [[Kamala Harris]]
| party2 = Democratic Party (United States)
| home_state2 = [[California]]
| running_mate2 = [[Tim Walz]]
}}"""
BOX_2028 = """{{Infobox election
| nominee1           = 
| party1             = Republican Party (United States)
| home_state1        = 
| running_mate1      = 
| nominee2           = 
| party2             = Democratic Party (United States)
}}"""
VP = "{{Infobox official post\n| incumbent = [[JD Vance]]\n}}"
WALZ = "{{Infobox officeholder\n| office1 = Ranking Member of the [[X|House Veterans' Affairs Committee]]\n| state2 = [[Minnesota]]\n}}"
NOBODY = "{{Infobox person\n| office = [[Governor of New Mexico]]\n}}"


def fetcher(election_box):
    pages = {CFG["election"]["wiki_article"]: election_box, "Vice President of the United States": VP,
             "Tim Walz": WALZ, "Some Governor": NOBODY}
    return lambda title: pages.get(title, "")


def test_filled_infobox():
    d = candidates.detect(CFG, fetch=fetcher(BOX_2024))
    assert d["rep"]["president"] == {"name": "Donald Trump", "state": "FL", "state_source": "Wikipedia infobox (home_state)"}, d
    assert d["rep"]["vp"]["name"] == "JD Vance" and d["rep"]["vp"]["state"] == "OH"
    assert d["dem"]["president"]["state"] == "CA" and d["dem"]["vp"]["state"] == "MN"
    assert d["sitting_vp"] == "JD Vance"
    codes, tickets, vp_nom = candidates.resolve(CFG, d)
    assert codes["rep_president_home"] == "FL" and codes["dem_vp_home"] == "MN"
    assert vp_nom is False  # Trump is not the sitting VP


def test_vp_is_nominee():
    box = BOX_2024.replace("'''[[Donald Trump]]'''", "[[JD Vance]]").replace("[[Florida]]", "[[Ohio]]")
    d = candidates.detect(CFG, fetch=fetcher(box))
    _, _, vp_nom = candidates.resolve(CFG, d)
    assert vp_nom is True


def test_empty_infobox_and_lookup():
    d = candidates.detect(CFG, fetch=fetcher(BOX_2028))
    assert d["dem"] == {} and d["rep"] == {}
    assert candidates.home_state_of("Tim Walz", [], fetcher(BOX_2028)) == ("MN", "Wikipedia infobox (state2)")
    assert candidates.home_state_of("Some Governor", [], fetcher(BOX_2028))[0] == "NM"


def test_vp_gap():
    import datetime as dt
    iso = lambda d: d  # noqa: E731
    mk = lambda who, f, u, day: {"pollster": who, "end_date": day, "answers": [{"choice": "Favorable", "pct": f}, {"choice": "Unfavorable", "pct": u}]}  # noqa: E731
    vp = [mk(p, 40, 50, "2026-11-01") for p in "ABC"]
    pr = [mk(p, 40, 56, "2026-11-01") for p in "ABC"]
    g, basis = candidates.vp_gap(vp, pr, dt.date(2026, 10, 1), dt.date(2026, 11, 11), iso)
    assert abs(g - 6) < 1e-9 and "both" in basis
    ap = lambda who, a, d: {"pollster": who, "end_date": "2026-11-01", "answers": [{"choice": "Approve", "pct": a}, {"choice": "Disapprove", "pct": d}]}  # noqa: E731
    g, basis = candidates.vp_gap([ap(p, 40, 48) for p in "ABC"], [ap(p, 37, 59) for p in "ABC"],
                                 dt.date(2026, 10, 1), dt.date(2026, 11, 11), iso, "approval")
    assert abs(g - 14) < 1e-9
    assert candidates.vp_gap(vp, pr, dt.date(2026, 10, 1), dt.date(2026, 11, 11), iso, "approval")[0] is None


def test_primary_standing():
    import datetime as dt
    import approval
    poll = lambda who, sub, rows, day="11/2/26", state="US": {"pollster": who, "state": state, "endDate": day, "questions": [  # noqa: E731
        {"stage": "primary", "subpopulation": sub, "answers": [{"candidateName": n, "pct": v} for n, v in rows]},
        {"stage": "general", "answers": [{"candidateName": "JD Vance", "pct": 45}, {"candidateName": "Gavin Newsom", "pct": 47}]}]}
    raw = [poll("A", "d", [("Gavin Newsom", 24), ("Pete Buttigieg", 14), ("Undecided", 30)]),
           poll("B", "d", [("Gavin Newsom", 20), ("Pete Buttigieg", 16), ("New Person", 9)]),
           poll("A", "d", [("Gavin Newsom", 90), ("Pete Buttigieg", 1)], day="9/1/26"),      # older poll by the same pollster
           poll("C", "d", [("Gavin Newsom", 99), ("Pete Buttigieg", 1)], state="NH"),         # state poll, ignored
           poll("A", "r", [("J.D. Vance", 50), ("Marco Rubio", 10), ("Donald Trump", 30)])]
    s = candidates.primary_standing(raw, dt.date(2026, 8, 1), dt.date(2026, 11, 11), approval._iso)
    assert [(r["name"], r["pct"]) for r in s["D"]] == [("Gavin Newsom", 22.0), ("Pete Buttigieg", 15.0), ("New Person", 9.0)], s
    assert s["R"][0] == {"name": "J.D. Vance", "pct": 50.0, "polls": 1}
    reg = [{"name": "JD Vance", "party": "R", "state": "OH", "aliases": ["J. D. Vance"]}, {"name": "Gavin Newsom", "party": "D", "state": "CA"}]
    wiki = lambda title: "| state = [[Vermont]]" if title == "New Person" else ""  # noqa: E731
    out = candidates.merge_registry(reg, s, fetch=wiki, exclude=["Donald Trump"])
    by = {c["name"]: c for c in out}
    assert by["JD Vance"]["primary"] == 50.0 and by["Gavin Newsom"]["primary"] == 22.0
    assert by["New Person"]["state"] == "VT" and by["New Person"]["auto"] is True
    assert "Donald Trump" not in by and "Pete Buttigieg" not in by and "Marco Rubio" not in by  # no home state found
    assert "primary" not in reg[0]  # the input list is not modified


if __name__ == "__main__":
    test_filled_infobox(); test_vp_is_nominee(); test_empty_infobox_and_lookup(); test_vp_gap(); test_primary_standing(); print("ok")

import datetime as dt  # noqa: E402

# Head-to-head matchups: every named Democrat vs named Republican counts, listed or not;
# generic party labels and three-way questions do not.
def _q(*ans):
    return {"stage": "general", "population": "rv", "answers": [{"candidateName": n, "party": p, "pct": v} for n, p, v in ans]}
_raw = [{"state": "US", "endDate": "2026-11-01", "pollster": "A", "questions": [
    _q(("Gavin Newsom", "DEM", 48), ("JD Vance", "REP", 44)),
    _q(("Mark Cuban", "DEM", 47), ("JD Vance", "REP", 41)),
    _q(("Generic Democrat", "DEM", 50), ("JD Vance", "REP", 42)),
    _q(("Gavin Newsom", "DEM", 45), ("Generic Republican", "REP", 44)),
    _q(("Gavin Newsom", "DEM", 44), ("JD Vance", "REP", 40), ("Aaron Rodgers", "IND", 9)),
    _q(("Barack Obama", "DEM", 52), ("Donald Trump", "REP", 42)),
]}]
_reg = [{"name": "Gavin Newsom", "party": "D", "state": "CA"}, {"name": "JD Vance", "party": "R", "state": "OH"}]
_rows, _skipped = candidates.general_matchups(_raw, dt.date(2026, 10, 1), dt.date(2026, 11, 13), lambda d: d, _reg,
                                              exclude=["Donald Trump", "Barack Obama"])
assert sorted(r["d"] for r in _rows) == ["Gavin Newsom", "Mark Cuban"], _rows
assert _skipped == 4, _skipped
print("ok (matchups)")


# National approval: with populations=["a"] only polls of all adults count, as in the paper.
import approval  # noqa: E402


def _ap(name, day, pop, yes, no, n=1000):
    return {"pollster": name, "end_date": day, "population": pop, "sample_size": n,
            "answers": [{"choice": "Approve", "pct": yes}, {"choice": "Disapprove", "pct": no}]}
_np = [_ap("A", "2026-11-10", "a", 34, 62), _ap("B", "2026-11-10", "rv", 40, 57), _ap("A", "2026-11-12", "rv", 36, 61, 900)]
_all = approval.national_average(_np, dt.date(2026, 10, 20), dt.date(2026, 11, 19))
_ad = approval.national_average(_np, dt.date(2026, 10, 20), dt.date(2026, 11, 19), populations=["a"])
assert _all["pollsters"] == 2 and _ad["pollsters"] == 1, (_all, _ad)
assert _ad["approve"] == 34 and _ad["disapprove"] == 62, _ad   # pollster A's sample of adults, not its later sample of voters
assert _all["approve"] > 36, _all
assert CFG["approval"]["national_populations"] == ["a"]
# In the paper's window every poll counts, by its sample size alone (pooled), not only each pollster's latest.
_pp = [_ap("A", "2026-06-05", "a", 40, 55, 1000), _ap("A", "2026-07-20", "a", 30, 65, 3000), _ap("B", "2026-07-01", "a", 36, 60, 1000),
       _ap("B", "2026-07-01", "rv", 50, 45, 9000)]
_po = approval.national_average(_pp, dt.date(2026, 6, 1), dt.date(2026, 7, 30), populations=["a"], pooled=True)
assert _po["pollsters"] == 2 and len(_po["polls"]) == 3, _po
assert abs(_po["approve"] - (40 * 1000 + 30 * 3000 + 36 * 1000) / 5000) < 1e-9, _po
_la = approval.national_average(_pp, dt.date(2026, 6, 1), dt.date(2026, 7, 30), populations=["a"])
assert _la["pollsters"] == 2 and len(_la["polls"]) == 2 and _la["approve"] < _po["approve"], _la
assert CFG["approval"]["constant"] == 43
print("ok (approval of all adults)")


# Reading the two approval feeds together (approval.merge_polls):
#  - a poll's all-adults figures are kept even when the first feed lists that poll only for voters
#  - a poll both feeds list counts once, however they spell the pollster's name
#  - a question put to one party's voters only is not a national figure
def _pr(name, day, groups, sub=""):   # one PollResults record; groups = [(who was asked, sample size, approve, disapprove)]
    return {"pollster": name, "state": "US", "endDate": day, "internal": "", "partisan": "", "questions": [
        {"population": g, "subpopulation": sub, "sampleSize": n, "answers": [{"politician": "Donald Trump", "yes": y, "no": no}]}
        for g, n, y, no in groups]}
_vh = [_ap("YouGov", "2026-06-29", "rv", 40, 58, 1428), _ap("Marist College", "2026-07-10", "a", 38, 56, 1408),
       _ap("YouGov", "2026-07-06", "a", 39, 57, 1602), _ap("YouGov", "2026-07-06", "a", 40, 60, 1709)]
_prr = [_pr("YouGov", "6/29/26", [("rv", 1428, 40, 58), ("a", 1606, 38, 58)]),   # its adults figures are new
        _pr("Marist University", "7/10/26", [("a", 1408, 38, 56)]),                # the same poll under the pollster's new name
        _pr("YouGov", "7/6/26", [("a", 1602, 39, 57)]),                            # already listed
        _pr("AtlasIntel", "7/1/26", [("a", 3000, 40, 55), ("rv", 2500, 42, 55)]),
        _pr("Tufts", "7/2/26", [("a", 300, 80, 15)], sub="r")]                     # Republicans only
_nat, _states = approval.merge_polls(_vh, _prr)
assert len(_nat) == 7 and not _states, [(p["pollster"], p["end_date"], p["population"]) for p in _nat]
assert [p["sample_size"] for p in _nat if p["pollster"] == "YouGov" and p["end_date"] == "2026-06-29" and p["population"] == "a"] == [1606]
assert approval.pollster_key("Marist College") == approval.pollster_key("Marist University") != approval.pollster_key("YouGov")
_now = approval.national_average(_nat, dt.date(2026, 6, 15), dt.date(2026, 7, 14), populations=["a"])
assert _now["pollsters"] == 3 and len(_now["polls"]) == 3, _now          # YouGov, Marist once, AtlasIntel
# In the paper's window every poll counts once: two YouGov polls that end on the same day are two polls.
_win = approval.national_average(_nat, dt.date(2026, 6, 1), dt.date(2026, 7, 30), populations=["a"], pooled=True)
assert len(_win["polls"]) == 5 and _win["pollsters"] == 3, _win
assert abs(_win["approve"] - (38 * 1606 + 38 * 1408 + 39 * 1602 + 40 * 1709 + 40 * 3000) / (1606 + 1408 + 1602 + 1709 + 3000)) < 1e-9, _win
print("ok (two feeds, one count per poll)")

# The vice-president gap compares like with like: the same survey and the same group of people.
_vpp = [_ap("Ipsos", "2026-04-28", "rv", 39, 49), _ap("Ipsos", "2026-04-28", "a", 35, 48),
        _ap("Quinnipiac University", "2026-05-18", "rv", 39, 54), _ap("CNN/SSRS", "2026-03-30", "a", 37, 62)]
_prs = [_ap("Ipsos", "2026-04-28", "rv", 38, 59), _ap("Ipsos", "2026-04-28", "a", 36, 61),
        _ap("Quinnipiac University", "2026-05-18", "rv", 37, 61), _ap("CNN/SSRS", "2026-03-30", "rv", 40, 58),
        _ap("CNN/SSRS", "2026-03-30", "a", 34, 63)]
_g, _basis = candidates.vp_gap(_vpp, _prs, dt.date(2026, 3, 1), dt.date(2026, 6, 1), lambda d: d, "approval", who=approval.pollster_key)
assert abs(_g - (12 + 9 + 4) / 3) < 1e-9 and _basis.startswith("3 polls"), (_g, _basis)   # adults with adults, voters with voters
print("ok (vice-president gap, like with like)")

# State approval is centred on the national figure by adult population: a national poll of adults is that average.
_res = json.load(open(os.path.join(os.path.dirname(__file__), "..", "results_2024.json")))
_pop = approval.adult_population()
assert len(_pop) == 51 and 2.4e8 < sum(_pop.values()) < 2.7e8
_by, _ = approval.state_approval(CFG, 34.0, _res)
assert abs(sum(_by[s] * _pop[s] for s in _by) / sum(_pop.values()) - 34.0) < 1e-9
print("ok (state approval centred by adult population)")

# The gaps between states count at approval.state_gap_scale: the model was fitted on state estimates whose gaps are
# about half as wide as the source's. The District of Columbia's gap is an assumption of its own and is not scaled.
import copy  # noqa: E402
_k = CFG["approval"]["state_gap_scale"]
assert 0 < _k <= 1, _k
_full_cfg = copy.deepcopy(CFG)
_full_cfg["approval"]["state_gap_scale"] = 1.0
_full, _ = approval.state_approval(_full_cfg, 34.0, _res)
assert abs(sum(_full[s] * _pop[s] for s in _full) / sum(_pop.values()) - 34.0) < 1e-9
for _a, _b in (("WY", "HI"), ("PA", "TX"), ("OK", "MA")):
    assert abs((_by[_a] - _by[_b]) - _k * (_full[_a] - _full[_b])) < 1e-9, (_a, _b)
assert abs(_by["DC"] - _full["DC"]) < 0.05, (_by["DC"], _full["DC"])
_none_cfg = copy.deepcopy(CFG)
del _none_cfg["approval"]["state_gap_scale"]                 # a config without the setting reads the gaps in full
assert approval.state_approval(_none_cfg, 34.0, _res)[0] == _full
print("ok (state gaps counted at %g of the source's)" % _k)

# The daily record (pipeline/daily_log.py): one record a day, a later run on the same day replaces it, and what
# changed since the last record is put in words.
import csv as _csv  # noqa: E402
import tempfile  # noqa: E402
import daily_log  # noqa: E402
_N1 = {"generated_at": "2026-11-20T11:20:00Z", "as_of": "2026-11-20", "mode": "nowcast", "fixture_run": False,
       "approval": {"approve": 34.0, "disapprove": 62.0, "window": ["2026-10-22", "2026-11-20"], "pollsters": 2,
                    "polls": [{"date": "2026-11-16", "approve": 32, "disapprove": 66, "n": 1521, "pollster": "Ipsos", "population": "a"},
                              {"date": "2026-11-10", "approve": 36, "disapprove": 60, "n": 1000, "pollster": "Gallup", "population": "a"}],
                    "state_data": {"name": "Civiqs", "as_of": "2026-11-19", "gap_scale": 0.5}},
       "economy": {"through": "2026-09"}, "tickets": {"dem": {}, "rep": {}}, "sitting_vp": "JD Vance",
       "vp": {"gap": 2.5, "raw_gap": 7.14, "polls": 7, "weight": 0.35, "kind": "approval", "applied": False, "basis": "7 polls"},
       "h2h": {"polls": [{"d": "Gavin Newsom", "r": "JD Vance", "share": 51.0, "date": "2026-11-05", "pollster": "Emerson"}]},
       "desart_final": None, "scenario": {"candidates": [{"name": "JD Vance", "party": "R", "primary": 36.5}]},
       "summary": {"pDemWin": 0.5606, "pTie": 0.0013, "demPopular": 50.76, "demEvPoint": 286},
       "models": {"enns": {"pDemWin": 0.666, "pTie": 0.0009, "demPopular": 51.69},
                  "desart": {"pDemWin": 0.4441, "pTie": 0.0027, "demPopular": 49.85}, "polls": {"avg": 51.0, "n": 1}},
       "states": [{"abbr": "PA", "ev": 19, "demShare": 50.53, "pDem": 0.56, "rating": "TD", "enns": 51.32, "ennsP": 0.65,
                   "desart": 49.7, "desartP": 0.47, "approve": 35.4, "econ": 0.08},
                  {"abbr": "NE2", "ev": 1, "demShare": 53.95, "pDem": 0.87, "rating": "LD", "enns": 55.03, "ennsP": 0.93,
                   "desart": 52.9, "desartP": 0.8, "approve": None, "econ": None}]}
with tempfile.TemporaryDirectory() as _d:
    assert daily_log.record(_N1, CFG, dt.date(2026, 11, 20), log_dir=_d) == ["Record starts."]
    assert daily_log.record(_N1, CFG, dt.date(2026, 11, 20), log_dir=_d) == []           # the same run again: nothing to note
    _N2 = copy.deepcopy(_N1)                                                              # a later day with news
    _N2["approval"]["polls"][1] = {"date": "2026-11-19", "approve": 33, "disapprove": 63, "n": 1100, "pollster": "Gallup", "population": "a"}
    _N2["approval"]["approve"] = 33.6
    _N2["approval"]["state_data"]["as_of"] = "2026-12-03"
    _N2["economy"]["through"] = "2026-10"
    _N2["summary"]["pDemWin"] = 0.57
    _cfg2 = copy.deepcopy(CFG)
    _cfg2["approval"]["state_gap_scale"] = 0.6
    _said = " ".join(daily_log.record(_N2, _cfg2, dt.date(2026, 12, 4), log_dir=_d))
    for _want in ("33.6% approve (was 34.0%)", "in: Gallup to Nov 19", "out: Gallup to Nov 10", "through October 2026",
                  "Civiqs copy of December 3, 2026 (was November 19, 2026)", "approval.state_gap_scale 0.5 to 0.6"):
        assert _want in _said, (_want, _said)
    assert "Head-to-head" not in _said and "Code changed" not in _said, _said
    _days = list(_csv.DictReader(open(os.path.join(_d, "daily.csv"))))
    assert [r["date"] for r in _days] == ["2026-11-20", "2026-12-04"] and _days[1]["dem_win"] == "0.57"
    assert _days[0]["approval_model_from"] == _days[0]["long_range_from"] == "site run"
    _st = list(_csv.DictReader(open(os.path.join(_d, "states.csv"))))
    assert [r["state"] for r in _st] == ["PA", "NE2", "PA", "NE2"] and _st[3]["trump_approval_used"] == ""
    _ch = list(_csv.DictReader(open(os.path.join(_d, "changes.csv"))))
    assert len(_ch) == 2 and _ch[1]["dem_win_before"] == "0.5606" and _ch[1]["dem_win_after"] == "0.57"
    assert sorted(os.listdir(os.path.join(_d, "days"))) == ["2026-11-20.json", "2026-12-04.json"]
    _N3 = copy.deepcopy(_N2)                                                              # a second run the same day
    _N3["summary"]["pDemWin"] = 0.58
    assert daily_log.record(_N3, _cfg2, dt.date(2026, 12, 4), log_dir=_d)[0].startswith("The numbers moved with none of the listed inputs changing")
    assert daily_log.record(_N3, _cfg2, dt.date(2026, 12, 5), log_dir=_d) == []           # the next day, nothing new
    _N3["summary"]["pDemWin"] = 0.581
    assert daily_log.record(_N3, _cfg2, dt.date(2026, 12, 6), log_dir=_d) == ["No new data: the polls are a day older, which shifts their weights a little."]
    _days = list(_csv.DictReader(open(os.path.join(_d, "daily.csv"))))
    assert [r["dem_win"] for r in _days] == ["0.5606", "0.58", "0.58", "0.581"]           # the second run of December 4 replaced the first
    assert len(list(_csv.DictReader(open(os.path.join(_d, "states.csv"))))) == 8
print("ok (daily record)")

# Putting an author's published forecast in (pipeline/put_in.py writes the file, pipeline/update.py reads it).
# The table can name states in full or by two letters, and give the Democratic share, the Republican share, the
# Democratic lead, or each party's share of all votes. Numbers that cannot be Democratic shares are refused.
import put_in  # noqa: E402
import update  # noqa: E402
_dem = {k: v["share"] + 1.5 for k, v in _res.items() if len(k) == 2}          # a made-up forecast: 2024 plus 1.5 points
with tempfile.TemporaryDirectory() as _d:
    def _table(name, rows, delim=","):
        path = os.path.join(_d, name)
        with open(path, "w", newline="") as f:
            _csv.writer(f, delimiter=delim).writerows(rows)
        return path
    _t1 = _table("names.csv", [["State", "Democratic two-party share"]] + [[_res[k]["name"], f"{v:.2f}"] for k, v in _dem.items() if k != "DC"] + [["National", "50.7"]])
    _s1, _n1 = put_in.read_table(_t1, _res)
    assert len(_s1) == 50 and abs(_s1["PA"] - round(_dem["PA"], 2)) < 1e-9 and "National" in _n1[0], (_s1.get("PA"), _n1)
    assert any("District of Columbia" in x for x in put_in.check(_s1, _res))
    _t2 = _table("rep.tsv", [[k, f"{100 - v:.2f}%", "1", "2"] for k, v in _dem.items()], delim="\t")
    _s2, _ = put_in.read_table(_t2, _res, values="rep", column="2")
    assert len(_s2) == 51 and abs(_s2["PA"] - round(_dem["PA"], 2)) < 0.011
    _t3 = _table("lead.csv", [[k, f"{(2 * v - 100) / 100:.4f}"] for k, v in _dem.items()])
    assert abs(put_in.read_table(_t3, _res, values="margin")[0]["PA"] - _dem["PA"]) < 0.011
    _t4 = _table("both.csv", [["state", "dem", "rep", "other"]] + [[k, f"{0.96 * v:.3f}", f"{0.96 * (100 - v):.3f}", "4"] for k, v in _dem.items()])
    assert abs(put_in.read_table(_t4, _res, dem_column="dem", rep_column="rep")[0]["PA"] - _dem["PA"]) < 0.011
    for _bad, _kw in ((_t2, {"column": "2"}),                                    # Republican shares given as Democratic
                      (_table("few.csv", [[k, f"{v:.2f}"] for k, v in list(_dem.items())[:40]]), {})):
        try:
            put_in.check(put_in.read_table(_bad, _res, **_kw)[0], _res)
            raise AssertionError("a table that cannot be a Democratic forecast was accepted")
        except SystemExit:
            pass
    # The file as the daily run reads it. A file with a state missing is not used, and the run carries on.
    _doc = put_in.build("desart", _s1, "2027-11-14", url="https://example.org/forecast", national=51.2, chance=0.61)
    assert _doc["short"] == "DeSart" and _doc["read_from"] == "table" and "electoral_votes" not in _doc
    os.makedirs(os.path.join(_d, "published"))
    json.dump(_doc, open(os.path.join(_d, "published", "desart_2028.json"), "w"))
    json.dump({**_doc, "states": {k: v for k, v in _s1.items() if k != "OH"}}, open(os.path.join(_d, "published", "enns_2028.json"), "w"))
    _pub = update.load_published(CFG, _res, os.path.join(_d, "published"))
    assert list(_pub) == ["desart"] and len(_pub["desart"]["states"]) == 50 and "_comment" not in _pub["desart"], list(_pub)
    assert update.sources_of(_pub) == {"enns": "site run", "desart": "authors' forecast"}
    assert update.published_id(_pub) and update.published_id({}) == "" and update.load_published(CFG, _res, _d) == {}
    # The daily record keeps the site's own runs next to what the site shows.
    _shown = copy.deepcopy(_N1)
    _shown["published"], _shown["model_sources"] = _pub, update.sources_of(_pub)
    _shown["summary"]["pDemWin"] = 0.5167
    _own = {"summary": _N1["summary"], "models": _N1["models"], "states": _N1["states"]}
    assert daily_log.record(_N1, CFG, dt.date(2027, 11, 13), log_dir=_d) == ["Record starts."]
    _said = " ".join(daily_log.record(_shown, CFG, dt.date(2027, 11, 16), own=_own, log_dir=_d))
    assert "long-range half is now the forecast DeSart published on November 14, 2027" in _said, _said
    _row = list(_csv.DictReader(open(os.path.join(_d, "daily.csv"))))[-1]
    assert (_row["dem_win"], _row["site_run_dem_win"], _row["long_range_from"], _row["approval_model_from"]) == ("0.5167", "0.5606", "authors' forecast", "site run"), _row
print("ok (published forecasts put in)")
