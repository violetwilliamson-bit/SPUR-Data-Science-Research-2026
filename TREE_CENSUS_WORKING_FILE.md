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

## SG-NES1 scan structure (worth knowing before checking other sites)

The 20-page scan PDF isn't a clean 1:1 page-per-sheet — found while transcribing:
- Sheets are numbered "n/16" in the corner; PDF pages 1–16 map directly to sheets 1/16–13/16, **except** sheet 13 appears three times: page 13 ("13a") has real data, pages 14 and 15 are both a near-blank duplicate ("13b") — only page 13 was entered.
- PDF pages 16–18 = sheets 14/16–16/16 (tags 4730–4822).
- PDF pages 19 and 20 are both the "new trees" addendum (tags 4823–4855, all flagged "out of sequence" with geotag references to nearby trees) — near-identical content scanned/copied twice. Per your call, only entered once (page 19).
- Sheets 12/16 and 13/16 have no date filled in at the top at all — per protocol ("if no date is written at the top, use the last day of the census"), these rows use Census_End (2026-08-10).
- Worth checking the other 3 sites' scans for the same kind of duplicate/blank pages before assuming page count = sheet count.

## Open items

- [ ] **Review `data/work/output/SG-NES1_inventory_data_2026_L0_26-09-24.xlsx` against the scans** — 555 rows, 93 Issue Log entries (mostly the ~99 rows with ambiguous page dates on sheets 1/16, 2/16, and the new-trees addendum; plus ~25 individually-flagged unclear cells — each cites its exact cell).
- [ ] Geotag_Ref/Dist/Dir for the 33 new (out-of-sequence) trees on the addendum page: the template has no dedicated columns matching this sheet's layout, so that data is folded into the Comment field for now — decide whether to add proper columns or leave as-is.
- [ ] Tag 4829's comment references tag 4326 but its Geotag Ref number is 4323 — inconsistency on the sheet itself, flagged in the Issue Log, needs your read of the original.
- [ ] Rows 4728/4729 and 4664/4668 have unusually sparse or odd data on the sheet itself (see Issue Log) — worth a second look at the originals.

## Progress log

| Date | What I did | Next step |
|------|------------|-----------|
| 2026-09-22 | Created working file | Answer open questions; collect a few sample scans |
| 2026-09-24 | Got protocol, scans, template, prior inventory into `data/`. Read protocol in full, confirmed template columns and a sample scan page match. Built `scripts/build_l0.py` and piloted it on SG-NES1 page 1 (trees 4301–4333) | Get your check on the pilot's accuracy, then scale up |
| 2026-09-24 | Updated script per your feedback: real numeric cells, cell references in Issue Log, Entry_Personnel = Violet Williamson, Census_Start/End deferred to whole-site date range, Geotag/Lat/Long left empty for continuing trees, no species-code validation | Same as above |
| 2026-09-24 | Fixed clipped header rows on all 3 sheets (Data Entry, Changelog, Issue Log) | — |
| 2026-09-24 | Cleaned up scratch files; hid `.venv` from Explorer | — |
| 2026-09-24 | Transcribed **all of SG-NES1** (16 main sheets + new-trees addendum, 555 trees), worked out the page/sheet numbering quirks above, resolved Census_Start/End (2026-08-07 to 2026-08-10) from the full page set, rewrote `build_l0.py` to handle a per-row page date (since one site spans multiple survey days) and to write real date objects → `data/work/output/SG-NES1_inventory_data_2026_L0_26-09-24.xlsx` | Get your check on SG-NES1's accuracy, then do the same for SG-NES3, CA-CAR3, CC-CVN2 |

## Notes and links

-
