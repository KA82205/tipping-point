"""The Civiqs reader: finds the data block in the page, reads a copy saved from a browser, and refuses a page
that has changed shape."""
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


if __name__ == "__main__":
    test_parse_reads_all_fifty_states()
    test_parse_refuses_a_changed_page()
    test_parse_shown_reads_a_saved_copy()
    test_parse_shown_refuses_a_changed_copy()
    test_read_saved_and_write_csv()
    print("ok")
