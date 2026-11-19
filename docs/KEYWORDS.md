# Writing good keywords

Each non-comment line of `keywords.txt` is **one search**. A paper is reported if it matches **any** line.

## Syntax

| Pattern | Example | Matches |
|---|---|---|
| phrase | `ghost imaging` | the exact phrase (case-insensitive) |
| AND | `single photon AND SPAD` | papers with both |
| OR | `QKD OR quantum key distribution` | papers with either |
| ANDNOT | `quantum imaging ANDNOT microscopy` | first but not second |
| author | `au:Padgett` | an author with that surname |
| author + first name | `au:Pan AND au:Jian` | avoids people with the same common surname |
| title only | `ti:review AND quantum optics` | "review" in the title |

Write operators in CAPITALS and use **one kind of operator per line**. Mixing `AND` and `OR` on a line
is ambiguous.

## Tips

- **Start specific.** Broad single words (`laser`, `entanglement`) return hundreds of papers a week.
  Combine them with `AND`.
- **Use `filters.txt`.** A filter on categories and required words removes off-topic hits better
  than long keyword lists. One example is nuclear-physics "HBT" papers in a photonics digest.
- **Follow people.** `au:` lines are often the most valuable. Use a first name for common surnames.
- **Check your queries** with `python3 digest.py --show-queries`.
- **Re-run after changes:** `python3 digest.py --now --from <date>` rebuilds a period with your new
  keywords.
- **Prune** keywords that only bring noise. The `Matched:` line in the PDF shows which keyword
  found each paper.

## Example packs

**Quantum optics / photonics** – see `keywords.example.txt`.

**Astronomy instrumentation**
```text
adaptive optics AND extremely large telescope
intensity interferometry
exoplanet AND coronagraph
ti:review AND spectrograph
```

**Machine learning for science**
```text
physics-informed neural network
neural operator AND PDE
foundation model AND materials
ti:survey AND scientific machine learning
```

Share your pack with a pull request. See [CONTRIBUTING.md](../CONTRIBUTING.md).
