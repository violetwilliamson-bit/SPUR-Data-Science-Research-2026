"""Append rows to a reading CSV from a compact pipe-separated text.

Usage: addrows.py <out.csv> <row_date> <rows.txt>
Line: tag|h1|h2|hm|d1|d2|hom|dm|cii|can|surv|dds|ddm|ll|ll2|crown|leaves|lean|leaf|wt|comment|crossed|source|flags
New-trees lines add: |prev_tag|sp_code|geotagged|geotag_ref|geotag_dist|geotag_dir
Flags use ' ; ' between notes here (written as ' | ' in the CSV).
"""
import csv, os, sys

COLS = ("tag,prev_tag_sheet,sp_code,height1,height2,height_method,dbh1,dbh2,dbh_hom,dbh_method,cii,"
        "canopy_pos,survival_status,deathdam_status,deathdam_mode,living_length,living_length2,pct_crown,"
        "pct_leaves,degrees_leaning,leaf_damage,wounded_trunk,comment,row_date,crossed_out,source,"
        "unclear_flags,geotagged,geotag_ref,geotag_dist,geotag_dir").split(",")
ORDER = ["tag", "height1", "height2", "height_method", "dbh1", "dbh2", "dbh_hom", "dbh_method", "cii",
         "canopy_pos", "survival_status", "deathdam_status", "deathdam_mode", "living_length",
         "living_length2", "pct_crown", "pct_leaves", "degrees_leaning", "leaf_damage", "wounded_trunk",
         "comment", "crossed_out", "source", "unclear_flags",
         "prev_tag_sheet", "sp_code", "geotagged", "geotag_ref", "geotag_dist", "geotag_dir"]

out, row_date, src = sys.argv[1:4]
# Check every line before writing any, so a bad line never leaves a partial page.
rows = []
for line in open(src):
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"):
        continue
    parts = [p.strip() for p in line.split("|")]
    if len(parts) not in (24, 30):
        sys.exit(f"bad field count {len(parts)} (nothing written): {line}")
    row = dict(zip(ORDER, parts))
    row["unclear_flags"] = " | ".join(x.strip() for x in row["unclear_flags"].split(" ; ") if x.strip())
    row["row_date"] = row_date
    rows.append({c: row.get(c, "") for c in COLS})
new = not os.path.exists(out)
with open(out, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    if new:
        w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} rows appended to {out}")
