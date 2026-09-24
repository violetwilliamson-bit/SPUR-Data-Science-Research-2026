#!/usr/bin/env python3
"""
Build an L0 tree-census workbook from a transcribed CSV of one or more scanned
datasheet pages, following data/protocol/Data Entry Protocol.pdf.

Usage:
    build_l0.py --site SG-NES1 --census 2 \
        --template data/template/Forest_Inventory+Mortality_Data_Entry_Template_2024-09-18.xlsx \
        --prior data/last_inventory/SG-NES1_inventory_data_2021_L2_24-11-04.xlsx \
        --raw data/work/csv/SG-NES1_page01_raw.csv \
        --page-date-status ambiguous \
        --census-start 2026-08-07 --census-end 2026-08-10 \
        --out data/work/output/SG-NES1_inventory_data_2026_L0_<today>.xlsx

Raw CSV columns (one row per tree, in datasheet order):
    tag, prev_tag_sheet, sp_code, height1, height2, height_method,
    dbh1, dbh2, dbh_hom, dbh_method, cii, canopy_pos, survival_status,
    deathdam_status, deathdam_mode, living_length, pct_crown, pct_leaves,
    degrees_leaning, leaf_damage, wounded_trunk, comment,
    unclear_field, unclear_flags

`unclear_field` names which raw-CSV field (e.g. "height1") the issue in
`unclear_flags` refers to, so the Issue Log can cite the exact cell; leave
it blank for a whole-row note. Numeric fields (heights, DBH, HOM, CII,
percentages, degrees leaning, wounded trunk, living length) are written as
real numbers, not text, except when the sheet literally has a dash or NA.
"""
import argparse
import csv
import datetime as dt
import shutil

import openpyxl
from openpyxl.styles import PatternFill
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


def to_cell_value(field, val):
    """Return (value, is_number) for a raw CSV string, per protocol rules."""
    val = val.strip() if val else ""
    if val == "":
        return None, False
    if val == "check":
        return CHECKMARK_FORMULA, False
    if field in NUMERIC_FIELDS and val not in ("-", "NA"):
        try:
            num = float(val)
            if num.is_integer():
                num = int(num)
            return num, True
        except ValueError:
            pass  # not parseable as a number — enter as written, flag separately
    return val, False


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
            cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical="center")
        other_ws.row_dimensions[1].height = 30

    prior = load_prior_inventory(args.prior)

    next_row = 2
    while ws.cell(row=next_row, column=col_idx["Tag_Number"]).value not in (None, ""):
        next_row += 1

    issue_row = 2
    while issues.cell(row=issue_row, column=1).value not in (None, ""):
        issue_row += 1

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

            ws.cell(row=r, column=col_idx["Site_Name"], value=args.site)
            ws.cell(row=r, column=col_idx["Census_Number"], value=args.census)
            ws.cell(row=r, column=col_idx["Tag_Number"], value=tag)
            ws.cell(row=r, column=col_idx["Entry_Personnel"], value=args.entry_personnel)
            ws.cell(row=r, column=col_idx["Entry_Date"], value=args.entry_date)

            if args.census_start:
                ws.cell(row=r, column=col_idx["Census_Start"], value=args.census_start)
            else:
                ws.cell(row=r, column=col_idx["Census_Start"]).fill = HIGHLIGHT
            if args.census_end:
                ws.cell(row=r, column=col_idx["Census_End"], value=args.census_end)
            else:
                ws.cell(row=r, column=col_idx["Census_End"]).fill = HIGHLIGHT

            prior_row = prior.get(tag)
            if prior_row is not None:
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=prior_row["Previous_Tag_Number"])
                ws.cell(row=r, column=col_idx["Tag_Date"], value=prior_row["Tag_Date"])
            else:
                # New tree: prev tag from sheet (if any); tag date = date tagged
                # this survey, passed in via --new-tree-date.
                ws.cell(row=r, column=col_idx["Previous_Tag_Number"], value=raw["prev_tag_sheet"] or "NA")
                if args.new_tree_date:
                    ws.cell(row=r, column=col_idx["Tag_Date"], value=args.new_tree_date)
                else:
                    ws.cell(row=r, column=col_idx["Tag_Date"]).fill = HIGHLIGHT
                    log_issue(f"Tag {tag}: new tree, no --new-tree-date supplied for Tag_Date",
                              row=r, colname="Tag_Date")

            for field, colname in FIELD_MAP.items():
                raw_val = raw.get(field, "")
                cell = ws.cell(row=r, column=col_idx[colname])
                value, _is_num = to_cell_value(field, raw_val)
                if value is None:
                    cell.fill = HIGHLIGHT
                else:
                    cell.value = value

            # Data collection dates: only fill if the page date is unambiguous.
            for datecol in DATE_COLUMNS:
                cell = ws.cell(row=r, column=col_idx[datecol])
                if args.page_date and args.page_date_status == "ok":
                    cell.value = args.page_date
                else:
                    cell.fill = HIGHLIGHT

            unclear = raw.get("unclear_flags", "").strip()
            if unclear:
                unclear_field = raw.get("unclear_field", "").strip()
                colname = FIELD_MAP.get(unclear_field)
                if colname:
                    log_issue(f"Tag {tag}: {unclear}", row=r, colname=colname)
                else:
                    log_issue(f"Tag {tag} (row {r}): {unclear}")

            next_row += 1

    if args.page_date_status != "ok":
        log_issue(f"{args.site}: page date ambiguous/unresolved "
                   f"({args.page_date or 'see scan header'}) — "
                   "Height_Date/DBH_Date/CII_Date/Crown_Class_Date/"
                   "Condition_Obs_Date left blank+highlighted for affected rows")

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
    p.add_argument("--page-date", default=None, help="Date to use for data-collection date columns (YYYY-MM-DD)")
    p.add_argument("--page-date-status", choices=["ok", "ambiguous"], default="ambiguous")
    p.add_argument("--new-tree-date", default=None, help="Tag_Date to use for trees not found in --prior")
    p.add_argument("--census-start", default=None, help="Earliest date across ALL of this site's datasheet pages")
    p.add_argument("--census-end", default=None, help="Latest date across ALL of this site's datasheet pages")
    p.add_argument("--entry-personnel", default="Violet Williamson")
    p.add_argument("--entry-date", default=dt.date.today().isoformat())
    p.add_argument("--out", required=True)
    build(p.parse_args())
