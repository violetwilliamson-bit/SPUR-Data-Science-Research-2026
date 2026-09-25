#!/usr/bin/env python3
"""
Build an L0 tree-census workbook from a transcribed CSV of scanned datasheet
pages for one site, following data/protocol/Data Entry Protocol.pdf.

Usage:
    build_l0.py --site SG-NES1 --census 2 \
        --template data/template/Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx \
        --prior data/last_inventory/SG-NES1_inventory_data_2021_L2_24-11-04.xlsx \
        --raw data/work/csv/SG-NES1_all_raw.csv \
        --census-start 2026-08-07 --census-end 2026-08-10 \
        --out data/work/output/SG-NES1_inventory_data_2026_L0_<today>.xlsx

Raw CSV columns (one row per tree, in datasheet order):
    tag, prev_tag_sheet, sp_code, height1, height2, height_method,
    dbh1, dbh2, dbh_hom, dbh_method, cii, canopy_pos, survival_status,
    deathdam_status, deathdam_mode, living_length, pct_crown, pct_leaves,
    degrees_leaning, leaf_damage, wounded_trunk, comment,
    row_date, crossed_out, unclear_field, unclear_flags

`row_date` (YYYY-MM-DD) is the date at the top of the page this row was
transcribed from — used for Height_Date/DBH_Date/CII_Date/Crown_Class_Date/
Condition_Obs_Date, and for Tag_Date on a new tree.

`crossed_out` = Y marks a tree that is fully crossed out on the sheet (already
dead at the previous census): the whole row is highlighted magenta, the small
pre-printed height is NOT entered, blanks are not highlighted, and only what is
actually written (species, DBH "NA", D, status letter, degrees leaning, mode)
is entered. `survival_status` for a dead tree is the boxed letter "D", not "Dead".

If `row_date` is blank the script defaults to --census-end (and logs one issue
saying so). While transcribing, fill `row_date` with the LATEST date listed on
that sheet; leave it blank only when the sheet has no date at all.

Values are checked against the sheet's column legends (e.g. height method must
be T or H, DBH method T or C); anything outside is highlighted and logged.
Degrees leaning of 0 is always written as "-".
"@" and "w/" in Comments / DeathDam mode are spelled out ("at", "with").

`unclear_field` names which raw-CSV field (e.g. "height1") the issue in
`unclear_flags` refers to, so the Issue Log can cite the exact cell; leave
it blank for a whole-row note. Numeric fields (heights, DBH, HOM, CII,
percentages, degrees leaning, wounded trunk, living length) are written as
real numbers, not text, except when the sheet literally has a dash or NA.
"""
import argparse
import csv
import datetime as dt
import re
import shutil

import openpyxl
from openpyxl.styles import PatternFill, Alignment
from openpyxl.utils import get_column_letter

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

# Fields that hold measurements, not codes/text — written as real numbers.
NUMERIC_FIELDS = {
    "height1", "height2", "dbh1", "dbh2", "dbh_hom", "cii",
    "living_length", "pct_crown", "pct_leaves", "degrees_leaning",
    "wounded_trunk",
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
}
ALLOWED_NUMERIC_RANGES = {
    "cii": (1, 5),
    "wounded_trunk": (0, 3),
    "pct_crown": (0, 100),
    "pct_leaves": (0, 100),
    "degrees_leaning": (0, 90),
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


def normalize_text(field, val):
    """Comments / DeathDam mode: spell out '@' and 'w/' (as done in the checked SG-NES1 file)."""
    if field not in ("comment", "deathdam_mode") or not val:
        return val
    val = re.sub(r"\s*@\s*", " at ", val)
    val = re.sub(r"\bw/\s*", "with ", val)
    return re.sub(r"\s{2,}", " ", val).strip()


def to_cell_value(field, val):
    """Return the value to write for a raw CSV string, per protocol rules."""
    val = val.strip() if val else ""
    if val == "":
        return None
    if val == "check":
        return CHECKMARK_FORMULA
    if field == "degrees_leaning" and val in ("0", "0.0"):
        return "-"  # a dash means 0 degrees of lean; record every 0 as a dash
    if field in NUMERIC_FIELDS and val not in ("-", "NA"):
        try:
            num = float(val)
            if num.is_integer():
                num = int(num)
            return num
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

    issue_row = 2
    while issues.cell(row=issue_row, column=1).value not in (None, ""):
        issue_row += 1

    ambiguous_date_rows = []
    fallback_date_rows = []

    def log_issue(text, row=None, colname=None):
        nonlocal issue_row
        if row is not None and colname is not None:
            addr = f"{get_column_letter(col_idx[colname])}{row}"
            text = f"[{ws.title}!{addr}] {text}"
        issues.cell(row=issue_row, column=1, value=text)
        issue_row += 1

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

            prior_row = prior.get(tag)
            if prior_row is not None:
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=prior_row["Previous_Tag_Number"])
                ws.cell(row=r, column=col_idx["Tag_Date"], value=prior_row["Tag_Date"])
            else:
                # New tree: prev tag from sheet (if any); Tag_Date = date tagged
                # this survey = this row's page date.
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=raw["prev_tag_sheet"] or "NA")
                if row_date:
                    ws.cell(row=r, column=col_idx["Tag_Date"], value=parse_date(row_date))
                else:
                    ws.cell(row=r, column=col_idx["Tag_Date"]).fill = HIGHLIGHT
                    log_issue(f"Tag {tag}: new tree, page date ambiguous — Tag_Date left blank",
                              row=r, colname="Tag_Date")

            for field, colname in FIELD_MAP.items():
                raw_val = normalize_text(field, raw.get(field, ""))
                cell = ws.cell(row=r, column=col_idx[colname])
                if crossed_out and field == "height1":
                    # The small number on a crossed-out row is the pre-printed
                    # prior-census height, not a measurement — leave it blank.
                    continue
                value = to_cell_value(field, raw_val)
                if value is None:
                    if not crossed_out:
                        cell.fill = HIGHLIGHT
                else:
                    cell.value = value
                    problem = None if crossed_out else check_allowed(field, raw_val)
                    if problem:
                        cell.fill = HIGHLIGHT
                        log_issue(f"Tag {tag}: {problem}", row=r, colname=colname)

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

            unclear = raw.get("unclear_flags", "").strip()
            if unclear:
                unclear_field = raw.get("unclear_field", "").strip()
                colname = FIELD_MAP.get(unclear_field)
                if colname:
                    log_issue(f"Tag {tag}: {unclear}", row=r, colname=colname)
                else:
                    log_issue(f"Tag {tag} (row {r}): {unclear}")

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
