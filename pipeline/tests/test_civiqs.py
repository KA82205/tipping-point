"""The Civiqs reader: finds the data block in the page, and refuses a page that has changed shape."""
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


if __name__ == "__main__":
    test_parse_reads_all_fifty_states()
    test_parse_refuses_a_changed_page()
    print("ok")
