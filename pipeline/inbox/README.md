# Inbox for the Civiqs page

State-by-state approval comes from Civiqs's tracker, whose site does not allow automatic reads. So every few weeks the
page is saved by hand and left here, and the site does the rest.

1. Open <https://civiqs.com/results/approve_president_trump_2025> in a browser. Press Ctrl+U (Cmd+Option+U on a Mac) to
   see the page's source, then Ctrl+S (Cmd+S) to save it. Any file name will do.
2. On this page, choose **Add file**, then **Upload files**, drop the saved file in, and press **Commit changes**.

The commit starts a run within a minute. It reads the page, checks it, updates `pipeline/state_approval.csv` and the
date of the copy, empties this folder, runs the models again, publishes the site and tells The Margin. Nothing else is
needed. `LAST.md` in this folder says what happened to the last page left here.

A page that fails a check changes nothing: the run is marked failed, GitHub sends its usual e-mail, and `LAST.md` gives
the reason. The checks are listed at the top of `pipeline/civiqs.py`.

Why the source: it carries Civiqs's own figures to two decimals. The page saved as shown (Ctrl+S without Ctrl+U) is read
too, but may give whole percentages only; the run says so when that happens.
