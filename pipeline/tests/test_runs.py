"""When a run is made, and what is kept of it.

The script runs every hour. It must run the models again when an input has changed and not otherwise, read FRED when a
release could be out, and keep every Nowcast that differs from the one before it in a file that is never written again.

    python pipeline/tests/test_runs.py
"""
import copy
import datetime as dt
import json
import os
import sys
import tempfile
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import daily_log  # noqa: E402
import update  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
ET = ZoneInfo("America/New_York")


def nowcast():
    text = open(os.path.join(ROOT, "docs", "nowcast.js"), encoding="utf-8").read()
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def test_fred_is_read_when_a_release_could_be_out():
    at = lambda d, h: dt.datetime(2026, 12, d, h, 17, tzinfo=ET)                 # December 7, 2026 is a Monday
    assert all(update.economy_due(at(7, h), False) for h in (8, 9, 10, 11, 14, 20))
    assert not any(update.economy_due(at(7, h), False) for h in (0, 5, 7, 12, 13, 16, 23))
    assert [h for h in range(24) if update.economy_due(at(12, h), False)] == [14, 20]        # a Saturday: the fallbacks only
    assert update.economy_due(at(12, 3), True) and update.economy_due(at(12, 3), False, force=True)


def test_the_same_inputs_are_not_run_twice():
    cfg = json.load(open(os.path.join(ROOT, "pipeline", "config.json")))
    n = nowcast()
    base = update.fingerprint(n, cfg)
    again = copy.deepcopy(n); again["generated_at"] = "2031-01-01T00:00:00Z"
    assert update.fingerprint(again, cfg) == base                                 # built at another time, nothing in it new
    def new(edit, c=cfg):
        other = copy.deepcopy(n); edit(other)
        f = update.fingerprint(other, c)
        return [k for k in f if f[k] != base[k]]
    assert new(lambda p: p["h2h"]["polls"].append(dict(p["h2h"]["polls"][0], pollster="A new pollster"))) == ["head-to-head polls"]
    assert new(lambda p: p["approval"].update(approve=p["approval"]["approve"] + 0.1)) == ["approval polls"]
    assert new(lambda p: p["scenario"]["states"][0].update(approve=p["scenario"]["states"][0]["approve"] + 0.1)) == ["model inputs"]
    assert new(lambda p: p["scenario"]["econVariants"][0].update(AL=p["scenario"]["econVariants"][0]["AL"] + 0.001)) == ["model inputs"]   # a new month of a state economy
    assert new(lambda p: p["economy"].update(through="2031-01")) == ["state economies"]
    assert new(lambda p: p.update(as_of="2031-01-02")) == ["the day"]
    assert new(lambda p: p["tickets"]["dem"].update(president={"name": "Somebody"})) == ["nominees"]
    assert new(lambda p: p["scenario"]["candidates"][0].update(primary=1.0)) == ["candidates and primary polls"]
    assert new(lambda p: p.update(something_added_later=1)) == ["other inputs"]                                      # nothing the models read can change unseen
    other_cfg = copy.deepcopy(cfg); other_cfg["simulation"]["seed"] = cfg["simulation"]["seed"] + 1
    assert new(lambda p: None, other_cfg) == ["settings"]


