# L0 run log: all 5 sites, October 2026

All five sites' 2026 scans go through one frozen procedure. Rules do not change
during the run. Anything the procedure doesn't cover is entered as written,
flagged, logged, and added to **Rule questions** below for after the run.

## Frozen versions (sha256, first 12 characters)

If any of these files change, the run is no longer on one procedure. Don't edit them until all five sites are built.

| File | Hash |
|---|---|
| L0_DATA_ENTRY_PROCEDURE.md | b896ea262260 (was 28e27c37cd95; 2026-10-21 merged the user's 2026-10-19 GitHub edit: wording only, no rule changed) |
| scripts/READING_BRIEF.md | fde5feb0eb81 |
| scripts/build_l0.py | 5ff8e00ebeb6 |
| scripts/scan_crops.py | 565ed3e24d55 |
| scripts/compare_readings.py | d2c0bc308759 (was be65cf1d36f3; 2026-10-21 fixes before first use: rows whose tag the readers read differently are paired by page order, spacing-only and struck-row blank-vs-dash differences are not counted. No entry rule changed) |
| scripts/add_reading_rows.py | c9288f320a11 (was 7ca03d008f2e; 2026-10-21 bug fix: a malformed line no longer leaves a partial page. Saving only, no rule change) |

Check: `sha256sum L0_DATA_ENTRY_PROCEDURE.md scripts/*.py scripts/READING_BRIEF.md`

## Steps per site

1. **Crop** (one site at a time, low priority so the 2-core machine isn't overloaded):
   `nice -n 19 .venv/bin/python scripts/scan_crops.py data/scans/<scan>.pdf 1 <pages> data/work/images/run2026-10`
2. **Map** pages (sheet number, header date, duplicates) into `data/L0/page_maps.md`.
3. **First reading** (Claude, main session): `data/L0/<SITE>/parts/reading1.csv`, appended one page at a time.
4. **Second reading** (separate subagents that never see reading 1, given `scripts/READING_BRIEF.md` and a page assignment): `data/L0/<SITE>/parts/reading2_pNN-NN.csv`.
   **Dropped from 2026-10-21 (user decision, after the account hit its spend limit):** no new second readings. CA-CAR3 has a full second reading; CC-CVN2 has one for pages 1-8 and 13-19 only (the p9-12 subagent stopped at the limit and saved nothing); SG-NES3, CC-EMN1 and SG-NES1 get one reading. Each workbook's Issue Log states which pages were double-read. The user chose this knowing the second reading caught 15 of the 28 errors in the CA-CAR3 test.
5. **Merge:** concatenate the reading2 parts into `<SITE>_reading2.csv`, copy reading1 to `<SITE>_reading1.csv`, then
   `.venv/bin/python scripts/compare_readings.py <SITE>_reading1.csv <SITE>_reading2.csv <SITE>_raw.csv`
6. **Build** with `scripts/build_l0.py` (procedure step 5) into `data/L0/<SITE>/<SITE>_inventory_data_2026_L0_<YY-MM-DD>.xlsx`.
7. **Hand off:** tell the user the site's workbook in `data/L0/<SITE>/` is ready to hand-check. No copy is made in the repo (user, 2026-10-21); the user checks their own copy, and the L0 file here is never edited.

## Hand-checking while the run continues

Sites are built and handed off one at a time. The hand-check of a finished site does **not** change how later sites are done:
- Corrections go only into the user's own copy, never into the L0 file here.
- Any lesson from a check (a new rule or a reading pattern) is added to **Rule questions** below, tagged with the site it came from. It is not applied until all five sites are built.
- After the run, the agreed rule changes become a new procedure version, and every site is re-checked against it the same way.

## Status

| Site | Pages | Cropped | Mapped | Reading 1 | Reading 2 | Built |
|---|---|---|---|---|---|---|
| CA-CAR3 | 11 | yes | yes | done | done | **yes**: `CA-CAR3_inventory_data_2026_L0_26-10-21.xlsx` (297 trees, 27 disagreeing cells) |
| SG-NES3 | 14 | yes | yes | done | not done (dropped) | **yes**: `SG-NES3_inventory_data_2026_L0_26-10-23.xlsx` (421 trees: 408 + 13 new; single reading) |
| CC-CVN2 | 19 | yes | yes | done | p1-8, p13-19 done; p9-12 none (stopped at spend limit; not rerun, user decision) | **yes**: `CC-CVN2_inventory_data_2026_L0_26-10-21.xlsx` (534 trees, 53 disagreeing cells, 132 single-read trees noted once in the Issue Log) |
| SG-NES1 | 20 | yes | yes | done | not done (dropped) | **yes**: `SG-NES1_inventory_data_2026_L0_26-10-23.xlsx` (555 trees: 522 + 33 new; single reading) |
| CC-EMN1 | 11 | yes (from upright copy) | yes | done | not done (dropped) | **yes**: `CC-EMN1_inventory_data_2026_L0_26-10-23.xlsx` (312 trees: 302 + 10 new; single reading, noted in the Issue Log) |

Order: CA-CAR3, then CC-CVN2 (user, 2026-10-21), then SG-NES3, CC-EMN1, SG-NES1. Order does not affect the procedure.

**Resume note (2026-10-21):** the session was closed mid-site. The CA-CAR3
second reading was started as three subagents (pages 1-4, 5-7, 8-11). All three parts
finished before the session closed, so nothing needs rerunning. CA-CAR3 is built. CC-CVN2 built 2026-10-21. CC-EMN1 built 2026-10-23. SG-NES3 and SG-NES1 built 2026-10-23. **All five sites are built.** Next: the user's hand-check, then the rule questions below.

## Rule questions (for after the run)

- CA-CAR3 p02 tag 8342: living length 6.6 written inside a hand-drawn box (entered as 6.6, flagged).
- CA-CAR3 p02 tag 8360: handwritten arrow in the left margin pointing at the row (noted in the Issue Log).
- CA-CAR3 p05 tag 8452 (2nd reading): 'beetle' written above 'popcorn' as an insertion in DeathDam mode.
- CA-CAR3 p06 tag 8475 (2nd reading): one word ('sappy') struck through inside a comment; the procedure covers lines through whole cells only.
- CA-CAR3 p04 tag 8423 (2nd reading): '8422' written in the comment cell with an arrow from 8422's comment (handwriting linking two rows).
- CA-CAR3 p11 new-tree tags: zeros written over other marks make the tags look five-digit on the zoomed crop (86000 vs 8600); the second reader entered five digits. Entered 8600, 9903-9908 from the full page and flagged.
- CA-CAR3 p10 tag 8587: a faint '15.9' written in the Height Method cell (entered as written, flagged).
- After the run: update README, TREE_CENSUS_WORKING_FILE.md and the procedure, which still mention deleted files (data/archive/, old test set). User chose to wait (2026-10-21).
- CC-CVN2 p15-17: header date written '10/12/26' (after the census; probably 8/12). Entered as written (row_date 2026-10-12) and flagged. Open: Census_End by rule = latest header date = 2026-10-12; decide with the user at build time.
- CC-CVN2 p01: Notes box has a tally ('122 trees left + 73 trees needing ...'), not data; not entered.
- CC-CVN2 p05: '11.6 11.7' written sideways in the left margin beside rows 1860-1862 (matches 1863's heights); not entered, flagged.
- CC-CVN2 p06/p07 (sheet 6a/6b): p07 has a hand-drawn bracket labelled "DONE" in the margin beside 1866-1893, and p06 has margin checkmarks beside 1894-1898 (cross-references between the two copies; not entered).
- CC-CVN2 p07 tag 1897: living-length dash with a hand-drawn loop around it. p08 tag 1926: a star drawn in the left margin (2nd reading).
- CC-CVN2 build: Census_End = 2026-10-12 by the rule (latest header date; p15-17 are written '10/12/26'). Page 1 has no header date, so its rows default to Census_End = 2026-10-12 as well. Both follow the frozen rule; ask the user whether to rebuild with 2026-08-13.
- CC-CVN2: from sheet 12 one crew writes 0 in Wounded Trunk (not in the 1-3 legend; each flagged) and 'A' in Height Method on many rows (flagged).
- CC-EMN1 sheet 6: header has two dates ('8/11/26, 8/14/26'); rows dated 8/14 (later date) and flagged. Which rows were done on which day is not marked.
- CC-EMN1: the scan PDF pages are stored sideways; cropped from an upright copy made with pypdf (crop script unchanged). Several cells hold two codes ('L/B', 'S/B', 'A/X'); entered as written and flagged.
- SG-NES3: many cells in Height/DBH Method written as 'J' (the reading notes say J is T); entered as written and flagged. Sheet 7/13 header has 8/5 and 8/6; dated 8/6.
- SG-NES3 new trees (p14): several comments name a different neighbour tree than the Geotag Ref (e.g. 8216 'next to 8022', ref 7511); entered as written.
- SG-NES1: sheets 1/16, 2/16 and the new-trees sheet have two dates in the header; the later (or the Date field) was used and flagged. Sheet 13 is scanned three times (13a holds 4697-4727; two scans of 13b hold 4728-4729). Sheet 7/16 photo is curved, so right-hand columns drift by up to a row; rows matched by printed labels and comments, flagged.
- SG-NES1 p19 vs p20: the new-trees sheet is photographed twice; read from p19 only.
