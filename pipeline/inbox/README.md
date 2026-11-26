# Inbox for the Civiqs page

State-by-state approval comes from Civiqs's tracker, whose site does not allow automatic reads. So every few weeks the
page is saved by hand and left here, and the site does the rest.

1. Open <https://civiqs.com/results/approve_president_trump_2025> in a browser and save the page (Ctrl+S, or Cmd+S on a
   Mac). Any file name will do.
2. On this page, choose **Add file**, then **Upload files**, drop the saved file in, and press **Commit changes**.

The commit starts a run within a minute. It reads the page, checks it, updates `pipeline/state_approval.csv` and the
date of the copy, empties this folder, runs the models again, publishes the site and tells The Margin. Nothing else is
needed. `LAST.md` in this folder says what happened to the last page left here.

A page that fails a check changes nothing: the run is marked failed, GitHub sends its usual e-mail, and `LAST.md` gives
the reason. The checks are listed at the top of `pipeline/civiqs.py`.

Saving the page's source instead (Ctrl+U, then Ctrl+S) gives the figures to two decimals where the page as shown gives
whole percentages. Either is read.
