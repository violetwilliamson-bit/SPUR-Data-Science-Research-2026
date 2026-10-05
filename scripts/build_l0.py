#!/usr/bin/env python3
"""
Build an L0 tree-census workbook from a transcribed CSV of scanned datasheet
pages for one site, following data/protocol/Data Entry Protocol.pdf.

Usage:
    build_l0.py --site SG-NES1 --census 2 \
        --template data/template/Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx \
        --prior data/last_inventory/SG-NES1_inventory_data_2021_L2_24-11-04.xlsx \
        --raw data/L0/SG-NES1/SG-NES1_raw.csv \
        --census-start 2026-08-07 --census-end 2026-08-10 \
        --out data/L0/SG-NES1/SG-NES1_inventory_data_2026_L0_<today>.xlsx

Raw CSV columns (one row per tree, in datasheet order):
    tag, prev_tag_sheet, sp_code, height1, height2, height_method,
    dbh1, dbh2, dbh_hom, dbh_method, cii, canopy_pos, survival_status,
    deathdam_status, deathdam_mode, living_length, pct_crown, pct_leaves,
    degrees_leaning, leaf_damage, wounded_trunk, comment,
    row_date, crossed_out, source, unclear_flags,
    geotagged, geotag_ref, geotag_dist, geotag_dir   (new-trees sheet only)

VERBATIM RULE (2026-10-05): every data cell holds only what is HANDWRITTEN on
the sheet, exactly as written -- "190" stays 190, "0" stays 0, "w/" stays "w/",
a letter in a number column stays a letter. Pre-printed text (the small
prior-census numbers, printed "NA", the Live/Dead labels, typed prior comments
that are not circled, the 9999 example row) is never entered. A cell with no
handwriting is left blank and highlighted. Handwriting that was crossed out by
the crew is left out of the cell and recorded in the Issue Log. Interpretations
("probably 90") go ONLY in the Issue Log, never in the cell. This script makes
no corrections; it only flags.

Site_Name, Tag_Number, Previous_Tag_Number, Tag_Date and Sp_Code for continuing
trees come from the prior-census file (--prior), as the protocol says, not from
the CSV. For a continuing tree, `sp_code` in the CSV is only filled when the
crew HANDWROTE a species on the row; if it differs from the prior-census code it
is flagged. New trees (not in --prior) take Sp_Code and prev tag from the CSV.

`row_date` (YYYY-MM-DD) is the date at the top of the page this row was
transcribed from -- used for Height_Date/DBH_Date/CII_Date/Crown_Class_Date/
Condition_Obs_Date, and for Tag_Date on a new tree. Fill it with the LATEST
date listed on that sheet; leave it blank only when the sheet has no date, and
the script uses --census-end (protocol rule) and logs that.

`crossed_out` = Y marks a tree that is fully crossed out on the sheet (already
dead at the previous census): the whole row is highlighted magenta. Only the
handwriting on it is entered, like any other row.

New-trees sheet: it has no Prev Tag column (Previous_Tag_Number is entered
as "NA") and has Geotag (T/F), Geotag Ref, Geotag Dist (m) and Geotag Dir
columns, read into the CSV fields geotagged, geotag_ref, geotag_dist,
geotag_dir and written to Geotagged / Geotag_Association_Ref / _Dist / _Dir.
These fields are ignored for continuing trees.

`source` names the scan image(s) the row was read from (e.g. "p01_b1"), so
every value can be traced back to the scan; it is cited in the Issue Log.

Values are checked against the sheet's column legends and ranges (e.g. height
method must be T or H, % crown 0-100); anything outside is still entered
exactly as written, but highlighted and logged.

`unclear_flags` holds Issue Log notes for the row, separated by " | ". Start a
note with a raw-CSV field name and a colon ("dbh1: 13.8 written and crossed
out") so the Issue Log cites the exact cell; a note without one is a whole-row
note. (The older single `unclear_field` column is still honoured.) Numeric
fields are written as real numbers when what is written is a plain number,
and as text otherwise.
"""
import argparse
import csv
import datetime as dt
import re
import shutil
from copy import copy

import openpyxl
from openpyxl.styles import PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink

