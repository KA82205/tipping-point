"""Who is running: nominees, running mates, home states, the sitting vice president,
and the vice-presidential approval adjustment. All detected automatically.

Nominees and running mates come from the infobox of Wikipedia's "2028 United States
presidential election" article (nominee1/2, party1/2, home_state1/2, running_mate1/2),
which editors fill in once the conventions pick the tickets. A running mate's home state
is read from their own article's infobox, then from pipeline/candidates.json.

The sitting vice president comes from the "Vice President of the United States" infobox.

VP adjustment (paper, Appendix 6): when the sitting VP is a nominee, state approval of the
president is shifted by (VP net rating - president net rating). VoteHub carries job-approval
polls of the vice president, which is what the paper used for 2000 and 2024; if none fall in
the window, favorability is used instead, as the paper did for 1988.

Possible candidates: PollResults.org's 2028 primary polls say who is being polled and how
they stand. That orders the choices in the site's ticket picker and adds anyone new.

Anything set in config.json "candidates" (non-null) overrides what is detected.
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "TippingPointForecast/1.0 (personal non-commercial election site; github.com/KA82205)"}

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Washington, D.C.": "DC", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def wiki_lead(title, fetch=None):
    """Wikitext of an article's lead section (where the infobox lives)."""
    if fetch:
        return fetch(title)
    qs = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                                 "rvsection": 0, "titles": title, "format": "json", "formatversion": 2,
                                 "redirects": 1})
    req = urllib.request.Request(f"{WIKI_API}?{qs}", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        pages = json.load(r)["query"]["pages"]
    rev = pages[0].get("revisions") if pages else None
    return rev[0]["slots"]["main"]["content"] if rev else ""


def _unlink(s):
    """'[[JD Vance|J. D. Vance]]' -> 'J. D. Vance'; strips refs, templates and markup."""
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", s or "", flags=re.S)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''?|<[^>]+>", "", s)
    return s.strip()


def _link_target(s):
    m = re.search(r"\[\[([^|\]]+)", s or "")
    return m.group(1).strip() if m else _unlink(s)


def infobox_fields(wikitext):
    fields = {}
    for m in re.finditer(r"^\s*\|\s*([a-z_]+\d*)\s*=\s*(.*)$", wikitext or "", flags=re.M):
        fields.setdefault(m.group(1), m.group(2).strip())
    return fields


def state_in(text):
    """First US state named in text, as a two-letter code."""
    text = _unlink(text)
    best = None
    for name, ab in STATE_ABBR.items():
        i = text.find(name)
        if i >= 0 and (best is None or i < best[0]) and not (name == "Washington" and "Washington, D.C." in text[i:i + 16]):
            best = (i, ab)
    return best[1] if best else None


def home_state_of(name, registry, fetch=None):
    """A politician's home state: candidates.json first (curated), then their Wikipedia infobox."""
    for c in registry:
        if c["name"].lower() == name.lower() or name.lower() in [a.lower() for a in c.get("aliases", [])]:
            return c["state"], "candidates.json"
    try:
        f = infobox_fields(wiki_lead(name, fetch))
    except Exception:
        return None, None
    keys = [k for k in f if re.fullmatch(r"(state|office|constituency)\d*|residence", k)]
    for key in keys + (["birth_place"] if "birth_place" in f else []):
        st = state_in(f[key])
        if st:
            return st, f"Wikipedia infobox ({key})"
    return None, None


def detect(cfg, fetch=None):
    """Return the tickets, home states and sitting VP. Never raises; failures leave nulls."""
    registry = json.load(open(os.path.join(HERE, "candidates.json")))["candidates"]
    out = {"dem": {}, "rep": {}, "sitting_vp": None, "source": "Wikipedia", "checked": dt.date.today().isoformat(),
           "notes": []}
    try:
        f = infobox_fields(wiki_lead(cfg["election"].get("wiki_article", "2028 United States presidential election"), fetch))
        for i in ("1", "2", "3"):
            party = f.get("party" + i, "")
            side = "dem" if "Democratic" in party else "rep" if "Republican" in party else None
            nominee = _unlink(f.get("nominee" + i, ""))
            if not side or not nominee or nominee.upper() in ("TBD", "TBA"):
                continue
            hs = state_in(f.get("home_state" + i, ""))
            pres = {"name": nominee, "state": hs, "state_source": "Wikipedia infobox (home_state)" if hs else None}
            if not hs:
                pres["state"], pres["state_source"] = home_state_of(_link_target(f.get("nominee" + i, "")), registry, fetch)
            out[side]["president"] = pres
            rm_raw = f.get("running_mate" + i, "")
            if _unlink(rm_raw):
                st, src = home_state_of(_link_target(rm_raw), registry, fetch)
                out[side]["vp"] = {"name": _unlink(rm_raw), "state": st, "state_source": src}
    except Exception as e:
        out["notes"].append(f"Could not read the election article: {e}")
    try:
        vf = infobox_fields(wiki_lead("Vice President of the United States", fetch))
        out["sitting_vp"] = _unlink(vf.get("incumbent", "")) or None
    except Exception as e:
        out["notes"].append(f"Could not read the sitting vice president: {e}")
    return out


def _norm(n):
    return re.sub(r"[^a-z]", "", (n or "").lower())


