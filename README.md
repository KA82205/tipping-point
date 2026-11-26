# Tipping Point

**Live site: https://ka82205.github.io/tipping-point/** (checked every hour, updated when a poll or a figure is new)

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
  the two. The same code runs in the update and in the browser.
- `pipeline/` fetches the data, builds the model inputs, runs both models and writes
  `docs/nowcast.js` and `docs/history.js`. It also keeps a daily record in `pipeline/log/` and every
  Nowcast that differed from the one before it in `docs/record/` (see below).
  `pipeline/published/` holds the authors' own 2028 forecasts once they are out and have been put in.
- `.github/workflows/update.yml` runs the pipeline every hour and on every push. When an input has
  changed it commits the new data and deploys `docs/` to GitHub Pages; when nothing has, it stops
  before the models are run (see "When it runs").

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
| August 6, 2028 | The site's own runs are frozen (`pipeline/frozen/forecast_2028.json`, `docs/forecast.js`) and the updates stop. The forecast is posted with whatever the authors have published by then |

**The final forecast is the authors' own** (set November 20, 2026). It will be the average of the two
forecasts the authors themselves publish for 2028: DeSart's, about a year before the election, and
Enns and colleagues', about 100 days before it. The site's own runs of the two models are for the
Nowcast. They stand in for a published forecast until it is out, or if it never is, and are marked
as stand-ins. Both models are refitted with the 2024 results, as their authors refit before each
forecast. If an author revises the model itself, the site's run switches to the revised version and
says so on the Method page.

### When the authors publish

1. **DeSart publishes his 2028 forecast (expected November 2027).** His state forecasts replace the
   site's own run of his model as the long-range half and stay fixed. From then on the Nowcast is the
   average of his published forecasts and the site's run of the approval model, so it moves
   only with approval and the economy.
2. **Enns and colleagues publish theirs (expected late July 2028).** Their state forecasts replace the
   site's own run of their model. The forecast is then final: the average of the two published
   forecasts, state by state, fixed until the election. The chance of winning comes from the site's
   simulation around those averaged state forecasts, as on the Archive's 2020 page.
3. **August 6, 2028, whatever has been published.** The site's own runs are frozen and the daily
   update stops. A forecast that is not out yet is stood in for by the site's own run, marked as a
   stand-in, and replaced if it comes out later.
4. **After the election.** The final forecast is scored against the official results and added to
   the Archive and the track record. The daily record (below) also allows a comparison of the
   authors' forecasts with the site's own runs.

**Putting a published forecast in.** The numbers have to be read from the authors' table, data file
or chart by hand. The rest is one command and one commit:

```
python pipeline/put_in.py desart his_table.csv --published 2027-11-14 --url https://...
python pipeline/put_in.py enns their_table.csv --published 2028-07-29 --url https://...
```

