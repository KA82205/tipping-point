"""The Civiqs reader: finds the data block in a page, takes in the data file the converter makes and nothing else, and
refuses figures that fail a check."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import civiqs  # noqa: E402


def _page(states, end="2026-11-10"):
    ctx = {"basename": "/", "state": {"loaderData": {"root": {}, civiqs.ROUTE: {
        "end_date": end, "crosstabs": {"map": states}}}}}
    return '<html><script>window.__remixContext = ' + json.dumps(ctx) + ';</script><p>}{ not json</p></html>'


def _states():
    fx = json.load(open(os.path.join(HERE, "fixtures", "civiqs_state_approval.json")))["states"]
    name = {v: k for k, v in civiqs.STATES.items()}
    return {name[a]: {"demographic": name[a], "Approve": v["approve"] / 100, "Disapprove": v["disapprove"] / 100}
            for a, v in fx.items()}


def test_parse_reads_all_fifty_states():
    out = civiqs.parse(_page(_states()))
    assert out["as_of"] == "2026-11-10" and len(out["states"]) == 50
    assert out["states"]["GA"] == {"approve": 33.11, "disapprove": 59.21}


def test_parse_refuses_a_changed_page():
    for bad in ("<html>no data here</html>", _page({k: v for k, v in _states().items() if k != "Ohio"}),
                _page({**_states(), "Ohio": {"Approve": 33.0, "Disapprove": 0.5}})):
        try:
            civiqs.parse(bad)
        except ValueError:
            continue
        raise AssertionError("a changed page was accepted")


def _saved(rows, day="November 18, 2026"):
    """A cut-down copy of the page as a browser saves it: no data block, whole percentages on show."""
    def group(kind, name, a, d):
        return (f'<a href="#"><span class="font-bold capitalize">{kind}:</span><span> {name}</span></a>'
                f'<div><span>Approve</span><span class="float-right">{a}%</span></div>'
                f'<div><span>Disapprove</span><span class="float-right">{d}%</span></div>'
                f'<div><span>Neither approve nor disapprove</span><span class="float-right">{100 - a - d}%</span></div>')
    return ('<html><script></script><p>January 20, 2025\u2014' + day + ': 143,723 Responses</p>'
            + group("age", "18-34", 30, 62) + "".join(group("state", n, a, d) for n, (a, d) in rows.items())
            + '<div data-testid="crosstabs"><h2>All Respondents</h2><div><span class="font-light">' + day
            + '</span><span>100% of population</span></div></div></html>')


def _rows():
    return {name: (25 + i % 30, 68 - i % 30) for i, name in enumerate(civiqs.STATES)}


def test_parse_shown_reads_a_saved_copy():
    out = civiqs.parse_shown(_saved(_rows()))
    assert out["as_of"] == "2026-11-18" and len(out["states"]) == 50 and out["rounded"] is True
    assert out["states"]["AL"] == {"approve": 25.0, "disapprove": 68.0}      # the first state, not the age group before it
    assert out["states"]["WY"] == {"approve": 25.0 + 49 % 30, "disapprove": 68.0 - 49 % 30}


def test_parse_shown_refuses_a_changed_copy():
    rows = _rows()
    for bad in ("<html>nothing</html>", _saved({k: v for k, v in rows.items() if k != "Ohio"}),
                _saved({**rows, "Ohio": (3, 96)}), _saved(rows, day="sometime")):
        try:
            civiqs.parse_shown(bad)
        except ValueError:
            continue
        raise AssertionError("a changed saved copy was accepted")


def test_read_saved_and_write_csv(tmp_path=None):
    import csv
    import tempfile
    d = str(tmp_path) if tmp_path else tempfile.mkdtemp()
    block, shown = os.path.join(d, "source.html"), os.path.join(d, "saved.html")
    open(block, "w", encoding="utf-8").write(_page(_states()))
    open(shown, "w", encoding="utf-8").write(_saved(_rows()))
    assert "rounded" not in civiqs.read_saved(block) and civiqs.read_saved(block)["states"]["GA"]["approve"] == 33.11
    data = civiqs.read_saved(shown)
    assert data["rounded"] is True
    out = os.path.join(d, "state_approval.csv")
    civiqs.write_csv(data, out)
    rows = {r["state"]: float(r["approve"]) for r in csv.DictReader(open(out))}
    fifty = [v for k, v in rows.items() if k != "DC"]
    assert len(rows) == 51 and abs(rows["DC"] - (sum(fifty) / 50 - 24)) < 0.006   # DC: 24 below the average state


def _folder():
    """A stand-in for pipeline/: the copy held (the fixture's figures, dated November 10), its date, and an empty inbox."""
    import tempfile
    d = tempfile.mkdtemp()
    fx = json.load(open(os.path.join(HERE, "fixtures", "civiqs_state_approval.json")))
    civiqs.write_csv({"states": fx["states"]}, os.path.join(d, "state_approval.csv"))
    json.dump({"approval": {"state_source": "csv", "state_csv_as_of": "2026-11-10"}}, open(os.path.join(d, "config.json"), "w"), indent=2)
    os.mkdir(os.path.join(d, "inbox"))
    open(os.path.join(d, "inbox", "README.md"), "w").write("how to use the inbox")
    return d


def _moved(by=1.0, only=None):
    out = _states()
    for i, (name, row) in enumerate(out.items()):
        if only is None or name == only:
            row["Approve"] = round(row["Approve"] + (by if i % 2 else -by) / 100, 4)
    return out


def _clean(states=None, end="2026-12-11", head="state,approve,as_of,source", source=None, fix=None):
    """The data file as the converter page writes it (docs/civiqs.html, toCsv)."""
    data = civiqs.parse(_page(states or _moved(1.0), end=end))
    rows = [[st, f"{v['approve']:.2f}", data["as_of"], source or civiqs.URL] for st, v in sorted(data["states"].items())]
    if fix:
        rows = fix(rows)
    return head + "\n" + "\n".join(",".join(r) for r in rows) + "\n"


def test_the_data_file_left_in_the_inbox_is_taken_in():
    import csv
    import datetime
    day = datetime.date(2026, 12, 12)
    d = _folder()
    assert civiqs.take_in(d, day) == ("empty", "")
    before = open(os.path.join(d, "state_approval.csv")).read()
    # newer figures: read, the copy and its date rewritten, the inbox emptied, what happened written down
    open(os.path.join(d, "inbox", "civiqs-2026-12-11.csv"), "w", newline="").write(_clean())
    state, words = civiqs.take_in(d, day)
    assert state == "taken" and "through 2026-12-11" in words and "two decimals" in words and "moved 1.0 points" in words
    rows = {r["state"]: float(r["approve"]) for r in csv.DictReader(open(os.path.join(d, "state_approval.csv")))}
    want = civiqs.parse(_page(_moved(1.0)))["states"]
    assert len(rows) == 51 and open(os.path.join(d, "state_approval.csv")).read() != before
    assert all(rows[st] == v["approve"] for st, v in want.items())                 # to the figure, all fifty
    assert json.load(open(os.path.join(d, "config.json")))["approval"]["state_csv_as_of"] == "2026-12-11"
    assert sorted(os.listdir(os.path.join(d, "inbox"))) == ["LAST.md", "README.md"] and "taken in" in open(os.path.join(d, "inbox", "LAST.md")).read()
    assert civiqs.take_in(d, day) == ("empty", "")
    # the same figures again (a second upload of the same day) are taken in and change nothing; Windows line ends are fine
    kept = open(os.path.join(d, "state_approval.csv")).read()
    open(os.path.join(d, "inbox", "again.CSV"), "w", newline="").write(_clean().replace("\n", "\r\n"))
    state, words = civiqs.take_in(d, day)
    assert state == "taken" and "moved 0.0 points" in words and open(os.path.join(d, "state_approval.csv")).read() == kept


def test_a_saved_page_is_removed_unread():
    """The page itself is never taken in: it is removed, the copy stays, and the words say where the data file is made."""
    import datetime
    day = datetime.date(2026, 12, 12)
    page = "<!-- saved from url=(0058)https://civiqs.com/results/approve_president_trump_2025 -->" + _page(_moved(1.0), end="2026-12-11")
    d = _folder()
    before = open(os.path.join(d, "state_approval.csv")).read()
    open(os.path.join(d, "inbox", "Donald Trump Job Approval.html"), "w", encoding="utf-8").write(page)
    os.mkdir(os.path.join(d, "inbox", "Donald Trump Job Approval_files"))          # what a browser's "complete" save leaves beside the page
    open(os.path.join(d, "inbox", "Donald Trump Job Approval_files", "app.js"), "w").write("x")
    state, words = civiqs.take_in(d, day)
    assert state == "refused" and "removed without being read" in words and civiqs.CONVERTER in words and "history" in words
    assert open(os.path.join(d, "state_approval.csv")).read() == before
    assert json.load(open(os.path.join(d, "config.json")))["approval"]["state_csv_as_of"] == "2026-11-10"
    assert sorted(os.listdir(os.path.join(d, "inbox"))) == ["LAST.md", "README.md"] and "refused" in open(os.path.join(d, "inbox", "LAST.md")).read()
    # a page renamed .csv is not read as figures either
    d = _folder()
    open(os.path.join(d, "inbox", "page.csv"), "w", encoding="utf-8").write(page)
    state, words = civiqs.take_in(d, day)
    assert state == "refused" and open(os.path.join(d, "state_approval.csv")).read() == before
    # the data file beside a page: the figures are used, the page is removed unread, and the words say so
    d = _folder()
    open(os.path.join(d, "inbox", "page.html"), "w", encoding="utf-8").write(page)
    open(os.path.join(d, "inbox", "civiqs-2026-12-11.csv"), "w", newline="").write(_clean())
    state, words = civiqs.take_in(d, day)
    assert state == "taken" and "removed without being read" in words and sorted(os.listdir(os.path.join(d, "inbox"))) == ["LAST.md", "README.md"]


def test_a_data_file_that_fails_a_check_changes_nothing():
    import datetime
    day = datetime.date(2026, 12, 12)
    drop = lambda rows: [r for r in rows if r[0] != "OH"]
    cases = {
        "older than the copy held": _clean(_states(), end="2026-11-01"),
        "dated in the future": _clean(_states(), end="2027-03-01"),
        "another Civiqs question": _clean(source="https://civiqs.com/results/favorable_donald_trump"),
        "figures far from the copy held": _clean(_moved(9.0)),
        "one state far out": _clean(_moved(20.0, only="Ohio")),
        "a state missing": _clean(fix=drop),
        "a state twice": _clean(fix=lambda rows: rows + [rows[0]]),
        "a place that is not a state": _clean(fix=lambda rows: drop(rows) + [["DC", "20.00", rows[0][2], rows[0][3]]]),
        "a figure that is not a number": _clean(fix=lambda rows: [[r[0], "=1+1" if r[0] == "OH" else r[1], r[2], r[3]] for r in rows]),
        "three decimals": _clean(fix=lambda rows: [[r[0], "40.123" if r[0] == "OH" else r[1], r[2], r[3]] for r in rows]),
        "a share of 1, not a percentage": _clean(fix=lambda rows: [[r[0], "0.41" if r[0] == "OH" else r[1], r[2], r[3]] for r in rows]),
        "two dates": _clean(fix=lambda rows: [[r[0], r[1], "2026-12-10" if r[0] == "OH" else r[2], r[3]] for r in rows]),
        "a fifth column": _clean(fix=lambda rows: [r + ["x"] for r in rows]),
        "another heading": _clean(head="state,approve"),
        "markup in a cell": _clean(fix=lambda rows: [[r[0], r[1], r[2], r[3] + "<script>" if r[0] == "OH" else r[3]] for r in rows]),
        "letters that are not plain": _clean().replace("OH,", "ÖH,"),
        "far too large": _clean() + "AL,40.00,2026-12-11," + civiqs.URL + "\n" * 9000,
        "empty": "",
    }
    for what, text in cases.items():
        d = _folder()
        before = open(os.path.join(d, "state_approval.csv")).read()
        open(os.path.join(d, "inbox", "civiqs.csv"), "w", encoding="utf-8", newline="").write(text)
        state, words = civiqs.take_in(d, day)
        assert state == "refused" and "stays as it was" in words, what
        assert open(os.path.join(d, "state_approval.csv")).read() == before, what
        assert json.load(open(os.path.join(d, "config.json")))["approval"]["state_csv_as_of"] == "2026-11-10", what
        assert sorted(os.listdir(os.path.join(d, "inbox"))) == ["LAST.md", "README.md"] and "refused" in open(os.path.join(d, "inbox", "LAST.md")).read(), what
    # two data files left at once, one of them bad: the good one is used
    d = _folder()
    open(os.path.join(d, "inbox", "a.csv"), "w").write("state,approve\n")
    open(os.path.join(d, "inbox", "b.csv"), "w", newline="").write(_clean(_moved(0.5)))
    assert civiqs.take_in(d, day)[0] == "taken"


if __name__ == "__main__":
    test_parse_reads_all_fifty_states()
    test_parse_refuses_a_changed_page()
    test_parse_shown_reads_a_saved_copy()
    test_parse_shown_refuses_a_changed_copy()
    test_read_saved_and_write_csv()
    test_the_data_file_left_in_the_inbox_is_taken_in()
    test_a_saved_page_is_removed_unread()
    test_a_data_file_that_fails_a_check_changes_nothing()
    print("ok")
