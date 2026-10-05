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

These were made under the older entry rules and are now in `data/archive/2026-09_old_rules/`. They are being re-entered under the verbatim L0 rule below into `data/L0/`.

## How it works

1. **Prepare images (script, no AI).** `scripts/scan_crops.py` renders each scan page, straightens it, and cuts it into 3 horizontal bands x 4 column groups (A: tag to CII, B: canopy to DeathDam mode, C: living length to wounded trunk, D: comment), each with the tag column attached. Each crop is small enough to be read without shrinking.
2. **Read the handwriting (AI).** An AI assistant with image reading (Claude) opens each crop and types one row per tree into a raw CSV in `data/L0/<site>/`. This is the only step that uses AI, and the only step where judgment happens. No OCR software is involved.
3. **Build the workbook (script, no AI).** `scripts/build_l0.py` copies the template, fills the identity columns from the prior census, writes the CSV values, and highlights and logs problems. It does not change any value.
4. **Hand-check (person).** Check the L0 file against the paper sheets and rename it L1.

### L0 reading rule (from 2026-10-05)

- Enter only what is **handwritten**, exactly as written: "190" stays 190, "0" stays 0, "w/" stays "w/", a letter in a number column stays a letter. Unless the 1 in front of the 90 looks like it has been erased, slightly lighter text next to darker text. 
- Never enter pre-printed text: the small prior-census numbers, printed "NA", the Live/Dead labels, typed comments (unless circled), or the 9999 example row.
- Site, tag, previous tag, tag date and species for continuing trees come from the prior-census file, as the data entry protocol says.
- A cell with no handwriting stays blank and highlighted.
- Handwriting crossed out by the crew stays out of the cell, blank and highlighted, and is described in the Issue Log.
- Erased or overwritten marks: record the **darker** marks, the ones that remain. If only faint, erased-looking writing is left, the cell stays blank. Flag cells where it is unclear what is erased or actually written in the Issue Log, but there is no need to flag every cell where something was erased and written over, mistakes happen in the field. 
- Out-of-range or invalid values are entered as written, highlighted and logged.
- New-trees sheet (last page(s) of each site): it has no Prev Tag column, so Previous_Tag_Number is "NA". Its Geotag (T/F), Geotag Ref, Geotag Dist and Geotag Dir go into Geotagged, Geotag_Association_Ref, Geotag_Association_Dist and Geotag_Association_Dir.
- Any interpretation goes only in the Issue Log, with a reference to the scan crop (e.g. `scan p01_b2`).

The Issue Log has two extra columns in front of the template's: **Tag_Number** and **Cell** (e.g. `N8 (DBH_1_CM)`, a link that jumps to the flagged cell). Issues are listed in sheet order.

The four L0 files from September 2026 were made under the older rules and are archived. New L0 files go in `data/L0/<site>/`, starting with a pilot of SG-NES3 sheet 1.

## Repo layout

```
data/
  L0/<site>/        current L0 data (verbatim rule): raw CSV + L0 workbook per site
  L1/               hand-checked L1 workbooks
  archive/          superseded files (2026-09_old_rules: first L0 pass, older rules)
  scans/            raw scanned datasheets (not committed; local only)
  template/         the master spreadsheet template
  last_inventory/   the prior census, used to carry forward continuing trees
  protocol/         the Data Entry and Cleanup Protocol
  work/images/      cropped scan images for reading (regenerable scratch; not committed)
scripts/            the build pipeline
```

## More detail

See [TREE_CENSUS_WORKING_FILE.md](TREE_CENSUS_WORKING_FILE.md) for the full protocol summary, per-site notes, open questions, and progress log.
