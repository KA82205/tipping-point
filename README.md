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
| November 7, 2027 | Long-range model fixed on polls conducted in October 2027, as DeSart does (`pipeline/frozen/desart_2028.json`). When DeSart publishes his own 2028 forecast, his state forecasts replace this run |
| Until June 1, 2028 | Approval model: approval polls from the last 30 days, latest economic month |
| June 2028 | Approval model switches to polls conducted June 1 to July 30, 2028, once ten pollsters have a poll in that window; economy through June |
| August 6, 2028 | The site's own runs are frozen (`pipeline/frozen/forecast_2028.json`, `docs/forecast.js`) and the daily update stops. The forecast is posted with whatever the authors have published by then |

**The final forecast is the authors' own** (set November 20, 2026). It will be the average of the two
forecasts the authors themselves publish for 2028: DeSart's, about a year before the election, and
Enns and colleagues', about 100 days before it. The site's own runs of the two models are for the
Nowcast. They stand in for a published forecast until it is out, or if it never is, and are marked
as stand-ins. Both models are refitted with the 2024 results, as their authors refit before each
forecast. If an author revises the model itself, the site's run switches to the revised version and
says so on the Method page.

## Data sources

| Input | Source | Updates |
|---|---|---|
| State economies | Philadelphia Fed State Coincident Indexes via FRED (`{ST}PHCI`) | Daily |
| National Trump approval | VoteHub and PollResults.org (both CC BY 4.0), merged and averaged; polls of all adults only | Daily |
| State-by-state approval | A copy of Civiqs's state tracker in `pipeline/state_approval.csv`; only the gaps between states are used, re-centred on the national average | By hand, from a saved copy of the page (see below) |
| Head-to-head polls, primary polls | PollResults.org 2028 feed | Daily |
| Nominees, running mates, home states, sitting VP | Wikipedia infoboxes, with `pipeline/candidates.json` as the curated list | Daily |
| Vice-president adjustment | VoteHub job approval of the sitting VP and the president (favorability as fallback) | Daily |
| 2024 results, district offsets | Certified 2024 results (`pipeline/results_2024.json`) | Fixed |

**National approval.** The paper estimates approval among all adults: its model covers ages 18 and
up, is weighted to census population counts, and is built from surveys of the general public. So
only polls of all adults count toward the national average (`config.json →
approval.national_populations`, `["a"]`); polls of registered or likely voters only are left out.
This took effect on November 20, 2026. Until then every poll counted, which read about 3 points
higher for Trump. The daily history restarts that day (`pipeline/history.json`); the earlier days
are kept in `pipeline/history_v4.json`. Until June 2028 the average takes each pollster's latest
poll from the last 30 days, newer polls counting more. On the paper's window (June 1 to July 30,
2028) every poll in the window counts by its sample size alone, as the paper pools every survey
answer from June and July.

**Approval baseline.** The model reads approval minus a baseline that the authors re-choose before
each forecast: the value that best fits the earlier elections. Their file uses 44 for 2024; with
2024 added the same rule gives 43 (`config.json → approval.constant`, and the fits in
`docs/engine.js`). The site used 44 until November 20, 2026.

**State approval.** The paper estimates approval in each state with MRP on survey microdata. No
free feed publishes that, so `config.json → approval.state_source` is set to `csv`: a dated copy of
Civiqs's public state tracker. Civiqs's site turns away automatic reads, so the copy is not
refreshed daily. It is refreshed by hand: open the tracker page in a browser, save it, and run
`python pipeline/civiqs.py "saved page.html"`. A saved copy shows whole percentages. Civiqs licenses
what it publishes under Creative Commons BY-NC-SA 3.0. G. Elliott Morris's Trump Approval Explorer has state MRP estimates, but its page
says the data may not be republished without written permission. Neither is read automatically
unless its owner agrees. To run the Nowcast with no state source at all, set `approval.state_source`
to `vote_swing`: each state then gets the national average shifted by its 2024 vote. The Method
page reports what that changes.

## Run locally

```
python pipeline/tests/test_economy.py           # reproduces the paper's Table A-2
python pipeline/tests/test_candidates.py        # nominee detection and head-to-head counting
node pipeline/tests/test_uncertainty.js         # reproduces the paper's 2024 odds (Harris about 27 in 100)
python pipeline/tests/make_fixtures.py          # fake data for an offline run...
python pipeline/update.py --fixtures pipeline/tests/fixtures   # ...shown with a TEST DATA flag
python pipeline/update.py                       # live data (needs FRED_API_KEY)
python pipeline/backtest_2008_2024.py FOLDER    # the Method page's track record and checks, from the papers' replication files
python pipeline/make_archive.py FOLDER          # the Archive page's 2008 to 2020, state by state (docs/archive.js)
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
  Method page next to the forecasts the authors actually published. The approval model's back-tests
  keep the Southern-states term its authors used through 2020, as their own code does; the script
  first checks that this reproduces the accuracy the paper reports. `pipeline/backtest_2008_2024.py`
  reproduces them, with a last-election baseline, the tests of other weights and of states moving
  together, and a check of the simulated ranges, from the replication files on Harvard Dataverse
  (doi:10.7910/DVN/PBGFOF and doi:10.7910/DVN/HZGLY9; the data are not stored here).
- The Archive page shows every one of those elections state by state, scored on the 50 states.
  For 2020 and 2024 it shows the forecasts the authors published and their average. Enns and
  Lagodny's 2020 state forecasts are printed only as a chart; `pipeline/extract_fig3_2020.py` reads
  its dots and reproduces the article's 290 electoral votes, 54.5% national vote and 59-in-100
  chance (`pipeline/forecast_2020_fig3.json`). DeSart's 2020 forecast is from his replication file
  (`pipeline/forecast_2020_desart.json`). 2008, 2012 and 2016 had no published state forecasts, so
  they are the same back-tests as the track record, labeled as back-tests. State results are
  official counts (`pipeline/results_2008_2020.json`). `pipeline/make_archive.py` writes
  `docs/archive.js`. The Nowcast began in November 2026 and forecast none of these elections.