The table has one row per state: the state, by name or two letters, and the Democratic share of the
two-party vote (`--values rep` or `--values margin` if it gives the Republican share or the
Democratic lead; `--dem-column` and `--rep-column` if it gives each party's share of all votes). The
command checks that all 50 states are there and that the numbers follow the 2024 results as a state
forecast must, shows how they sit against the site's own run, and writes
`pipeline/published/desart_2028.json` or `enns_2028.json`. Commit that file. From the next run:

- that half of every state's number is the published forecast, held at its published value
  (`docs/combine.js`), and the site says so wherever it names the models;
- the site's own run of the model is still computed and goes on into the daily record, in the
  `site_run` columns;
- the District of Columbia and any state the authors leave out keep the site's own number, and
  Maine's and Nebraska's districts follow their state.

Deleting the file takes the forecast out again. A forecast put in after August 6, 2028 still replaces
the stand-in for it: the next run redoes the posted forecast from the inputs frozen that day
(`pipeline/frozen/nowcast_2028.json`). Tried on the two forecasts the authors published for 2024, this
gives the Archive's 2024 figures (`pipeline/tests/test_uncertainty.js`).

## When it runs

The pipeline is started every hour. Each run reads the poll feeds and builds the models' inputs, then
compares a fingerprint of those inputs, the settings and the code with the fingerprint of the run
that made the published Nowcast (`pipeline/cache/fingerprint.json`). The time a run was made is not
part of the fingerprint.

- **Nothing new:** the run stops there. The models are not run again, nothing is saved and the site
  is not deployed.
- **Something new** (a poll in or out, a new month of state economies, a nominee, a setting, the
  code): both models are run, the data are saved and the site is deployed.
- **The first run of each day** always goes through, because the poll windows move with the day. So
  does a run started by hand or by a push, and every run on a day when something is to be fixed for
  good (the long-range model's polls from November 7, 2027; the final forecast from August 6, 2028).
- **A feed that cannot be read this hour** is not a change. Outside the day's first run the published
  Nowcast stands and the feed is tried again next hour, so a passing fault never moves the numbers.
  The day's first run keeps the rules it always had: the last good copy is used and said to be so.
- **FRED** is read when a release of the state indexes could be out: on working days at 8, 9, 10 and
  11 in the morning, Eastern time, at 2 and 8 in the afternoon and evening of every day, and on the
  day's first run. Between those hours the last good read in `pipeline/cache/` is used.
- **The cutoffs do not move.** The long-range model still takes only polls conducted in October 2027,
  fixed on November 7, 2027; the approval model's last run still takes polls conducted June 1 to
  July 30, 2028; and once the final forecast is posted nothing runs again. Checking more often
  changes how soon a poll inside a window is seen, not which polls count.

A failed scheduled run is tried again the next hour. It is marked as failed at 7 a.m., 1 p.m. and
7 p.m. Eastern only, so a fault that lasts is reported three times a day and a passing one not at all.

**"Every hour" is what is asked of GitHub, not what GitHub promises.** GitHub starts scheduled runs when it has
room. From November 20 to 25, 2026 the two daily starts asked for here began 6 to 12 hours late. A late run loses
nothing but time, since every run is complete in itself, but how often the checks really happen is GitHub's doing.
A run started from outside (the "Run workflow" button, or a call to GitHub's API by a clock somewhere else) starts
at once; "Run workflow" has a box to make the run as the hourly check does.

The Margin reads the Nowcast. If this repository has a secret named `DISPATCH_TOKEN` (a token allowed
to start workflows in the `the-margin` repository), The Margin is told as soon as a new Nowcast is
live; without it The Margin finds the change at its own next hourly check.

## The record

**Every Nowcast, kept.** Each Nowcast that differs from the one before it (a tenth of a point in the
chance, a twentieth of a point in the popular vote, another electoral count, or the same in any one
state) is written to `docs/record/` in a file of its own, named for the time it was made, and never
opened for writing again. `docs/record/index.json` lists them. The files are on the site, at
`record/index.json`.

**The daily record.** For later research, every run that goes through also writes to `pipeline/log/`
(`pipeline/daily_log.py`). Nothing on the site reads it.

- `daily.csv`: one row a day, the headline numbers and the inputs behind them
- `states.csv`: one row a day for every state and district
- `changes.csv`: one row each time something changed, saying what in plain words: polls in or out, a
  new month of state economies, a new copy of the state approval figures, a setting, the code
- `days/YYYY-MM-DD.json`: the whole Nowcast as it stood at the end of that day

The record starts on November 20, 2026. Earlier runs are in the repository's history only.

**The site's own runs stay in the record.** The plain columns are what the site shows; the columns
that start with `site_run` are the site's own runs of the two models. Until an author's 2028 forecast
is put on the site the two are the same. From then on the plain columns hold the authors' forecast
for that model (`approval_model_from` and `long_range_from` say so) and the `site_run` columns keep
the site's own run. After the election that allows a three-way comparison with the result: the
authors' forecasts, the site's own runs on the day before each was published, and the site's own
runs on the last day (decided November 20, 2026).

## Data sources

| Input | Source | Updates |
|---|---|---|
| State economies | Philadelphia Fed State Coincident Indexes via FRED (`{ST}PHCI`) | When a release could be out (see "When it runs") |
| National Trump approval | VoteHub and PollResults.org (both CC BY 4.0), merged and averaged; polls of all adults only | Every hour |
| State-by-state approval | A copy of Civiqs's state tracker in `pipeline/state_approval.csv`; only the gaps between states are used, counted at half (`approval.state_gap_scale`) and re-centred on the national average with each state weighted by its adult population (`pipeline/adult_population.json`) | By hand every few weeks: a saved copy of the page uploaded to `pipeline/inbox` (see below) |
| Head-to-head polls, primary polls | PollResults.org 2028 feed | Every hour |
| Nominees, running mates, home states, sitting VP | Wikipedia infoboxes, with `pipeline/candidates.json` as the curated list | Every hour |
| Vice-president adjustment | VoteHub job approval of the sitting VP and the president (favorability as fallback), compared in surveys that asked about both among the same group of people | Every hour |
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
Civiqs's public state tracker. Civiqs's site turns away automatic reads and offers no data service, so
the copy is not refreshed daily. It is refreshed by hand every few weeks, with nothing but a browser: open
the tracker page, open its source (Ctrl+U), save it (Ctrl+S), and upload the saved file to [`pipeline/inbox`](pipeline/inbox) on GitHub
("Add file", "Upload files", commit). The commit starts a run that reads the page, checks it (all 50
states, the right tracker, a date not earlier than the copy held, no state more than 15 points from
it), rewrites the copy and its date, empties the inbox, runs the models, publishes, and tells The
Margin. A page that fails a check changes nothing and the run is marked failed, with the reason in
`pipeline/inbox/LAST.md`. From a command line the same is `python pipeline/civiqs.py "saved page.html"`.
The page's source (Ctrl+U, then save) carries Civiqs's own
figures to two decimals; a copy of the page as shown gives whole percentages. No other public source
was found to stand in: Morning Consult's state tracker is monthly, pools three months of interviews and
puts its data behind a paid plan, and YouGov publishes no regular state-by-state series. Civiqs licenses
what it publishes under Creative Commons BY-NC-SA 3.0. G. Elliott Morris's Trump Approval Explorer has state MRP estimates, but its page
says the data may not be republished without written permission. Neither is read automatically
unless its owner agrees. To run the Nowcast with no state source at all, set `approval.state_source`
to `vote_swing`: each state then gets the national average shifted by its 2024 vote. The Method
page reports what that changes.

**How far apart the states sit.** The model was fitted on the authors' own state estimates, whose
gaps between states are narrower than Civiqs's: 0.56 times as wide for Trump in 2020 and 0.35 times
for Biden in 2024, 0.48 times with the two together. So each state's gap from the Civiqs average
counts at half (`config.json → approval.state_gap_scale`; 1 would count it in full). Run before the
fact, the authors' model missed the average state by 3.89 points in 2020 and 1.73 in 2024 with
Civiqs's gaps in full, by 3.60 and 1.16 with them at half, and by 3.75 and 1.37 with the authors'
own figures. `python pipeline/state_gap_scale.py <replication folder> <first-term Trump page> <Biden page>`
reproduces this from the authors' replication file and saved copies of the page source of Civiqs's
two finished trackers; neither is kept in this repository.

## Run locally

```
python pipeline/tests/test_economy.py           # reproduces the paper's Table A-2
python pipeline/tests/test_candidates.py        # nominee detection and head-to-head counting
python pipeline/tests/test_runs.py              # when a run is made: the script run three times in a scratch copy
node pipeline/tests/test_uncertainty.js         # reproduces the paper's 2024 odds (Harris about 27 in 100)
python pipeline/tests/make_fixtures.py          # fake data for an offline run...
python pipeline/update.py --fixtures pipeline/tests/fixtures   # ...shown with a TEST DATA flag
python pipeline/update.py                       # live data (needs FRED_API_KEY)
python pipeline/put_in.py desart TABLE.csv --published DATE   # put an author's published forecast on the site
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
