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
- `data/work/` — scratch area: `images/` (rendered page PNGs), `csv/` (transcribed raw rows per page), `output/` (built L0 workbooks), `checked/` (your hand-checked/edited workbooks, e.g. `SG-NES1_inventory_data_2026_L1_<date>.xlsx` — kept separate so my original L0 output is never overwritten).

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
- Sheets are numbered "n/16" in the corner; PDF pages 1–16 map directly to sheets 1/16–13/16, **except** sheet 13 appears three times: page 13 ("13a") has real data for tags 4697–4727, and pages 14 and 15 are two scans of "13b", which looks like a near-blank duplicate **but is not** — it holds the real data for tags 4728 and 4729 (which are blank on 13a). I only entered 13a, so those two rows were incomplete until you fixed them. Lesson: compare apparent duplicate pages row by row before skipping one.
- PDF pages 16–18 = sheets 14/16–16/16 (tags 4730–4822).
- PDF pages 19 and 20 are both the "new trees" addendum (tags 4823–4855, all flagged "out of sequence" with geotag references to nearby trees) — near-identical content scanned/copied twice. Per your call, only entered once (page 19).
- Sheets 12/16 and 13/16 have no date filled in at the top at all — per protocol ("if no date is written at the top, use the last day of the census"), these rows use Census_End (2026-08-10).
- Worth checking the other 3 sites' scans for the same kind of duplicate/blank pages before assuming page count = sheet count.

## What your hand-check of SG-NES1 taught me

I diffed your checked workbook against my original (982 changed cells). What changed, and what I do differently from now on:

| What you fixed | Cause | Now |
|---|---|---|
| 8 × "J" in Height_Method → "T" | Misread; only T/H are valid | Script checks every coded column against the sheet legends and flags anything outside (would have caught all 8) |
| "Dead" in Survival_Status → "D" (46 rows) | I wrote the word instead of the boxed letter | Use the boxed letter; script flags "Dead" |
| Degrees_Leaning / Leaf_Damage swapped on ~12 dead rows | Column misalignment in my CSV for dead rows | Crossed-out rows now use a `crossed_out` flag; script writes them, so no hand-aligned blanks |
| Heights on crossed-out (already-dead) rows removed | That small number is the pre-printed prior-census value, not a measurement | Not entered for crossed-out rows |
| ~63 comments removed | I entered the small **pre-printed** prior-census comments (e.g. "shares base with 4408"); protocol says only enter them if circled | Only handwritten / circled comments |
| Comment placed on wrong row (e.g. 4301 vs 4302) | Handwriting sits between rows | Flag comments that sit between rows instead of guessing |
| "@" → "at", "w/" → "with" | You normalized these | Script does it in Comments / DeathDam mode |
| Two conflicting values kept as "9.9/10.4" | I had kept only the first | Enter both, separated by "/" |
| ~54 heights, a few DBH/HOM digit misreads (e.g. 2.16 → 2.6, 3.6 → 3, 13.2 → 12.2) | Handwriting | Flag digit strings that are unusual for the tree's size |
| Rows 4728 / 4729 filled in | I skipped page 13b (see above) | Compare duplicate pages row by row |
| Crossed-out rows highlighted magenta, whole row | Your convention | Script highlights crossed-out rows magenta |

Confirmed convention for a crossed-out row: only Tag, Prev tag, Sp_Code, DBH_1 = "NA", Survival "D", DeathDam status, degrees leaning / mode if written, plus **all five *_Date columns filled**.

Dates: for the next sites, `*_Date` and new-tree `Tag_Date` default to the **latest date listed on that sheet**, or the **census end date** if the sheet has none (no more blank+highlighted "ambiguous" rows).

Open questions from the diff:
- **Tag_Date is empty in every row of your checked file** (all 522 continuing trees). Deliberate (waiting on your PI), or lost in the export?
- **Degrees_Leaning "0" → "-"** on 67 rows, almost all on sheets 14–16 (tags 4730–4822). On the scan those read as 0s to me. Is a "0" on these sheets meant to be a dash, or is 0 right and "-" your choice?
- Single cells highlighted magenta (mostly DBH_Date on tags 4334–4366 and 4823–4855; also some Wounded_Trunk / Living_Length) — a different meaning from the full-row crossed-out highlight?
- Did you want the SG-NES1 raw CSV / workbook regenerated with these fixes? I left them alone since your checked file is now the better version.