HIGHLIGHT = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
CHECKMARK_FORMULA = "=UNICHAR(10004)"

# raw CSV field -> Data Entry column name
FIELD_MAP = {
    "sp_code": "Sp_Code",
    "height1": "Height_1_M",
    "height2": "Height_2_M",
    "height_method": "Height_Method",
    "dbh1": "DBH_1_CM",
    "dbh2": "DBH_2_CM",
    "dbh_hom": "DBH_HOM",
    "dbh_method": "DBH_Method",
    "cii": "CII",
    "canopy_pos": "Crown_Class",
    "survival_status": "Survival_Status",
    "deathdam_status": "Death_Damage_Status",
    "deathdam_mode": "Death_Damage_Mode",
    "living_length": "Living_Length_1_M",
    "pct_crown": "Pct_Crown_Remaining",
    "pct_leaves": "Pct_Leaves_Remaining",
    "degrees_leaning": "Degrees_Leaning",
    "leaf_damage": "Leaf_Damage",
    "wounded_trunk": "Wounded_Trunk",
    "comment": "Comments",
}

# Extra columns that only the new-trees sheet has. Written for new trees only;
# for continuing trees these columns are left empty (not on their sheet).
NEW_TREE_FIELD_MAP = {
    "geotagged": "Geotagged",
    "geotag_ref": "Geotag_Association_Ref",
    "geotag_dist": "Geotag_Association_Dist",
    "geotag_dir": "Geotag_Association_Dir",
}

# Fields that hold measurements, not codes/text — written as real numbers.
NUMERIC_FIELDS = {
    "height1", "height2", "dbh1", "dbh2", "dbh_hom", "cii",
    "living_length", "pct_crown", "pct_leaves", "degrees_leaning",
    "wounded_trunk", "geotag_ref", "geotag_dist", "geotag_dir",
}

DATE_COLUMNS = [
    "Height_Date",
    "DBH_Date",
    "CII_Date",
    "Crown_Class_Date",
    "Condition_Obs_Date",
]

# Full-row highlight for trees crossed out on the sheet (already dead at the
# previous census) — matches the convention used in the hand-checked SG-NES1 file.
CROSSED_OUT_FILL = PatternFill(start_color="FF00FF", end_color="FF00FF", fill_type="solid")

# Values the sheet's column legends allow. A value outside these is almost
# certainly a misread (e.g. a "J" in a T/H column), so it's still entered as
# read, but highlighted and logged. "/" separates two conflicting entries.
ALLOWED_CODES = {
    "height_method": {"T", "H"},
    "dbh_method": {"T", "C"},
    "canopy_pos": {"D", "I", "S", "C"},
    "survival_status": {"A", "D", "OK", "X", "NF"},
    "deathdam_status": {"S", "L", "B", "U", "X"},
    "leaf_damage": {"Y", "N"},
    "geotagged": {"T", "F"},
}
ALLOWED_NUMERIC_RANGES = {
    "cii": (1, 5),
    "wounded_trunk": (0, 3),
    "pct_crown": (0, 100),
    "pct_leaves": (0, 100),
    "degrees_leaning": (0, 90),
    "geotag_dir": (0, 360),
}


def check_allowed(field, val):
    """Return a problem description if `val` is outside the sheet's legend, else None."""
    val = val.strip() if val else ""
    if val in ("", "-", "NA", "check"):
        return None
    if field in ALLOWED_CODES:
        parts = [p.strip() for p in val.split("/")]
        bad = [p for p in parts if p not in ALLOWED_CODES[field]]
        if bad:
            return (f"'{val}' is not a valid {field} code "
                    f"(allowed: {', '.join(sorted(ALLOWED_CODES[field]))})")
    if field in ALLOWED_NUMERIC_RANGES:
        lo, hi = ALLOWED_NUMERIC_RANGES[field]
        for p in val.split("/"):
            try:
                n = float(p)
            except ValueError:
                return f"'{val}' is not a number (expected {lo}-{hi})"
            if not lo <= n <= hi:
                return f"'{val}' is outside the expected range {lo}-{hi}"
    return None


