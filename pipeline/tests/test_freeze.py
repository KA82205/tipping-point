"""The two years ahead, run in a scratch copy on simulated dates: the academic forecast is fixed when it should be and
stays fixed, an author's own forecast replaces the site's run of that model whenever it arrives, and the live feed of
polls, approval and nominees (docs/live.js) goes on being written to Election Day.

The polls are the real ones saved in pipeline/cache, laid down again one and two years later so that every simulated
date has a recent poll behind it; at each date the feeds hold only what would have been published by then. Nothing
here says anything about what will happen in 2028: it shows what the code does on those days.

    python pipeline/tests/test_freeze.py              the test
    python pipeline/tests/test_freeze.py --export D   also write each stage's Nowcast and live feed to folder D
                                                      (The Margin's own tests of the same days are built on them)
"""
import copy
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(HERE, ".."))
import approval  # noqa: E402

D = dt.date.fromisoformat
LAID = (349, 714)          # days the saved polls are moved on by: November 26, 2026 lands on November 10, 2027 and on November 9, 2028


def _moved(rec, days, tag):
    """One saved poll, the same in everything but its dates."""
    r = copy.deepcopy(rec)
    if "end_date" in r:                                              # VoteHub: ISO dates
        for k in ("created_at", "start_date", "end_date"):
            if r.get(k):
                r[k] = (D(r[k][:10]) + dt.timedelta(days=days)).isoformat()
        r["id"] = f"{r.get('id')}-{tag}"
    else:                                                            # PollResults: 11/23/26, and 11/24/26 10:29
        for k in ("startDate", "endDate", "createdAt"):
            if r.get(k):
                day = D(approval._iso(r[k])) + dt.timedelta(days=days)
                r[k] = f"{day.month}/{day.day}/{day.year % 100:02d}" + (" 12:00" if k == "createdAt" else "")
        r["pollId"] = f"{r.get('pollId')}-{tag}"
    return r


def _day(rec):
    return D(rec["end_date"][:10]) if "end_date" in rec else D(approval._iso(rec["endDate"]))


