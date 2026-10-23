# L0 Data Entry Procedure

How to turn the scanned, handwritten tree census datasheets into L0 spreadsheets. L0 is a cell-for-cell record of what the field crew wrote, with nothing corrected or interpreted. Corrections belong at L1 and L2 (see `data/protocol/Data Entry Protocol.pdf`).

On the messiest handwritting pages tested (CA-CAR3 sheets 6-9/9, 126 trees), the AI scan/reading was 98.9% accurate before human checking: 28 errors in 2,520 handwritten cells, 24 of them already flagged for review.

## Who does what

- **Reading the handwriting:** An AI assistant that can read images (Claude). The scripts do not read handwriting on their own.
- **Building the workbook:** `scripts/build_l0.py` fills the Xcel template, checks every value against the sheet legends, and flags problems.
- **Checking:** A human compares every flagged cell against the paper and corrects a separate copy.

## Inputs and outputs

| Item | What it is | Where |
| --- | --- | --- |
| Scans | One PDF of datasheets per site. The last page(s) hold the new trees. | `data/scans/` (local only, not in git) |
| Template | `Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx` (Data Entry, Changelog, Issue Log sheets) | `data/template/` |
| Prior inventory | 2021 L2 file per site. Source of Tag, Previous Tag, Tag Date and Species for continuing trees. | `data/last_inventory/` |
| Raw transcription | One CSV row per tree, in datasheet column order, with notes on anything unclear | `data/L0/<site>/` |
| L0 workbook | The filled template. Flagged cells are yellow, and each one is explained in the Issue Log. | `data/L0/<site>/` |
| Checked copy | The person's corrected file, kept separate so L0 is never overwritten | `data/L1/` |
| Test set | Messy pages and a checked answer key, used to test rule changes | `data/test/` |

File names follow `<plot_id>_inventory_data_<year>_L0_<YY-MM-DD created>.xlsx`, for example `CA-CAR3_inventory_data_2026_L0_26-10-19.xlsx`.

## Procedure

1. **Map the scan.** Match each PDF page to its sheet number (written in the corner, such as "7/17") and its tag range. A scan can hold two copies of one sheet with different rows filled in (CA-CAR3 sheet 6/9, SG-NES1 sheet 13). Compare such copies row by row before skipping one.

2. **Crop and zoom.** Full pages are too small to tell digits apart, so cut each page into zoomed strips:

   ```
   .venv/bin/python scripts/scan_crops.py <scan.pdf> <first_page> <last_page> data/work/images
   ```

   Each page becomes 3 row bands × 4 column groups (A: heights to CII; B: canopy to DeathDam mode; C: living length to wounded trunk; D: comment), each with the tag column attached, plus a full-page image for the header.

3. **First reading.** Transcribe every handwritten mark into the raw CSV using the entry rules below. Anything unclear goes in the row's `unclear_flags` column as `field: note`, never into a guess.

4. **Second reading.** Read the same page again independently. Flag every cell where the two readings disagree. In the CA-CAR3 test, this caught 15 of the 28 errors.

5. **Build the workbook.**

   ```
   .venv/bin/python scripts/build_l0.py --site <SITE> --census 2 \
       --template "data/template/Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx" \
       --prior data/last_inventory/<SITE>_inventory_data_2021_L2_<date>.xlsx \
       --raw data/L0/<SITE>/<SITE>_raw.csv \
       --census-start <YYYY-MM-DD> --census-end <YYYY-MM-DD> \
       --out data/L0/<SITE>/<SITE>_inventory_data_2026_L0_<YY-MM-DD>.xlsx
   ```

   The script takes identity columns from the prior inventory, checks codes and ranges, colours flagged cells yellow, and writes an Issue Log entry for each flag with a link to its cell.

6. **Human check.** Compare every yellow cell, and spot-check the rest, against the paper. Correct a copy in `data/L1/`.

## Entry rules

**Enter only what is handwritten, exactly as written.** Interpretations go in the Issue Log.

