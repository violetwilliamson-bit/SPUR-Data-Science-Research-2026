# Reading brief: transcribing one scan page into a reading CSV

This brief is given, word for word, to every reader of every page (first and
second reading, every site), so all pages are read the same way. It applies
`L0_DATA_ENTRY_PROCEDURE.md` (read its "Entry rules", "Reading notes" and
"Raw CSV columns" sections first). If the brief and the procedure ever seem to
differ, follow the procedure and note it in `unclear_flags`.

## Keep the readings independent

Read only the scan images. Do not open any other transcription of these
pages: no other `reading*.csv` or `*_raw.csv`, nothing in `data/archive/`,
`data/test/` or another site's `data/L0/` folder, and no L0 workbook. The point
of the second reading is that it is made without seeing the first.

## Images

Crops are in `data/work/images/run2026-10/`, named `<SITE>-pNN_bK_G.png`:
- `pNN` = PDF page, `bK` = row band 1-3 (top, middle, bottom; bands overlap a little,
  so a row near a band edge appears twice: enter it once), `G` = column group:
  - A: prev tag, species, height 1, height 2, height method, DBH 1, DBH 2, DBH HOM, DBH method, CII
  - B: canopy position, survival status, DeathDam status, DeathDam mode
  - C: living length, % crown remaining, % leaves remaining, degrees leaning, leaf damage, wounded trunk
    (on the new-trees sheet C/D also hold Geotag, Geotag Ref, Geotag Dist, Geotag Dir)
  - D: comment
- Every crop has the tag-number column on its left so rows can be matched.
- `<SITE>-pNN_full.png` is the whole page, for the header date and layout.

Open every crop of the page. Zoom by reading the crop itself; never guess from
the full page.

## What to write

One CSV row per tree on the assigned rows, in sheet order, with exactly the
columns listed under "Raw CSV columns" in the procedure:

```
tag,prev_tag_sheet,sp_code,height1,height2,height_method,dbh1,dbh2,dbh_hom,dbh_method,cii,canopy_pos,survival_status,deathdam_status,deathdam_mode,living_length,living_length2,pct_crown,pct_leaves,degrees_leaning,leaf_damage,wounded_trunk,comment,row_date,crossed_out,source,unclear_flags,geotagged,geotag_ref,geotag_dist,geotag_dir
```

- Enter ONLY handwriting, exactly as written. Pre-printed text (the small
  prior-census numbers, printed NA, Live/Dead labels, typed comments, the
  example row 9999) is never entered. No handwriting = empty field.
- `tag`: the printed tag number (new-trees sheet: the handwritten tag).
- `prev_tag_sheet`: new-trees sheet only, if one is handwritten; else empty.
- `sp_code`: continuing trees only if the crew handwrote a species; new-trees
  sheet: the handwritten species.
- `row_date`: given in the page assignment (the header date). Do not change it.
- `crossed_out`: `Y` if a strike line runs through the whole row (dead at the
  previous census); handwriting on such a row is still entered. A strike line
  through only some cells: write `-` in those fields.
- `source`: the band the row was read from, e.g. `p08_b2`.
- `unclear_flags`: notes separated by ` | `, each starting with the field name
  and a colon when it is about one cell, e.g.
  `dbh1: last digit written over another; darker mark reads 4, could be 1`.
  Flag (do not guess) every mark you are not sure of, every overwritten or
  erased mark, handwriting sitting between two rows, and anything the
  procedure does not cover (start such a note with `NEW SITUATION:`).
- Quote fields containing commas. Do not add or drop columns.

## Output

Write the rows to the CSV path given in the assignment (header row included).
Then reply with: the number of rows written, the tag range, and any
`NEW SITUATION` notes.
