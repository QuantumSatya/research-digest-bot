# How it works

## The weekly cycle

The bot is meant to be started **once a day** by your scheduler (launchd, cron or Task Scheduler).
On every run it:

1. **Checks the journal feeds** in `journals.txt` and keeps new matches in a waiting list. Feeds only
   show the last few days of articles, so checking daily means nothing rolls off before report day.
2. **Decides whether a report is due.** A report is made when today is your `report_weekday`, or the
   first run after a missed report day (for example, if your computer was off on Monday).
3. **If due**, it:
   - runs one arXiv API query per keyword line, for papers submitted since the last report;
   - drops papers it has already reported and papers that fail the topic filter;
   - adds the waiting journal articles;
   - writes `Report_<start>_to_<end>.pdf` and stores the data behind it in `_state/reports/`;
   - remembers everything it reported in `_state/seen.json`;
   - emails you, if email is configured.

`--now` makes a report immediately. `--now --from YYYY-MM-DD` makes a report for a chosen period and
ignores the "already seen" list, which is useful after changing your keywords.

## arXiv search

Each line of `keywords.txt` becomes one query to the
[arXiv API](https://info.arxiv.org/help/api/index.html), sorted by submission date (newest first,
up to `max_results_per_keyword`). The topic filter from `filters.txt` is added to every query:

```text
(all:"time tagging" AND all:"camera") AND (cat:quant-ph OR cat:physics.optics ...)
                                      AND (abs:"photon" OR abs:"light" ...)
```

Papers that match several keywords appear once, with all matching keywords listed.
The bot waits at least 3 seconds between API calls, as arXiv asks. About 100 keywords therefore
take roughly 6 minutes, which is fine in the background.

## Journal feeds

Publishers do not offer keyword search in their feeds, so the bot downloads each feed and matches
locally, with the same syntax as arXiv. Hyphens and dashes (`Hong–Ou–Mandel`) are treated as spaces,
accents are ignored (`Gräfe` = `Grafe`) and simple plurals match (`photon` matches `photons`).
RSS 2.0, RSS 1.0 (RDF) and Atom feeds are supported. Journal PDFs are usually paywalled, so the
report links to the DOI.

When a feed is used for the first time, only its items from the last `first_run_lookback_days` are
reported. This avoids a flood of a whole back issue.

## The PDF

`pdfreport.py` writes the PDF directly, with no external libraries, using the built-in Helvetica
fonts. Characters those fonts lack, such as most Greek letters and math symbols, are written as
words (α → "alpha"). Each article has:

- a clickable title (opens the arXiv abstract or the DOI);
- authors, arXiv ID, category, date and matched keywords;
- the abstract;
- links to the abstract page and the PDF;
- a **tick box**: ticking it turns the title background light green. It is a standard PDF form
  checkbox, so it works in Preview, Acrobat and most viewers. Save the PDF to keep your ticks.

`python3 rebuild_reports.py` re-renders all existing reports with the current `pdfreport.py`
and keeps your ticks.

## Files the bot keeps

| File | Purpose |
|---|---|
| `_state/seen.json` | IDs of reported papers, waiting journal items, date of last report |
| `_state/digest.log` | one line per action, useful for debugging |
| `_state/reports/*.json` | the data behind each report, used for rebuilding |

Deleting `seen.json` makes the bot forget what it has reported. The next report then starts from
`first_run_lookback_days` ago.
