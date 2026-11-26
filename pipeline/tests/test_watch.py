"""The watch for the authors' publications: what counts as one, and that looking never breaks a run.

    python pipeline/tests/test_watch.py
"""
import json, os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import watch  # noqa: E402


def crossref(items):
    return lambda url, timeout=40: {"message": {"items": items if "DeSart" in url else []}}


ITEMS = [{"DOI": "10.1017/S1049096528000001", "title": ["A Long-Range State-Level 2028 Presidential Election Forecast"], "author": [{"family": "DeSart", "given": "Jay A."}], "issued": {"date-parts": [[2027, 11, 14]]}, "container-title": ["PS: Political Science & Politics"]},
         {"DOI": "10.1017/S1049096524000805", "title": ["Long-Range State-Level 2024 Presidential Election Forecast"], "author": [{"family": "DeSart"}], "issued": {"date-parts": [[2024, 10]]}, "container-title": ["PS"]},
         {"DOI": "10.1000/other", "title": ["Forecasting the 2028 Presidential Election with Yard Signs"], "author": [{"family": "Smith"}], "issued": {"date-parts": [[2028, 1]]}, "container-title": ["X"]}]


def test_watch():
    path = os.path.join(tempfile.mkdtemp(), "watch.json")
    state, words = watch.refresh("2027-11-20", path, crossref(ITEMS)); got = json.load(open(path))
    assert state == "new" and "2028 Presidential Election Forecast" in words and len(got["found"]) == 1, (state, words)          # the 2024 paper and another author's are not it
    assert got["found"][0]["model"] == "the long-range model" and got["found"][0]["published"] == "2027-11-14" and got["found"][0]["url"].startswith("https://doi.org/10.1017/")
    assert watch.refresh("2027-11-20", path, crossref(ITEMS))[0] == "early"                                                          # once a day
    assert watch.refresh("2027-11-21", path, crossref(ITEMS))[0] == "same"                                                           # already known: said once, not every day
    def down(url, timeout=40): raise ConnectionError("no answer")
    assert watch.refresh("2027-11-22", path, down)[0] == "unreachable" and len(json.load(open(path))["found"]) == 1                 # the list stays
    assert watch.refresh("2026-11-25", os.path.join(tempfile.mkdtemp(), "w.json"), crossref([]))[0] == "same"                       # nothing published yet


if __name__ == "__main__":
    test_watch(); print("ok (the watch for the authors' publications)")
