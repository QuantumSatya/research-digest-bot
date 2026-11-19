# Contributing

Thanks for helping! Small, focused pull requests are easiest to review.

## Ground rules

- **Standard library only.** Users should never need `pip install`. Optional extras are fine if the
  bot still works without them.
- **Python 3.8+** and macOS, Linux and Windows.
- **Be polite to data sources.** Keep the ≥3 s arXiv pause and don't add aggressive scraping.
- **No personal data** in commits. `config.ini`, `keywords.txt`, `journals.txt` and `filters.txt` are
  git-ignored for that reason.

## Development

```bash
python3 -m unittest discover -s tests -v     # offline tests, no network needed
python3 digest.py --show-queries             # check keyword parsing
DIGEST_OUTPUT_DIR=/tmp/digest-test python3 digest.py --now   # real run into a scratch folder
```

Please add or extend a test in `tests/` for new behaviour.

## Good first contributions

- **Keyword / journal packs** for other fields (add them to `docs/KEYWORDS.md` or a `packs/` folder).
- More journal feed URLs in `journals.example.txt`.
- Other sources: bioRxiv / medRxiv, ChemRxiv, Semantic Scholar, OpenAlex citation alerts.
- Output formats: HTML or Markdown digest, RSS of your own digest, Zotero/BibTeX export.
- Better PDF typography, for example embedding a font with Greek and math symbols.

## Reporting bugs

Open an issue with your OS, Python version, the relevant lines of `_state/digest.log` and, if
possible, the keyword line involved. Remove any personal information first.