def to_cell_value(field, val):
    """Return the value to write for a raw CSV string, per protocol rules."""
    val = val.strip() if val else ""
    if val == "":
        return None
    if val == "check":
        return CHECKMARK_FORMULA
    if field in NUMERIC_FIELDS and val not in ("-", "NA"):
        try:
            num = float(val)
            # Keep "16" as 16 and "16.0" as 16.0: the written form is the data.
            return int(val) if re.fullmatch(r"-?\d+", val) else num
        except ValueError:
            pass  # not parseable as a number — enter as written, flag separately
    return val


def load_prior_inventory(path):
    """Return {tag_number: {Previous_Tag_Number, Tag_Date, Sp_Code}} from an L2 file."""
    if not path:
        return {}
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    headers = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(headers)}
    out = {}
    for r in range(2, ws.max_row + 1):
        row = [ws.cell(row=r, column=c + 1).value for c in range(len(headers))]
        tag = row[idx.get("Tag_Number", -1)] if "Tag_Number" in idx else None
        if tag is None:
            continue
        tag = int(tag) if isinstance(tag, float) else tag
        out[tag] = {
            "Previous_Tag_Number": row[idx["Previous_Tag_Number"]] if "Previous_Tag_Number" in idx else None,
            "Tag_Date": row[idx["Tag_Date"]] if "Tag_Date" in idx else None,
            "Sp_Code": row[idx["Sp_Code"]] if "Sp_Code" in idx else None,
        }
    return out


def parse_date(val):
    """Parse a YYYY-MM-DD string to a date object; pass through other values."""
    if isinstance(val, str) and val.strip():
        try:
            return dt.date.fromisoformat(val.strip())
        except ValueError:
            return val
    return val


