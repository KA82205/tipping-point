"""Watch for a new publication by the authors of the two models.

The Nowcast runs its own reading of two published methods. When the authors publish their own forecast for 2028, theirs
replaces the site's (pipeline/put_in.py and the readme say how). This script looks, once a day, for such a publication, so
that nobody has to remember to.

Where it looks: Crossref, the open register of scholarly publications (api.crossref.org), for works that name one of the
authors and have 2028 in the title. Both methods have been published in PS: Political Science & Politics before each
election, and anything with a DOI is in Crossref within days.

What it does when it finds one: it writes the title, the authors, the date and the link to docs/watch.json and says so in
the run. It does not put the forecast in. A published forecast arrives as a table inside an article, in a layout that is
not known in advance; reading it wrongly would silently replace a model with a mistake. Until a person has put the table in
(one command), the site carries on with its own reading of the method and says a publication is waiting.

    python pipeline/watch.py            look now and print what was found
"""
import datetime as dt, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "watch.json")
AGENT = {"User-Agent": "Mozilla/5.0 (compatible; tipping-point/1.0; +https://github.com/KA82205/tipping-point)"}
AUTHORS = {"the long-range model": ("DeSart",), "the approval-and-economy model": ("Enns", "Lagodny")}
YEAR = "2028"


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def found(read=get):
    """Works in Crossref by one of the authors with the year in the title: [{model, title, authors, published, url}]."""
    out = {}
    for model, names in AUTHORS.items():
        for name in names:
            q = urllib.parse.urlencode({"query.author": name, "query.title": f"{YEAR} presidential election forecast", "rows": 20, "select": "DOI,title,author,issued,container-title"})
            for w in (read("https://api.crossref.org/works?" + q).get("message") or {}).get("items") or []:
                title = " ".join(w.get("title") or []); people = [a.get("family", "") for a in w.get("author") or []]
                if YEAR not in title or not any(n.lower() == p.lower() for n in names for p in people):
                    continue
                if not any(k in title.lower() for k in ("forecast", "election", "president")):
                    continue
                parts = ((w.get("issued") or {}).get("date-parts") or [[None]])[0]
                out[w["DOI"]] = {"model": model, "title": title, "authors": people, "published": "-".join(f"{int(x):02d}" for x in parts if x) or None,
                                 "where": " ".join(w.get("container-title") or []), "url": "https://doi.org/" + w["DOI"]}
    return sorted(out.values(), key=lambda x: (x["published"] or "", x["title"]))


def refresh(today=None, path=OUT, read=get):
    """Look once a day. Returns (state, words): 'same', 'new', 'early' (already looked today) or 'unreachable'."""
    today = today or dt.date.today().isoformat()
    old = json.load(open(path)) if os.path.exists(path) else {}
    if old.get("looked") == today:
        return "early", "the authors' publications were already looked for today"
    try:
        works = found(read)
    except Exception as err:                            # noqa: BLE001  the last list stays
        return "unreachable", f"Crossref was not reached ({type(err).__name__}: {str(err)[:80]}); the last list stays"
    known = {w["url"] for w in old.get("found") or []}; new = [w for w in works if w["url"] not in known]
    json.dump({"looked": today, "what": "publications by the models' authors with 2028 in the title, from Crossref", "found": works,
               "note": "A forecast published by the authors replaces the site's own reading of their method once it has been put in (pipeline/put_in.py)."}, open(path, "w"), indent=1)
    if new:
        return "new", "; ".join(f"{w['title']} ({', '.join(w['authors'])}; {w['url']})" for w in new)
    return "same", f"{len(works)} publication(s) by the authors on {YEAR} known; none new"


if __name__ == "__main__":
    state, words = refresh()
    if state == "new":
        print("::warning::A new publication by the authors of one of the models: " + words + ". Until its forecast is put in (pipeline/put_in.py), the site runs its own reading of the method.")
    else:
        print("Authors' publications: " + words)
