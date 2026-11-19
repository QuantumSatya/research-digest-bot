# Troubleshooting

Start with the log: `<output_dir>/_state/digest.log`. On macOS, also check
`~/Library/Logs/research-digest-bot.log`.

| Symptom | Cause / fix |
|---|---|
| `Operation not permitted` (macOS) | output folder is in Desktop/Documents/Downloads; see [Scheduling](SCHEDULING.md#macos-launchd) |
| `launchctl list` shows `1` in the middle | the last run failed; read the log |
| `All arXiv searches failed (offline?)` | no internet, or arXiv is down; the bot retries next run |
| `journal feed failed: … 403` | the publisher blocks automated readers; switch that feed off |
| Too many papers | make keywords more specific; add a `filters.txt`; remove broad `au:` lines |
| Off-topic papers | check `Matched:` in the PDF to find the culprit keyword; tighten `filters.txt` |
| Too few papers | broaden keywords; check `--show-queries`; raise `max_results_per_keyword` |
| No email | run `python3 digest.py --test-email`; for SMTP check `DIGEST_SMTP_PASSWORD` |
| Ticks disappear | save the PDF after ticking (Cmd+S / Ctrl+S) |
| `?` or words instead of symbols | the built-in PDF fonts lack that character; see [How it works](HOW_IT_WORKS.md#the-pdf) |
| Want to start over | delete `_state/seen.json` (forgets reported papers), then run `--now` |
