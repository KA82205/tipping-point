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