| On the sheet | In the cell |
| --- | --- |
| A handwritten value | The value as written: "190" stays 190, "9.0" stays 9.0, a letter in a number column stays a letter |
| Pre-printed text: prior-census numbers, printed "NA", Live/Dead labels, typed comments, the example row 9999 | Nothing; never entered |
| No handwriting | Blank, not highlighted |
| A dash written by the crew | `-` |
| A line struck through a row or through cells (a tree dead at the previous census, or the cells after "OK") | `-` in every cell the line crosses. Handwriting on the row (such as D and S) is entered as written. The row is not highlighted. |
| A digit written over another, or erased | The darker mark. If only faint writing is left, the cell is blank. The other mark goes in the Issue Log. |
| Two values written in one cell | Both, as `a/b` |
| Two circled living-length values | Living_Length_1_M and Living_Length_2_M |
| A checkmark | `=UNICHAR(10004)` |
| An out-of-range value or invalid code | Entered as written, flagged, and logged |

**Identity columns.** For continuing trees, Site, Tag, Previous Tag, Tag Date and Species come from the 2021 L2 file. A different species handwritten on the sheet is flagged. New trees take these from the new-trees sheet (Previous Tag = `NA`, Tag Date = that sheet's date) and fill Geotagged, Geotag_Association_Ref, _Dist and _Dir.

**Dates.** The five observation date columns (Height, DBH, CII, Crown Class, Condition) use the date written at the top of the sheet being read. A sheet with no header date uses the last day of the census, and this is logged. A different date in the sheet's Notes is logged, not used. Dates are entered as dates only, with no time. Census_Start and Census_End are the earliest and latest header dates across all of a site's sheets.

**Left empty at L0.** Family, Genus, Species, Subspecies and Authority (filled later from a species lookup). For continuing trees, also Geotag_Date, Latitude, Longitude and GPS_File_Name.

**Every row.** Entry_Personnel and Entry_Date (the day the workbook is built).

### Reading notes from the hand checks

- Valid codes follow the sheet legends: Height Method T/H, DBH Method T/C, Canopy D/I/S/C, Survival OK/A/D/X/NF, DeathDam Status S/L/B/U/X, Leaf Damage Y/N, Wounded Trunk 1-3. A "J" in a method column is a T.
- Some crews write a loopy "0" in Degrees Leaning that looks like a 6 or an 8, and an X-shaped "Y" in Leaf Damage. "BV" in DeathDam Mode is BW (budworm).
- A thin, light "1" before "90" in % Crown or % Leaves is an erased 1. Enter 90 and log the 1.
- Handwriting that sits between two rows is flagged, not assigned by guess.

## Flagging and the Issue Log

Yellow marks only the cells a person needs to check. Every yellow cell has a matching Issue Log entry.

- **Flagged:** overwritten or erased marks; hard-to-read values; codes outside the legend; implausible values (such as a negative living length); a species that differs from 2021; any cell where the two readings disagree.
- **Issue Log entry:** Tag Number, a link to the exact cell, what was seen and the other possible reading, and the scan strip it came from (such as `p08_b2`), so every value can be traced back to the paper.
- **Not highlighted:** blank cells, dashes and struck-through rows. These are ordinary entries.

## Raw CSV columns

```
tag, prev_tag_sheet, sp_code, height1, height2, height_method, dbh1, dbh2, dbh_hom,
dbh_method, cii, canopy_pos, survival_status, deathdam_status, deathdam_mode,
living_length, living_length2, pct_crown, pct_leaves, degrees_leaning, leaf_damage,
wounded_trunk, comment, row_date, crossed_out, source, unclear_flags,
geotagged, geotag_ref, geotag_dist, geotag_dir
```

- `row_date`: the sheet's header date (YYYY-MM-DD), or blank if the sheet has none.
- `crossed_out`: `Y` when a strike line runs through the row. The script then enters `-` in every sheet column with no other handwriting.
- `source`: the scan strip the row was read from, such as `p08_b2`.
- `unclear_flags`: notes separated by ` | `. Start a note with a field name (`dbh1: last digit overwritten`) to flag that cell; a note without one applies to the whole row.
- `sp_code`: for continuing trees, filled only if the crew handwrote a species.
- `geotag_*`: new-trees sheet only.
