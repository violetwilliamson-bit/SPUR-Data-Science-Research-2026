# Tree Census Data Entry Helper

Turns scanned, handwritten tree census datasheets into digital L0 spreadsheets, following the lab's Data Entry and Cleanup Protocol — so the data doesn't have to be typed in by hand.

## Status

All 4 plots for the 2026 census have been transcribed to L0:

| Site | Trees |
|---|---|
| SG-NES1 | 555 |
| SG-NES3 | 421 |
| CA-CAR3 | 297 |
| CC-CVN2 | 534 |

Output workbooks are in `data/work/output/`. Hand-checked (L1) versions go in `data/work/checked/`.

## How it works

1. Render each scanned datasheet page to a high-resolution, deskewed image (`scripts/scan_crops.py`).
2. Transcribe the page by reading the image and writing a raw CSV (one row per tree).
3. `scripts/build_l0.py` merges the raw CSV with the prior census's data and writes it into a copy of the site's template, applying the protocol's entry rules (highlighting blanks, checkmark formulas, an Issue Log for anything unclear).

The transcription step (reading the handwriting) is done by an AI assistant with image reading, not by the scripts alone.

## Repo layout

- `data/protocol/` — the Data Entry and Cleanup Protocol
- `data/scans/` — raw scanned datasheets (not committed; local only)
- `data/template/` — the master spreadsheet template
- `data/last_inventory/` — the prior census, used to carry forward continuing trees
- `data/work/` — transcribed CSVs, built L0 workbooks, and hand-checked versions
- `scripts/` — the build pipeline

## More detail

See [TREE_CENSUS_WORKING_FILE.md](TREE_CENSUS_WORKING_FILE.md) for the full protocol summary, per-site notes, open questions, and progress log.
