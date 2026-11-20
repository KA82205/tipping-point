# The daily record

Kept for later research. Nothing on the site reads these files. The daily run writes them
(`pipeline/daily_log.py`); do not edit them by hand.

- `daily.csv`: one row a day. The Democrat's chance, the popular vote, the electoral count, each model on its
  own, and the inputs behind them. Opens in Excel.
- `states.csv`: one row a day for every state and district.
- `changes.csv`: one row each time something changed, saying what: polls in or out, a new month of state
  economies, a new copy of the state approval figures, a setting, the code.
- `days/`: the whole Nowcast as it stood at the end of each day.

Days are US Eastern dates. The record starts on November 20, 2026.

Two sets of numbers sit side by side. The plain columns are what the site shows. The columns that start with
`site_run` are the site's own runs of the two models. Until an author's own 2028 forecast is put on the site the
two sets are the same. From then on the plain columns hold the authors' forecast for that model (the columns
`approval_model_from` and `long_range_from` say so) and the `site_run` columns keep the site's own run. After the
election that allows a three-way comparison with the result: the authors' forecasts, the site's own runs on the
day before each was published, and the site's own runs on the last day.
