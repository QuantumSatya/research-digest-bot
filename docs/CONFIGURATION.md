# Configuration

On the first run, the bot copies each `*.example.*` file to an editable file. Your editable files are
git-ignored, so `git pull` never overwrites them and you never commit them by accident.

| You edit | Created from | Purpose |
|---|---|---|
| `config.ini` | `config.example.ini` | settings |
| `keywords.txt` | `keywords.example.txt` | what to search for ([syntax](KEYWORDS.md)) |
| `filters.txt` | `filters.example.txt` | topic filter |
| `journals.txt` | `journals.example.txt` | journal feeds |

## config.ini

### [paths]
| Key | Default | Meaning |
|---|---|---|
| `output_dir` | `~/ResearchDigest` | where reports and `_state/` go (`~` is expanded) |
| `keywords_file`, `journals_file`, `filters_file` | `keywords.txt`, … | file names, relative to the bot folder |

The environment variables `DIGEST_CONFIG` (path to a config file) and `DIGEST_OUTPUT_DIR`
override these settings. This is handy for running several digests, for example one per project.

### [schedule]
| Key | Default | Meaning |
|---|---|---|
| `report_weekday` | `monday` | day on which the weekly report is made |
| `first_run_lookback_days` | `7` | how far back the very first report (and each new feed) goes |
| `max_age_days` | `21` | never report arXiv papers older than this, even after a long break |

### [arxiv]
| Key | Default | Meaning |
|---|---|---|
| `max_results_per_keyword` | `300` | newest N results checked per keyword; raise for broad keywords |
| `pause_seconds` | `3.5` | pause between API calls (minimum 3) |
| `user_agent` | | identify yourself, for example with your repo URL |

### [email]
| Key | Meaning |
|---|---|
| `method` | `none`, `mail_app` (macOS Mail, no password needed) or `smtp` |
| `to` | recipient address |
| `smtp_host`, `smtp_port`, `smtp_user`, `smtp_from` | SMTP server details (STARTTLS) |
| `attach_pdf` | attach the report PDF (smtp only) |

The SMTP password is **never** stored in a file. Set it in the environment variable
`DIGEST_SMTP_PASSWORD`, for example in your scheduler job or shell profile. For Gmail and Outlook,
use an *app password*.

## filters.txt

```text
categories:   quant-ph, physics.optics          # arXiv categories (incl. cross-lists)
must_mention: photon, photons, light, optical   # title/abstract must contain one of these
```

Remove a line, or the whole file, to switch that rule off. See the full category list at
<https://arxiv.org/category_taxonomy>. Examples:

| Field | categories |
|---|---|
| Photonics / quantum optics | `quant-ph, physics.optics, physics.ins-det` |
| Astronomy instrumentation | `astro-ph.IM, physics.ins-det` |
| Machine learning | `cs.LG, stat.ML, cs.AI` |
| Condensed matter | `cond-mat.mes-hall, cond-mat.mtrl-sci, cond-mat.supr-con` |
| Quantitative biology | `q-bio.NC, q-bio.QM` |

## journals.txt

One feed per line, as `Journal name | feed URL`. Most publishers list their feeds on a "RSS" page:

| Publisher | Feed URL pattern |
|---|---|
| Nature portfolio | `https://www.nature.com/<journal-code>.rss` (e.g. `nphoton`, `nphys`, `ncomms`) |
| APS (Physical Review) | `https://feeds.aps.org/rss/recent/<code>.xml` (e.g. `prl`, `pra`, `prxquantum`) |
| Optica | `https://opg.optica.org/rss/<code>_feed.xml` (e.g. `optica`, `opex`, `ol`) |
| IOP | `https://iopscience.iop.org/journal/rss/<ISSN>` |
| Wiley | `https://onlinelibrary.wiley.com/feed/<eISSN-without-dash>/most-recent` |
| Science | `https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science` |

Some publishers (for example ACS) block automated readers. The log then shows `HTTP Error 403`,
and you can switch that line off with `#`.
