# Tipping Point

A personal, non-commercial US presidential election forecast site built on the State Presidential Approval/State
Economy Model (Enns, Colner, Kumar & Lagodny, *PS: Political Science & Politics*, 2024,
doi:10.1017/S1049096524000994, CC BY-NC 4.0).

- `docs/` is the website (plain HTML/CSS/JS, no build step). `docs/engine.js` is the model; the
  2028 page reruns it in the browser for the matchup builder.
- `pipeline/` fetches data every day, builds the model inputs and writes `docs/nowcast.js`.
- `.github/workflows/update.yml` runs the pipeline daily and commits the new data.

## How it runs

`.github/workflows/update.yml` runs every morning, on every push, and from the Actions tab
(**Run workflow**). It builds the 2024 data and map shapes, fetches the latest polls and FRED
data, runs the model, commits the new data, and deploys `docs/` to GitHub Pages
(Settings → Pages → Source: GitHub Actions).

The FRED key lives in a repository secret named `FRED_API_KEY`
(Settings → Secrets and variables → Actions), so it never appears in the public code.

## Run locally

```
python pipeline/update.py                       # live data
python pipeline/tests/make_fixtures.py          # fake data for an offline test...
python pipeline/update.py --fixtures pipeline/tests/fixtures   # ...shown with a TEST DATA flag
python pipeline/tests/test_economy.py           # reproduces the paper's Table A-2
python pipeline/tests/test_candidates.py        # nominee detection on real Wikipedia text
```
Build `docs/data.js` and `docs/us-states.js` first (see the workflow), then open
`docs/index.html`. Delete `docs/nowcast.js` after a fixture run.

## Data sources

| Input | Source | Automated |
|---|---|---|
| State economies | Philadelphia Fed State Coincident Indexes via FRED (`{ST}PHCI`) | Yes, daily |
| National Trump approval | VoteHub Polling API and PollResults.org (both CC BY 4.0), merged and averaged here | Yes, daily |
| State approval | See below | Partly |
| 2024 state lean, district offsets | Certified 2024 results (`pipeline/results_2024.json`) | Fixed |
| Nominees, running mates, home states, sitting VP | Wikipedia infobox (`pipeline/candidates.py`), with `pipeline/candidates.json` as fallback; `config.json` overrides | Yes, daily |
| Vice-president adjustment | VoteHub favorability of the sitting VP and the president | Yes, daily |

**State approval.** The paper estimates it with MRP on survey microdata (Gallup, AP-NORC,
Verasight and others, June–July of the election year). No free feed publishes state MRP
approval, so `config.json → approval.state_source` chooses:

- `state_polls` (default): the `vote_swing` estimate, pulled toward any state-level approval
  polls PollResults.org carries (window plus 60 days; the baseline counts as 1,500 respondents).
- `vote_swing`: national average shifted by each state's 2024 Trump margin.
- `csv`: `pipeline/state_approval.csv` with columns `state,approve` (all 50 states + DC).
  Use estimates you are allowed to republish (Civiqs and Morning Consult publish daily or
  monthly state trackers, but neither offers a public API), or your own MRP output.
  The file's state differences are kept and re-centred on the national poll average.

## 2024 scorecard numbers

The paper prints state forecasts only as a chart (Figure A-2). `pipeline/extract_fig_a2.py`
reads the chart's vector paths from the supplement PDF and recovers each state's mean,
90% range and win probability. The recovered values reproduce every call and rating in the
paper, its count of 17 states within 5 points and 10 within 2.5, and Trump's 312 electoral votes.

## Assumptions to confirm with the replication data

These are not published in the paper or appendix and are set in `config.json`:

- **Approval constant (50).** Table A-3's range (−21.85 to 34.68) and the 2024 national
  result are both consistent with about 50.
- **Economic weight δ (0.55) and its grid (0.40–0.70).** 0.55 is the appendix's California
  example; the 2024 forecast used the median of the fitted 2008–2016 values.
- **Economy signed by incumbent party.** Growth is multiplied by −1 under a Republican
  president, as approval is.
- **Coefficient draws are independent.** The paper's CLARIFY draws use the full covariance
  matrix.

The replication archive (Harvard Dataverse, doi:10.7910/DVN/PBGFOF) would settle all four.

## Before the forecast date

Until 1 June 2028 the tracker uses a trailing 30-day poll window and weights the latest
quarter of economic data as if it were the election year's second quarter. From 1 June 2028
the poll window switches to June 1–July 30, matching the paper. For the official 30 July
forecast, nominees, running mates, home states and the VP adjustment fill in automatically
once Wikipedia lists the tickets; supply MRP state approval through the `csv` source.

Gallup, one of the paper's 2024 sources, has stopped publishing presidential approval;
plan the 2028 MRP survey sources early.
