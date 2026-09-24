# Tree Census Data Entry Helper: Working File

## Goal

Build a data entry helper that takes scanned, handwritten tree census data sheets and turns them into rows in a spreadsheet.

## Pipeline (draft)

1. **Scan intake**: collect scanned sheets (PDF/JPG/PNG) in one folder.
2. **Preprocess**: deskew, crop, boost contrast, split multi-page PDFs into images.
3. **Layout detection**: find the table and its rows and columns on each sheet.
4. **Recognition (OCR/HTR)**: read the handwriting in each cell.
5. **Validate and review**: flag low-confidence or invalid values for a human to check and correct.
6. **Export**: write the cleaned rows to a spreadsheet (CSV/XLSX or Google Sheets).

The human review step matters most. Handwriting recognition will make mistakes, so the goal is to reduce typing, not to eliminate checking.

## Open questions

- [ ] What columns are on the sheets (species, DBH, height, condition, location, date, surveyor, ...)?
- [ ] Are all sheets the same template, or do formats vary?
- [ ] Is the handwriting mostly numbers and short codes, or free text?
- [ ] Roughly how many sheets, and what is the scan quality (resolution, skew, shadows)?
- [ ] Which recognition approach to try first: Tesseract, a cloud OCR service, or a vision-language model?
- [ ] Where should the output go: CSV/XLSX file or Google Sheets?

## Data fields

| Field | Type | Valid values / rules | Notes |
|-------|------|----------------------|-------|
| _tbd_ | | | |

## Validation rules (ideas)

- Numeric fields (e.g. diameter) must fall within a plausible range.
- Categorical fields (e.g. species code, condition) must match a known list.
- Flag any cell the recognizer is unsure about.

## Inputs (in `data/`)

- `data/protocol/Data Entry Protocol.pdf` — the Data Entry and Cleanup Protocol (L0/L1/L2 definitions, naming convention, entry rules).
- `data/scans/` — scanned datasheet PDFs, one per site: SG-NES1 (20 pages), SG-NES3 (14 pages), CA-CAR3 (11 pages), CC-CVN2 (19 pages). Last page(s) of each = new trees tagged that census.
- `data/template/Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx` — the master template (`Data Entry`, `Changelog`, `Issue Log` sheets).
- `data/last_inventory/` — 2021 L2 files per site, used to seed `Site_Name`, `Tag_Number`, `Previous_Tag_Number`, `Tag_Date`, `Sp_Code` for continuing trees, per protocol.
- `data/work/` — scratch area: `images/` (rendered page PNGs), `csv/` (transcribed raw rows per page), `output/` (built L0 workbooks).

## Protocol summary (L0 scope only, for now)

- Enter data exactly as written. Blank field → leave blank + highlight cell. Dash on sheet → literal dash. Checkmark → `=UNICHAR(10004)`. Unclear/wrong entry → still enter it, highlight, and log in Issue Log with the tag number.
- `*_Date` columns (Height_Date, DBH_Date, CII_Date, Crown_Class_Date, Condition_Obs_Date) = date at top of that datasheet page, unless a different date is noted next to an observation.
- Family/Genus/Species/Subspecies/Authority are filled later via a species-code lookup, not typed per row — leave blank at L0.
- New trees (last page(s) of each site's scan set): `Tag_Date` = date tagged that survey (per your instruction), appended after the last existing tag number, increasing by tag number.
- File name format: `<plot_id>_inventory_data_<collection_year>_L0_<YY-MM-DD created>`.

## Pipeline (built)

1. Render a scan page to a high-res PNG (`pdftoppm`).
2. Transcribe the page by reading the image (Claude vision) into a raw CSV (one row per tree, datasheet column order) — `data/work/csv/`. Anything unclear goes in the `unclear_flags` column instead of being guessed.
3. `scripts/build_l0.py` merges the raw CSV with the prior-inventory lookup and writes rows into a copy of the template, applying the protocol rules above (highlighting, checkmark formula, Issue Log entries).
4. Output lands in `data/work/output/`.

## Decisions

- **Numbers are real numbers.** Height, DBH, DBH_HOM, CII, %Crown/%Leaves Remaining, Degrees Leaning, Wounded Trunk, and Living Length are written as numeric cells (not text) unless the sheet literally has a dash or "NA", which stay as text per protocol.
- **Every Issue Log entry cites its cell**, e.g. `[Data Entry!Y6] Tag 4305: ...`, so you can jump straight to it.
- **Census_Start / Census_End**: use the earliest/latest date written across *all* of a site's datasheet pages (not just one page). Left blank+highlighted until all of a site's pages are transcribed and the full date range is known.
- **Ambiguous page dates** (a page header showing two dates): flagged as an issue rather than guessed — `*_Date` columns left blank+highlighted for those rows.
- **Entry_Personnel**: "Violet Williamson" on every row.
- **Geotag_*, Latitude, Longitude, GPS_File_Name** for continuing trees: left empty at L0, not carried forward from `last_inventory` — pending your check with your PI.
- **Species codes**: not validated against a lookup list — you'll check those manually if needed.

## Open items

- [ ] Once a site's full date range is known (after all its pages are transcribed), fill in that site's Census_Start/Census_End across all its rows.

## Progress log

| Date | What I did | Next step |
|------|------------|-----------|
| 2026-09-22 | Created working file | Answer open questions; collect a few sample scans |
| 2026-09-24 | Got protocol, scans, template, prior inventory into `data/`. Read protocol in full, confirmed template columns and a sample scan page match. Built `scripts/build_l0.py` and piloted it on SG-NES1 page 1 (trees 4301–4333) → `data/work/output/SG-NES1_inventory_data_2026_L0_26-09-24_PILOT.xlsx` | Get your check on the pilot's accuracy against the actual scan, then scale to the rest of SG-NES1 and the other 3 sites |
| 2026-09-24 | Updated script per your feedback: real numeric cells, cell references in Issue Log, Entry_Personnel = Violet Williamson, Census_Start/End deferred to whole-site date range, Geotag/Lat/Long left empty for continuing trees, no species-code validation. Rebuilt pilot. | Same as above — check pilot, then scale up |

## Notes and links

-