def resolve(cfg, detected):
    """Model inputs: config overrides win over detection. Returns (codes, ticket, vp_is_nominee)."""
    c = cfg["candidates"]
    tickets = {"dem": dict(detected.get("dem", {})), "rep": dict(detected.get("rep", {}))}
    for side in ("dem", "rep"):
        for role in ("president", "vp"):
            key = f"{side}_{'president' if role == 'president' else 'vp'}_home"
            if c.get(key):
                tickets[side][role] = {**tickets[side].get(role, {}), "state": c[key], "state_source": "config.json override"}
    codes = {
        "dem_president_home": tickets["dem"].get("president", {}).get("state"),
        "rep_president_home": tickets["rep"].get("president", {}).get("state"),
        "dem_vp_home": tickets["dem"].get("vp", {}).get("state"),
        "rep_vp_home": tickets["rep"].get("vp", {}).get("state"),
        "dem_president_home_lag": c["dem_president_home_lag"],
        "rep_president_home_lag": c["rep_president_home_lag"],
    }
    vp = _norm(detected.get("sitting_vp"))
    vp_is_nominee = bool(vp) and any(_norm(tickets[s].get("president", {}).get("name")) == vp for s in ("dem", "rep"))
    return codes, tickets, vp_is_nominee


def vp_gap(vp_polls, pres_polls, start, end, iso, kind="favorability", min_vp=1):
    """Average (VP net - president net) rating, from approval or favorability polls. Pairs polls
    from the same pollster and end date when possible; otherwise compares the two averages,
    as long as at least min_vp polls of the vice president are in the window."""
    pos, neg = ("approve", "disapprove") if kind == "approval" else ("fav", "unfav")

    def nets(polls):
        rows = {}
        for p in polls or []:
            d = iso(p.get("end_date"))
            try:
                day = dt.date.fromisoformat(d)
            except ValueError:
                continue
            if not (start <= day <= end) or p.get("internal") or p.get("partisan"):
                continue
            up = down = None
            for a in p.get("answers", []):
                ch = str(a.get("choice", "")).lower()
                if ch.startswith(pos) and a.get("pct") is not None:
                    up = float(a["pct"])
                elif ch.startswith(neg) and a.get("pct") is not None:
                    down = float(a["pct"])
            if up is not None and down is not None:
                rows[(str(p.get("pollster", "")).lower(), d)] = up - down
        return rows
    a, b = nets(vp_polls), nets(pres_polls)
    paired = [a[k] - b[k] for k in a if k in b]
    if len(paired) >= 3:
        return sum(paired) / len(paired), f"{len(paired)} polls that asked about both"
    if a and b and len(a) >= min_vp:
        return sum(a.values()) / len(a) - sum(b.values()) / len(b), f"averages of {len(a)} and {len(b)} polls"
    return None, f"no {kind} polls in the window"


NOT_A_PERSON = ("undecided", "other", "someone else", "none", "not sure", "don't know", "dont know", "refused",
                "would not vote", "no one", "unsure")


def primary_standing(raw, start, end, iso):
    """National 2028 primary polling from PollResults.org records.
    Each pollster's latest poll in the window, per party; a candidate's figure is the average
    over the polls that included them. Returns {"D": [{name, pct, polls}], "R": [...]}."""
    latest = {}
    for res in raw or []:
        if str(res.get("state") or "").upper() not in ("US", "USA", "NATIONAL", "") or res.get("internal"):
            continue
        try:
            day = dt.date.fromisoformat(iso(res.get("endDate") or res.get("end_date")))
        except ValueError:
            continue
        if not (start <= day <= end):
            continue
        for q in res.get("questions") or []:
            if str(q.get("stage") or "").lower() != "primary":
                continue
            answers = [a for a in q.get("answers") or [] if a.get("candidateName") and a.get("pct") is not None]
            sub = str(q.get("subpopulation") or "").lower()
            party = "D" if sub.startswith("d") else "R" if sub.startswith("r") else None
            if not party and answers:
                tags = [str(a.get("party") or "").upper()[:1] for a in answers]
                party = max(("D", "R"), key=tags.count) if tags.count("D") != tags.count("R") else None
            if not party or len(answers) < 2:
                continue
            key = (party, str(res.get("pollster") or "").lower())
            if key not in latest or day > latest[key][0] or (day == latest[key][0] and len(answers) > len(latest[key][1])):
                latest[key] = (day, answers)
    out = {}
    for party in ("D", "R"):
        polls = [v[1] for k, v in latest.items() if k[0] == party]
        tally = {}
        for answers in polls:
            for a in answers:
                name = str(a["candidateName"]).strip()
                if any(w in name.lower() for w in NOT_A_PERSON):
                    continue
                t = tally.setdefault(_norm(name), {"name": name, "sum": 0.0, "polls": 0})
                t["sum"] += float(a["pct"]); t["polls"] += 1
        need = 2 if len(polls) >= 3 else 1
        rows = [{"name": t["name"], "pct": round(t["sum"] / t["polls"], 1), "polls": t["polls"]}
                for t in tally.values() if t["polls"] >= need]
        out[party] = sorted(rows, key=lambda r: -r["pct"])
    return out


def merge_registry(registry, standing, fetch=None, min_pct=3.0, max_new=8, exclude=()):
    """Attach primary-poll standing to the candidate list, and add anyone polling at min_pct or
    more who is not on it yet (home state from their Wikipedia infobox; skipped if not found)."""
    out = [dict(c) for c in registry]
    skip = {_norm(x) for x in exclude}
    for party, rows in (standing or {}).items():
        added = 0
        for r in rows:
            key = _norm(r["name"])
            hit = next((c for c in out if c["party"] == party and
                        key in [_norm(c["name"])] + [_norm(a) for a in c.get("aliases", [])]), None)
            if hit:
                hit["primary"], hit["primary_polls"] = r["pct"], r["polls"]
            elif key not in skip and r["pct"] >= min_pct and added < max_new:
                st, _src = home_state_of(r["name"], [], fetch)
                if st:
                    out.append({"name": r["name"], "party": party, "state": st, "primary": r["pct"],
                                "primary_polls": r["polls"], "auto": True})
                    added += 1
    return out