## SG-NES3 (transcribed 2026-09-25)

- 14-page scan = 13 numbered sheets ("n/13", page N = sheet N, no duplicates) + a new-trees addendum (page 14). Page 13's lower half is blank.
- 421 trees: all 408 from the 2021 inventory (tags 7501–7600 and 7901–8208; the 7600→7901 jump is real and matches the 2021 file) + 13 new trees (8209–8221).
- Dates: `*_Date` = latest date on each sheet (8/5 or 8/6; page 7's header lists both, so 8/6). Sheet 3 has no date, so it defaults to the census end (8/6). Census 2026-08-05 to 2026-08-06. New trees use the addendum's date (8/5).
- Crossed-out rows (already dead at the previous census) are magenta-highlighted: 7554, 7558, 7580, 8038, 8183, 8186, 8189 (+ 7990, a dropped tag).
- New-tree geotag ref/dist/dir are folded into the Comment (same as SG-NES1). Six new trees have a geotag ref that disagrees with the tag named in their comment — flagged.
- 65 Issue Log entries (each cites its cell): mostly stray "1" before "90" in % crown/leaves (entered 90), "+" or "N" in Wounded_Trunk / Degrees_Leaning, negative Living_Length (-0.1), and dashes where DBH_HOM would be 0.
- Scan workflow change: `scripts/scan_crops.py` deskews each page and cuts it into zoomed left/right bands; the full-page images were too small to tell digits apart reliably.

## CA-CAR3 (transcribed 2026-09-25)

- 11-page scan = sheets 1/9-9/9, a second copy of sheet 6/9, and a new-trees sheet (page 11, labeled "10/9"). The two copies of 6/9 are complementary, not duplicates: page 6 holds trees 8466-8476 (8477-8498 are blank pre-printed rows), page 7 holds 8477-8498 (8466-8476 blank). Both were used. Same pattern as SG-NES1's sheet 13a/13b.
- 297 trees: all 291 from the 2021 inventory (8301-8591) + 6 new trees (8600, 9903, 9904, 9905, 9907, 9908). Tag 9902 is mentioned on tag 8325's comment ("new tag -> 9902 out of seq") but has no row on the new-trees sheet - worth asking.
- Dates: every sheet is 8/8/26 (page 5 has no date, so it defaults to the census end, which is also 8/8/26). Census start = census end = 2026-08-08.
- 31 crossed-out (already dead) rows, magenta. 54 Issue Log entries.
- New-tree geotag ref/dist/dir are folded into the Comment, as for the other sites. New-tree tag numbers jump 8600 -> 9903 (out of series), all entered in increasing tag order.
- Sheets 5-9 have a dash in DBH_HOM where the other sites write 0 (entered as written; flagged once per sheet).
- Several rows have a line drawn through DeathDam status/mode but real numbers in the rest of the row (e.g. 8485, 8499): entered as read and flagged.

## Open items

- [ ] **Hand-off (after all four sites are done):** make this reusable by whoever comes next, given the same template and datasheets. Plan: move the valid-code lists and the column map out of `build_l0.py` into a config file; add `requirements.txt`; write a README covering the steps (render + crop scans, transcribe, build, spot-check); document the conventions from the SG-NES1 check. Note for the README: the reading of handwriting is done by Claude looking at the cropped images, so the next person needs an AI assistant with image reading, not just the scripts.
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
| 2026-09-25 | Compared your checked SG-NES1 workbook (in `data/work/checked/`) against my original; added valid-value checks, `crossed_out` row handling, comment normalization and a latest-date default to `build_l0.py`; documented the lessons above | Answer the open questions from the diff, then transcribe SG-NES3 / CA-CAR3 / CC-CVN2 |
| 2026-09-25 | Built degrees-leaning 0→"-" into the script; transcribed all of SG-NES3 (421 trees) with the new checks → `data/work/output/SG-NES3_inventory_data_2026_L0_26-09-25.xlsx` | Your spot-check of SG-NES3, then CA-CAR3 and CC-CVN2 |
| 2026-09-25 | Transcribed all of CA-CAR3 (297 trees) with the same checks → `data/work/output/CA-CAR3_inventory_data_2026_L0_26-09-25.xlsx` | Your spot-check of CA-CAR3, then CC-CVN2 (last site) |

## Notes and links

-