def test_every_different_nowcast_is_kept_once():
    n = nowcast(); folder = tempfile.mkdtemp()
    first = daily_log.keep_run(n, folder)
    assert first == n["generated_at"].replace(":", "") + ".json"
    later = copy.deepcopy(n); later["generated_at"] = "2031-01-01T01:00:00Z"
    assert daily_log.keep_run(later, folder) is None                              # the same numbers an hour later: not kept twice
    later["summary"]["pDemWin"] += 0.0004; later["states"][0]["demShare"] += 0.02
    assert daily_log.keep_run(later, folder) is None                              # nor a difference too small to see
    moved = copy.deepcopy(later); moved["generated_at"] = "2031-01-01T02:00:00Z"; moved["summary"]["pDemWin"] = n["summary"]["pDemWin"] + 0.002
    second = daily_log.keep_run(moved, folder)
    assert second == "2031-01-01T020000Z.json"
    one_state = copy.deepcopy(moved); one_state["generated_at"] = "2031-01-01T03:00:00Z"; one_state["states"][5]["demShare"] += 0.3
    third = daily_log.keep_run(one_state, folder)
    assert third and [e["file"] for e in json.load(open(os.path.join(folder, "index.json")))] == [first, second, third]
    before = open(os.path.join(folder, first)).read()
    clash = copy.deepcopy(n); clash["summary"]["pDemWin"] = 0.99                    # the first file's time stamp again, with other numbers
    try:
        daily_log.keep_run(clash, folder)
    except FileExistsError:
        pass
    else:
        raise AssertionError("a kept Nowcast was written over")
    assert open(os.path.join(folder, first)).read() == before and len(json.load(open(os.path.join(folder, "index.json")))) == 3
    kept = json.loads(before)
    assert len(kept["states"]) == len(n["states"]) and kept["dem_win"] == round(n["summary"]["pDemWin"], 4)


def test_a_whole_run_stops_when_nothing_is_new():
    """The script itself, run three times in a scratch copy on the feeds saved in pipeline/cache: the first run goes
    through, the second finds nothing new and stops before the models, and after a poll is taken out of the feed the
    third goes through again and says what was new."""
    import shutil
    import subprocess
    scratch = tempfile.mkdtemp()
    for part in ("pipeline", "docs"):
        shutil.copytree(os.path.join(ROOT, part), os.path.join(scratch, part), ignore=shutil.ignore_patterns("node_modules", "__pycache__", "log", "record"))
    feeds = os.path.join(scratch, "feeds"); os.makedirs(feeds)
    for name in os.listdir(os.path.join(scratch, "pipeline", "cache")):
        if name != "fingerprint.json":
            shutil.copy(os.path.join(scratch, "pipeline", "cache", name), feeds)
    os.remove(os.path.join(scratch, "pipeline", "cache", "fingerprint.json")) if os.path.exists(os.path.join(scratch, "pipeline", "cache", "fingerprint.json")) else None
    day = max(h["date"] for h in json.load(open(os.path.join(scratch, "pipeline", "history.json"))))
    def run():
        r = subprocess.run([sys.executable, os.path.join(scratch, "pipeline", "update.py"), "--fixtures", feeds, "--gate-in-test", "--today", day],
                           cwd=scratch, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        return r.stdout
    made = lambda: open(os.path.join(scratch, "docs", "nowcast.js")).read()
    first = run(); after_first = made()
    assert "Nothing new" not in first and "Dem win" in first
    second = run()
    assert "Nothing new since the published Nowcast was made" in second and "Dem win" not in second and made() == after_first
    feed = os.path.join(feeds, "votehub.json"); polls = json.load(open(feed))
    old = min(polls["polls"], key=lambda p: p["end_date"])
    json.dump({"polls": [p for p in polls["polls"] if p is not old]}, open(feed, "w"))
    assert "Nothing new" in run()                                                  # a poll from long before the window is not an input: taking it out changes nothing
    newest = max((p for p in polls["polls"] if p.get("population") == "a"), key=lambda p: p["end_date"])
    json.dump({"polls": [p for p in polls["polls"] if p is not newest]}, open(feed, "w"))      # the newest poll of all adults is gone from the feed
    third = run()
    assert "New since the published Nowcast: " in third and "approval polls" in third.split("New since the published Nowcast: ")[1].splitlines()[0] and "Dem win" in third, third[-600:]
    assert "Nothing new" in run()                                                  # and once that is published, nothing is new again
    shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    test_fred_is_read_when_a_release_could_be_out()
    test_the_same_inputs_are_not_run_twice()
    test_every_different_nowcast_is_kept_once()
    test_a_whole_run_stops_when_nothing_is_new()
    print("ok (when a run is made, and what is kept)")