def build(args):
    shutil.copy(args.template, args.out)
    wb = openpyxl.load_workbook(args.out)
    ws = wb["Data Entry"]
    issues = wb["Issue Log"]

    headers = [c.value for c in ws[1]]
    col_idx = {h: i + 1 for i, h in enumerate(headers)}

    # The template's header row has wrap-text on but no explicit row height,
    # so long wrapped headers (e.g. "Geotag_Association_Dist") get clipped
    # at the top in Excel. Give the header row enough height to show 3 lines.
    ws.row_dimensions[1].height = 45

    # Changelog and Issue Log headers (e.g. "Cell_or_Column", "Destination_Sheet")
    # are wider than their columns and have wrap-text off, so Excel clips them
    # against the next column. Turn on wrap and give the header row room.
    for other_name in ("Changelog", "Issue Log"):
        other_ws = wb[other_name]
        for cell in other_ws[1]:
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        other_ws.row_dimensions[1].height = 30

    prior = load_prior_inventory(args.prior)

    next_row = 2
    while ws.cell(row=next_row, column=col_idx["Tag_Number"]).value not in (None, ""):
        next_row += 1

    # Issue Log: add Tag_Number and Cell columns in front of the template's
    # Issues column, so each issue can be found at a glance. Cell is a link
    # that jumps to the flagged cell on the Data Entry sheet.
    issues.insert_cols(1, 2)
    for col, name, width in ((1, "Tag_Number", 12), (2, "Cell", 24)):
        hdr = issues.cell(row=1, column=col, value=name)
        hdr.font = copy(issues.cell(row=1, column=3).font)
        hdr.alignment = Alignment(wrap_text=True, vertical="center")
        issues.column_dimensions[get_column_letter(col)].width = width
    for col, width in ((3, 70), (4, 38), (5, 38), (6, 14), (7, 14)):
        issues.column_dimensions[get_column_letter(col)].width = width
    ISSUE_COL = 3

    issue_row = 2
    while issues.cell(row=issue_row, column=ISSUE_COL).value not in (None, ""):
        issue_row += 1

    ambiguous_date_rows = []
    fallback_date_rows = []

    pending_issues = []  # written at the end, sorted by row then column

    def log_issue(text, tag=None, row=None, colname=None):
        """Queue one Issue Log row: Tag_Number | Cell (linked) | Issues."""
        col = col_idx[colname] if colname is not None else 0
        # Site-wide notes (no row) sort after all per-tree issues.
        pending_issues.append(((row if row is not None else 10**9, col), tag, row, colname, text))

    def write_issues():
        r = issue_row
        for _, tag, row, colname, text in sorted(pending_issues, key=lambda i: i[0]):
            if tag is not None:
                issues.cell(row=r, column=1, value=tag)
            if row is not None:
                if colname is not None:
                    addr = f"{get_column_letter(col_idx[colname])}{row}"
                    label = f"{addr} ({colname})"
                else:
                    addr, label = f"A{row}", f"row {row}"
                link = issues.cell(row=r, column=2, value=label)
                link.hyperlink = Hyperlink(ref=link.coordinate, location=f"'{ws.title}'!{addr}")
                link.style = "Hyperlink"
            cell = issues.cell(row=r, column=ISSUE_COL, value=text)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            r += 1

    with open(args.raw, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            r = next_row
            tag_raw = raw["tag"].strip()
            tag = int(tag_raw) if tag_raw.isdigit() else tag_raw
            row_date = raw.get("row_date", "").strip()
            crossed_out = raw.get("crossed_out", "").strip().upper() == "Y"
            if not row_date and args.census_end:
                # No date could be read for this page: default to the latest
                # census date, and say so in the Issue Log.
                row_date = args.census_end
                fallback_date_rows.append(r)

            ws.cell(row=r, column=col_idx["Site_Name"], value=args.site)
            ws.cell(row=r, column=col_idx["Census_Number"], value=args.census)
            ws.cell(row=r, column=col_idx["Tag_Number"], value=tag)
            ws.cell(row=r, column=col_idx["Entry_Personnel"], value=args.entry_personnel)
            ws.cell(row=r, column=col_idx["Entry_Date"], value=parse_date(args.entry_date))

            if args.census_start:
                ws.cell(row=r, column=col_idx["Census_Start"], value=parse_date(args.census_start))
            else:
                ws.cell(row=r, column=col_idx["Census_Start"]).fill = HIGHLIGHT
            if args.census_end:
                ws.cell(row=r, column=col_idx["Census_End"], value=parse_date(args.census_end))
            else:
                ws.cell(row=r, column=col_idx["Census_End"]).fill = HIGHLIGHT

            src = raw.get("source", "").strip()
            where = f" (scan {src})" if src else ""
            sheet_sp = raw.get("sp_code", "").strip()

            prior_row = prior.get(tag)
            if prior_row is not None:
                # Continuing tree: identity columns come from the prior census
                # (protocol), not from reading the printed columns.
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=prior_row["Previous_Tag_Number"])
                ws.cell(row=r, column=col_idx["Tag_Date"], value=prior_row["Tag_Date"])
                ws.cell(row=r, column=col_idx["Sp_Code"], value=prior_row["Sp_Code"])
                if sheet_sp and sheet_sp != prior_row["Sp_Code"]:
                    ws.cell(row=r, column=col_idx["Sp_Code"]).fill = HIGHLIGHT
                    log_issue(f"Species '{sheet_sp}' handwritten on the sheet, "
                              f"prior census says '{prior_row['Sp_Code']}'{where}",
                              tag=tag, row=r, colname="Sp_Code")
            else:
                # New tree: prev tag and species as handwritten; Tag_Date =
                # date tagged this survey = this row's page date.
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=raw["prev_tag_sheet"] or "NA")
                if row_date:
                    ws.cell(row=r, column=col_idx["Tag_Date"], value=parse_date(row_date))
                else:
                    ws.cell(row=r, column=col_idx["Tag_Date"]).fill = HIGHLIGHT
                    log_issue("New tree, page date ambiguous — Tag_Date left blank",
                              tag=tag, row=r, colname="Tag_Date")

            fields = dict(FIELD_MAP)
            if prior_row is None:
                fields.update(NEW_TREE_FIELD_MAP)
            for field, colname in fields.items():
                if field == "sp_code" and prior_row is not None:
                    continue  # written above
                raw_val = raw.get(field, "")
                cell = ws.cell(row=r, column=col_idx[colname])
                value = to_cell_value(field, raw_val)
                if value is None:
                    cell.fill = HIGHLIGHT
                    continue
                cell.value = value
                if isinstance(value, str) and value.startswith("=") and value != CHECKMARK_FORMULA:
                    cell.data_type = "s"  # a written "=" is text, not a formula
                if isinstance(value, float):
                    # Show the decimals that were written ("2.10" stays 2.10).
                    # (".35" written without a leading zero displays as .35)
                    lead = "#" if raw_val.strip().startswith(".") else "0"
                    cell.number_format = lead + "." + "0" * len(raw_val.strip().split(".")[1])
                problem = check_allowed(field, raw_val)
                if problem:
                    cell.fill = HIGHLIGHT
                    log_issue(f"{problem[0].upper()}{problem[1:]} — entered exactly as written{where}",
                              tag=tag, row=r, colname=colname)

            if crossed_out:
                # Whole row highlighted, matching the hand-checked SG-NES1 file.
                for c in range(1, len(headers) + 1):
                    ws.cell(row=r, column=c).fill = CROSSED_OUT_FILL

            # Data collection dates: only fill if this row's page date is known.
            for datecol in DATE_COLUMNS:
                cell = ws.cell(row=r, column=col_idx[datecol])
                if row_date:
                    cell.value = parse_date(row_date)
                else:
                    cell.fill = HIGHLIGHT
                    ambiguous_date_rows.append(r)

            # Notes: "field: text | field: text | whole-row text"
            legacy_field = raw.get("unclear_field", "").strip()
            for note in filter(None, (n.strip() for n in raw.get("unclear_flags", "").split(" | "))):
                field, _, text = note.partition(":")
                colname = {**FIELD_MAP, **NEW_TREE_FIELD_MAP}.get(field.strip())
                if colname and text.strip():
                    note = text.strip()
                else:
                    colname = FIELD_MAP.get(legacy_field)
                if colname:
                    ws.cell(row=r, column=col_idx[colname]).fill = HIGHLIGHT
                    log_issue(f"{note[0].upper()}{note[1:]}{where}", tag=tag, row=r, colname=colname)
                else:
                    log_issue(f"{note[0].upper()}{note[1:]}{where}", tag=tag, row=r)

            next_row += 1

    if ambiguous_date_rows:
        # Report contiguous row ranges (one per affected page), not just the
        # overall min-max, which would wrongly imply every row in between
        # is affected. (Each row can appear once per date column, so dedupe.)
        unique_rows = sorted(set(ambiguous_date_rows))
        ranges = []
        start = prev = unique_rows[0]
        for r in unique_rows[1:]:
            if r == prev + 1:
                prev = r
                continue
            ranges.append((start, prev))
            start = prev = r
        ranges.append((start, prev))
        rows_desc = ", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in ranges)
        log_issue(f"{args.site}: page date ambiguous/unresolved for rows {rows_desc} — "
                   "Height_Date/DBH_Date/CII_Date/Crown_Class_Date/Condition_Obs_Date "
                   "left blank+highlighted (see scan header)")

    if fallback_date_rows:
        log_issue(f"{args.site}: no readable page date for {len(fallback_date_rows)} rows — "
                   f"defaulted to the census end date ({args.census_end}) for Tag_Date (new trees) "
                   "and all *_Date columns; check against the sheet headers")

    if not args.census_start or not args.census_end:
        log_issue(f"{args.site}: Census_Start/Census_End left blank+highlighted — "
                   "need dates from every page of this site's datasheets before filling in "
                   "(protocol: earliest/latest date across all datasheets for the site)")

    write_issues()
    wb.save(args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--site", required=True)
    p.add_argument("--census", type=int, required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--prior", default=None)
    p.add_argument("--raw", required=True)
    p.add_argument("--census-start", default=None, help="Earliest date across ALL of this site's datasheet pages")
    p.add_argument("--census-end", default=None, help="Latest date across ALL of this site's datasheet pages")
    p.add_argument("--entry-personnel", default="Violet Williamson")
    p.add_argument("--entry-date", default=dt.date.today().isoformat())
    p.add_argument("--out", required=True)
    build(p.parse_args())
