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


if __name__ == "__main__":
    test_filled_infobox(); test_vp_is_nominee(); test_empty_infobox_and_lookup(); test_vp_gap(); print("ok")