class World:
    """A scratch copy of the pipeline and the site, and the feeds as they would stand on any day."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        for part in ("pipeline", "docs"):
            shutil.copytree(os.path.join(ROOT, part), os.path.join(self.dir, part),
                            ignore=shutil.ignore_patterns("node_modules", "__pycache__", "log", "record", "frozen", "published"))
        self.feeds = os.path.join(self.dir, "feeds")
        os.makedirs(self.feeds)
        cache = os.path.join(self.dir, "pipeline", "cache")
        self.master = {}
        for name, key in (("votehub.json", "polls"), ("pollresults.json", "results"), ("pollresults_president.json", "results")):
            rows = json.load(open(os.path.join(cache, name)))[key]
            self.master[name] = (key, [_moved(r, days, i) for i, days in enumerate(LAID) for r in rows])
        for name in os.listdir(cache):                               # the state economies: as they stand, read every time
            if name.endswith("PHCI.json"):
                shutil.copy(os.path.join(cache, name), self.feeds)
        for name in ("fingerprint.json",):
            if os.path.exists(os.path.join(cache, name)):
                os.remove(os.path.join(cache, name))
        if os.path.exists(os.path.join(self.dir, "docs", "live.js")):
            os.remove(os.path.join(self.dir, "docs", "live.js"))
        self.extra = []                                              # polls added by a test, on top of the laid-down ones

    def run(self, day, *more):
        """The feeds as of `day`, then update.py on that day, fixing and posting on its days as a live run does."""
        for name, (key, rows) in self.master.items():
            have = [r for r in rows if _day(r) <= D(day)]
            if name == "pollresults_president.json":
                have += [r for r in self.extra if _day(r) <= D(day)]
            json.dump({key: have}, open(os.path.join(self.feeds, name), "w"))
        r = subprocess.run([sys.executable, os.path.join(self.dir, "pipeline", "update.py"), "--fixtures", self.feeds, "--today", day,
                            "--freeze-in-test", *more], cwd=self.dir, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-1500:]
        return r.stdout

    def text(self, name):
        p = os.path.join(self.dir, "docs", name)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None

    def js(self, name):
        t = self.text(name)
        return json.loads(t[t.index("{"):t.rindex("}") + 1])

    def poll(self, day, pollster, dem, rep, d_pct, r_pct, state="US"):
        """A new general-election poll in the PollResults feed, shaped as that feed sends them."""
        d = D(day)
        ans = lambda party, name, pct: {"party": party, "pct": pct, "answer": name, "candidateName": name}
        self.extra.append({"pollId": f"test-{len(self.extra)}", "pollster": pollster, "state": state, "startDate": f"{d.month}/{d.day}/{d.year % 100:02d}",
                           "endDate": f"{d.month}/{d.day}/{d.year % 100:02d}", "createdAt": f"{d.month}/{d.day}/{d.year % 100:02d} 12:00", "url": "https://example.org/poll",
                           "internal": "", "partisan": "", "cycle": "2028", "officeType": "U.S. President", "type": "president",
                           "questions": [{"sampleSize": 1200, "population": "lv", "stage": "general",
                                          "answers": [ans("DEM", dem, d_pct), ans("REP", rep, r_pct), ans("NONE", "Undecided", 100 - d_pct - r_pct)]}]})

    def nominees(self, dem, rep):
        """Wikipedia's election article as it reads once both parties have a nominee."""
        open(os.path.join(self.feeds, "wiki_2028-united-states-presidential-election.txt"), "w").write(
            "{{Infobox election\n| election_name = 2028 United States presidential election\n"
            f"| nominee1 = [[{rep[0]}]]\n| party1 = Republican Party (United States)\n| home_state1 = [[{rep[1]}]]\n"
            f"| nominee2 = [[{dem[0]}]]\n| party2 = Democratic Party (United States)\n| home_state2 = [[{dem[1]}]]\n}}}}\n")

    def publish(self, model, day, lean):
        """An author's own forecast, put in the way it will be: a table of the 50 states handed to pipeline/put_in.py."""
        now = {s["abbr"]: s["demShare"] for s in self.js("nowcast.js")["states"] if len(s["abbr"]) == 2 and s["abbr"] != "DC"}
        table = os.path.join(self.dir, f"{model}_table.csv")
        with open(table, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["State", "Democratic two-party share"])
            for st, v in sorted(now.items()):
                w.writerow([st, round(v + lean, 1)])
        r = subprocess.run([sys.executable, os.path.join(self.dir, "pipeline", "put_in.py"), model, table, "--published", day, "--url", "https://example.org/forecast"],
                           cwd=self.dir, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
        return {st: round(v + lean, 1) for st, v in now.items()}


def _keep(world, stage, out):
    """What The Margin reads at this stage, cut down to the parts it reads."""
    if not out:
        return
    n, live = world.js("nowcast.js"), world.js("live.js")
    for k in ("scenario", "evHistogram", "economy", "vp"):
        n.pop(k, None)
    n["approval"] = {k: v for k, v in n["approval"].items() if k in ("approve", "disapprove", "trend", "window", "pollsters")}
    n["states"] = [{k: s[k] for k in ("abbr", "name", "ev", "demShare") if k in s} for s in n["states"]]
    for h in (n["h2h"], live["h2h"]):
        h.pop("skipped", None)
    if n.get("desart_final"):
        n["desart_final"] = {k: v for k, v in n["desart_final"].items() if k in ("window", "frozen", "as_of")}
    os.makedirs(out, exist_ok=True)
    json.dump({"nowcast": n, "live": live}, open(os.path.join(out, f"{stage}.json"), "w"), separators=(",", ":"))


def test_the_two_years_ahead(export=None):
    w = World()
    lean = {"desart": 1.2, "enns": -0.8}      # how far each author's table sits from the Nowcast of the day, so it can be told from the site's own run

    # 1. November 10, 2027, before DeSart's own forecast: the long-range half is fixed on October 2027's polls, and it
    #    is the site's own run.
    out = w.run("2027-11-10")
    n1, l1 = w.js("nowcast.js"), w.js("live.js")
    assert "Froze the polls model's half" in out and n1["desart_final"]["frozen"] is True and n1["desart_final"]["window"] == ["2027-10-01", "2027-10-31"]
    assert "published" not in n1 and l1["academic"] == {"fixed": False, "since": None, "updated": None, "sources": {"enns": "site run", "desart": "site run"}}
    assert l1["as_of"] == "2027-11-10" and l1["h2h"]["polls"] == n1["h2h"]["polls"] and l1["h2h"]["window"][1] == "2027-11-10"
    assert (l1["approval"]["approve"], l1["approval"]["disapprove"]) == (n1["approval"]["approve"], n1["approval"]["disapprove"]) and l1["approval"]["june"] == []
    _keep(w, "1-before-desart", export)

    # 2. November 20, 2027, DeSart's forecast is out and put in: it replaces the site's run of that half, state for state.
    table_d = w.publish("desart", "2027-11-18", lean["desart"])
    out = w.run("2027-11-20")
    n2 = w.js("nowcast.js")
    assert "Published forecasts in use: desart" in out and n2["model_sources"] == {"enns": "site run", "desart": "authors' forecast"}
    assert n2["published"]["desart"]["states"]["OH"] == table_d["OH"] and w.js("live.js")["academic"]["sources"]["desart"] == "authors' forecast"
    assert abs(n2["models"]["desart"]["demPopular"] - (n1["summary"]["demPopular"] + lean["desart"])) < 0.35, "the long-range half is now the table's national figure"
    assert abs(n2["models"]["enns"]["demPopular"] - n1["models"]["enns"]["demPopular"]) < 1.5, "the other half is still the site's own run"
    _keep(w, "2-after-desart", export)
    before_enns = World.__new__(World)                 # a second copy of the world from here: the one where Enns and colleagues publish late
    before_enns.__dict__.update(copy.deepcopy({k: v for k, v in w.__dict__.items() if k not in ("dir", "feeds")}))
    before_enns.dir = tempfile.mkdtemp()
    shutil.copytree(w.dir, before_enns.dir, dirs_exist_ok=True)
    before_enns.feeds = os.path.join(before_enns.dir, "feeds")

    # 3. August 1, 2028, Enns and colleagues' forecast is out and put in: both halves are now the authors' own.
    w.run("2028-07-30")
    whole = w.js("nowcast.js")["summary"]["demPopular"]
    table_e = w.publish("enns", "2028-07-31", lean["enns"])
    out = w.run("2028-08-01")
    n3, l3 = w.js("nowcast.js"), w.js("live.js")
    assert n3["model_sources"] == {"enns": "authors' forecast", "desart": "authors' forecast"} and n3["published"]["enns"]["states"]["PA"] == table_e["PA"]
    assert abs(n3["models"]["enns"]["demPopular"] - (whole + lean["enns"])) < 0.35, "the approval half is now the table's national figure"
    pa = next(s for s in n3["states"] if s["abbr"] == "PA")
    assert abs(pa["demShare"] - (table_d["PA"] + table_e["PA"]) / 2) < 0.06, "the final number is the plain average of the two authors' forecasts"
    assert len(l3["approval"]["june"]) == 30 and l3["approval"]["june"][0]["d"] == "2028-06-01", "every day of June, for the reading The Margin takes"
    assert l3["h2h"]["window"][1] == "2028-08-01" and n3["h2h"]["window"][1] == "2028-07-30", "the Nowcast's polls stop at the forecast day; the feed's do not"
    _keep(w, "3-after-enns", export)

    # 4. August 6, 2028: the forecast is posted and fixed.
    out = w.run("2028-08-06")
    assert "Published the final 2028 forecast" in out and w.text("forecast.js")
    fixed = {name: w.text(name) for name in ("nowcast.js", "forecast.js")}
    f4 = w.js("forecast.js")
    assert f4["published"] == "2028-08-06" and f4["sources"] == {"enns": "authors' forecast", "desart": "authors' forecast"}
    out = w.run("2028-08-07")
    l4 = w.js("live.js")
    assert "the models are not run again" in out and l4["academic"]["fixed"] is True and l4["academic"]["since"] == "2028-08-06" and l4["as_of"] == "2028-08-07"
    assert {name: w.text(name) for name in fixed} == fixed
    _keep(w, "4-after-the-freeze", export)

    # 5. September 15, 2028: both parties have a nominee and a new national poll of the two is out. The forecast does
    #    not move by a character; the feed has the nominees and the poll.
    top = max({(p["d"], p["r"]) for p in l4["h2h"]["polls"]}, key=lambda k: sum(1 for p in l4["h2h"]["polls"] if (p["d"], p["r"]) == k))
    homes = {c["name"]: c["state"] for c in json.load(open(os.path.join(w.dir, "pipeline", "candidates.json")))["candidates"]}
    names = {"CA": "California", "OH": "Ohio", "FL": "Florida", "NY": "New York", "TX": "Texas", "PA": "Pennsylvania", "IL": "Illinois", "MI": "Michigan", "KY": "Kentucky", "MD": "Maryland", "GA": "Georgia", "AZ": "Arizona", "MN": "Minnesota", "VA": "Virginia", "NJ": "New Jersey", "MA": "Massachusetts", "CO": "Colorado", "AR": "Arkansas", "SC": "South Carolina", "MO": "Missouri"}
    w.nominees((top[0], names.get(homes.get(top[0]), "California")), (top[1], names.get(homes.get(top[1]), "Ohio")))
    w.poll("2028-09-12", "A September Pollster", top[0], top[1], 49, 45)
    out = w.run("2028-09-15")
    l5 = w.js("live.js")
    assert {name: w.text(name) for name in fixed} == fixed, "a new poll after the freeze does not touch the posted forecast"
    assert "The live feed" in out and "written" in out
    new = [p for p in l5["h2h"]["polls"] if p["pollster"] == "A September Pollster"]
    assert len(new) == 1 and new[0]["date"] == "2028-09-12" and new[0]["share"] == round(100 * 49 / 94, 2) and l5["h2h"]["window"] == ["2028-03-19", "2028-09-15"]
    assert (l5["tickets"]["dem"]["president"]["name"], l5["tickets"]["rep"]["president"]["name"]) == top
    assert l5["approval"]["june"] == l4["approval"]["june"] == l3["approval"]["june"], "June's reading does not change once June is over"
    assert "2028-09" in l5["approval"]["window"][1] and l5["academic"]["fixed"] is True
    _keep(w, "5-a-national-poll-in-september", export)
    again = w.run("2028-09-15")
    assert "nothing new" in again and w.js("live.js")["generated_at"] == l5["generated_at"], "the same sources an hour later: the feed is not written again"

    # 6. October 10, 2028: a state poll comes out. State polls are The Margin's to read (from the same feed); here the
    #    forecast stays fixed and the feed stays current.
    w.poll("2028-10-08", "An October Pollster", top[0], top[1], 47, 48, state="PA")
    w.run("2028-10-10")
    l6 = w.js("live.js")
    assert {name: w.text(name) for name in fixed} == fixed and l6["as_of"] == "2028-10-10" and not [p for p in l6["h2h"]["polls"] if p["pollster"] == "An October Pollster"]
    _keep(w, "6-a-state-poll-in-october", export)

    # 8. Election Day: still fixed, still fed.
    w.run("2028-11-07")
    l8 = w.js("live.js")
    assert {name: w.text(name) for name in fixed} == fixed and l8["as_of"] == "2028-11-07" and l8["h2h"]["window"][1] == "2028-11-07" and l8["h2h"]["polls"]
    _keep(w, "8-election-day", export)

    # 7. The other world: Enns and colleagues publish after the freeze. Until they do the site's own run stands in; when
    #    their table is put in, the posted forecast is redone from the inputs kept on the freeze day, once.
    b = before_enns
    b.run("2028-07-30")
    b.run("2028-08-06")
    f_b = b.js("forecast.js")
    assert f_b["sources"] == {"enns": "site run", "desart": "authors' forecast"}
    stand_in = {name: b.text(name) for name in ("nowcast.js", "forecast.js")}
    b.run("2028-08-15")
    assert {name: b.text(name) for name in stand_in} == stand_in and b.js("live.js")["academic"]["sources"]["enns"] == "site run"
    _keep(b, "7a-frozen-with-a-stand-in", export)
    table_late = b.publish("enns", "2028-08-19", lean["enns"])
    out = b.run("2028-08-20")
    f_late, n_late, l_late = b.js("forecast.js"), b.js("nowcast.js"), b.js("live.js")
    assert "The posted 2028 forecast was redone" in out and f_late["sources"] == {"enns": "authors' forecast", "desart": "authors' forecast"}
    assert f_late["published"] == "2028-08-06" and f_late["updated"] == "2028-08-20" and n_late["published"]["enns"]["states"]["WI"] == table_late["WI"]
    assert abs(f_late["models"]["enns"]["demPopular"] - (f_b["summary"]["demPopular"] + lean["enns"])) < 0.35 and f_late["models"]["enns"] != f_b["models"]["enns"]
    assert f_late["models"]["desart"] == f_b["models"]["desart"], "the half that was already the author's own is untouched"
    assert l_late["academic"] == {"fixed": True, "since": "2028-08-06", "updated": "2028-08-20", "sources": {"enns": "authors' forecast", "desart": "authors' forecast"}}
    _keep(b, "7b-enns-arrives-late", export)
    redone = {name: b.text(name) for name in ("nowcast.js", "forecast.js")}
    out = b.run("2028-08-21")
    assert "redone" not in out and {name: b.text(name) for name in redone} == redone, "redone once, then fixed again"

    shutil.rmtree(w.dir, ignore_errors=True)
    shutil.rmtree(b.dir, ignore_errors=True)


if __name__ == "__main__":
    test_the_two_years_ahead(sys.argv[sys.argv.index("--export") + 1] if "--export" in sys.argv else None)
    print("ok (2027 to Election Day 2028: the forecast is fixed when it should be, an author's forecast replaces the site's run early or late, the live feed never stops)")
