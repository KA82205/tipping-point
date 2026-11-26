# Inbox for the Civiqs figures

State-by-state approval comes from Civiqs's tracker, whose site does not allow automatic reads. So every few weeks the
figures are brought over by hand. It takes about two minutes and nothing but a browser.

1. Open <https://civiqs.com/results/approve_president_trump_2025>. Press Ctrl+U (Cmd+Option+U on a Mac) to see the
   page's source, then Ctrl+S (Cmd+S) to save it anywhere on your computer.
2. Open the converter, <https://ka82205.github.io/tipping-point/civiqs.html>, and give it the saved file. It reads the
   file inside your browser, sends it nowhere, and shows the fifty figures and their date.
3. Press **Open GitHub with the file filled in**, then **Commit changes** on GitHub.

The commit starts a run within a minute. It checks the figures, updates `pipeline/state_approval.csv` and the date of
the copy, empties this folder, runs the models again, publishes the site and tells The Margin. Nothing else is needed.
`LAST.md` in this folder says what happened to the last file left here.

## Do not upload the saved page itself

Only the data file is taken in: `state,approve,as_of,source`, one line a state. A saved page is removed unread.

A saved page carries everything Civiqs's site sends a browser: its scripts, its settings, and the keys of the outside
services its own site uses (maps, analytics, error reports). They are Civiqs's, they are public in the sense that every
visitor's browser receives them, and they still do not belong here: GitHub's scanner reports them as leaked secrets, and
a file once committed stays in this repository's history after it is deleted. The converter exists so that only fifty
figures and a date ever leave your computer.

## If something is wrong

A file that fails a check changes nothing: the run is marked failed, GitHub sends its usual e-mail, and `LAST.md` gives
the reason. The checks are listed at the top of `pipeline/civiqs.py`: the file's exact form, all fifty states, one date
that is not earlier than the copy held and not in the future, and no state more than 15 points from the copy held.
