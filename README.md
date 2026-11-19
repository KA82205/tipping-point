# Tipping Point

**Live site: https://ka82205.github.io/tipping-point/** (updated every morning)

A personal, non-commercial forecast of the 2028 US presidential election. It runs two published
models state by state and averages them half and half:

- the **State Presidential Approval/State Economy Model** (Enns, Colner, Kumar & Lagodny,
  *PS: Political Science & Politics*, 2024, doi:10.1017/S1049096524000994, CC BY-NC 4.0), and
- the **Long-Range State-Level Forecast Model** (DeSart, *PS: Political Science & Politics*, 2025,
  doi:10.1017/S1049096524000805).

Until the final forecast the site shows a daily **Nowcast**: what the two models say on the data each
would use today. The site's Method page documents every equation, test and departure from the papers.

## Layout

- `docs/` is the website (plain HTML/CSS/JS, no build step). `docs/engine.js` is the approval and
  fundamentals model and the simulation; `docs/combine.js` adds the long-range model and averages
  the two. The same code runs in the daily update and in the browser.
- `pipeline/` fetches the data every day, builds the model inputs, runs both models and writes
  `docs/nowcast.js` and `docs/history.js`.
- `.github/workflows/update.yml` runs the pipeline every morning and on every push, commits the new
  data and deploys `docs/` to GitHub Pages.

The FRED key lives in a repository secret named `FRED_API_KEY`
(Settings → Secrets and variables → Actions), so it never appears in the public code.

## Dates

Days are US Eastern dates. Each model keeps its paper's own cutoff, judged by the day a poll was
conducted.

| When | What happens |
|---|---|
| Until November 7, 2027 | Long-range model: head-to-head polls conducted in the last 180 days |
| November 7, 2027 | Long-range model fixed on polls conducted in October 2027, as DeSart does (`pipeline/frozen/desart_2028.json`) |
| Until June 1, 2028 | Approval model: approval polls from the last 30 days, latest economic month |
| June 2028 | Approval model switches to polls conducted June 1 to July 30, 2028, once ten pollsters have a poll in that window; economy through June |
| August 6, 2028 | The Nowcast that day is saved as the final forecast (`pipeline/frozen/forecast_2028.json`, `docs/forecast.js`). It never changes, and the daily update stops |

Both models are refitted with the 2024 results, as their authors refit before each forecast. If
either author publishes a revised 2028 version before August 6, 2028, the site switches to it and
says so on the Method page.

## Data sources

| Input | Source | Updates |
|---|---|---|
| State economies | Philadelphia Fed State Coincident Indexes via FRED (`{ST}PHCI`) | Daily |
| National Trump approval | VoteHub and PollResults.org (both CC BY 4.0), merged and averaged | Daily |
| State-by-state approval | A copy of Civiqs's state tracker in `pipeline/state_approval.csv`; only the gaps between states are used, re-centred on the national average | By hand, from a saved copy of the page (see below) |
| Head-to-head polls, primary polls | PollResults.org 2028 feed | Daily |
| Nominees, running mates, home states, sitting VP | Wikipedia infoboxes, with `pipeline/candidates.json` as the curated list | Daily |
| Vice-president adjustment | VoteHub job approval of the sitting VP and the president (favorability as fallback) | Daily |
| 2024 results, district offsets | Certified 2024 results (`pipeline/results_2024.json`) | Fixed |

**State approval.** The paper estimates approval in each state with MRP on survey microdata. No
free feed publishes that, so `config.json → approval.state_source` is set to `csv`: a dated copy of
Civiqs's public state tracker. Civiqs's site turns away automatic reads, so the copy is not
refreshed daily. It is refreshed by hand: open the tracker page in a browser, save it, and run
`python pipeline/civiqs.py "saved page.html"`. A saved copy shows whole percentages. Civiqs licenses
what it publishes under Creative Commons BY-NC-SA 3.0. G. Elliott Morris's Trump Approval Explorer has state MRP estimates, but its page
says the data may not be republished without written permission. Neither is read automatically
unless its owner agrees.

## Run locally

```
python pipeline/tests/test_economy.py           # reproduces the paper's Table A-2
python pipeline/tests/test_candidates.py        # nominee detection and head-to-head counting
node pipeline/tests/test_uncertainty.js         # reproduces the paper's 2024 odds (Harris about 27 in 100)
python pipeline/tests/make_fixtures.py          # fake data for an offline run...
python pipeline/update.py --fixtures pipeline/tests/fixtures   # ...shown with a TEST DATA flag
python pipeline/update.py                       # live data (needs FRED_API_KEY)
python pipeline/backtest_2008_2024.py FOLDER    # the Method page's track record and checks, from the papers' replication files
```

Build `docs/data.js` and `docs/us-states.js` first (see the workflow), then open
`docs/index.html`. Restore `docs/nowcast.js` after a fixture run.

## Checks against the papers

- Refitting each model on its paper's years reproduces the published coefficients exactly; the
  site then adds 2024 (`docs/engine.js`, `docs/combine.js`).
- Rerunning the authors' simulation on their replication data gives Harris 27 in 100 for 2024, as
  published. DeSart's equation with his own independent errors reproduces his published 2024
  simulation (256 Democratic electoral votes on average).
- The paper prints its 2024 state forecasts only as a chart (Figure A-2);
  `pipeline/extract_fig_a2.py` reads the chart's vector paths, and the recovered values match every
  call and rating in the paper and Trump's 312 electoral votes.
- Back-tests of 2008 to 2024, each election forecast from earlier elections only, are on the
  Method page next to the forecasts the authors actually published. `pipeline/backtest_2008_2024.py`
  reproduces them, with a last-election baseline, the tests of other weights and of states moving
  together, and a check of the simulated ranges, from the replication files on Harvard Dataverse
  (doi:10.7910/DVN/PBGFOF and doi:10.7910/DVN/HZGLY9; the data are not stored here).
