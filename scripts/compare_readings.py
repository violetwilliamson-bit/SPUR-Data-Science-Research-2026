#!/usr/bin/env python3
"""
Merge two independent readings of a site's scan pages into the raw CSV that
build_l0.py takes (procedure step 4).

The first reading's values go into the cells. Every field where the second
reading differs gets an `unclear_flags` note citing the other reading, so the
cell is highlighted and logged for the human check. The second reading's own
notes are carried over too, marked "(2nd reading)". A tag found in only one
reading is kept and flagged as a whole row.

Usage: compare_readings.py <reading1.csv> <reading2.csv> <out_raw.csv>
"""
import csv
import sys

# Fields compared between the readings (everything except bookkeeping).
SKIP = {"source", "unclear_flags"}


def norm(v):
    return " ".join((v or "").split())


def load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, {r["tag"].strip(): r for r in rows}


def main(r1_path, r2_path, out_path):
    rows1, by_tag1 = load(r1_path)
    rows2, by_tag2 = load(r2_path)
    fields = list(rows1[0].keys())
    # A tag the readers read differently (e.g. a handwritten new-tree tag)
    # leaves a row in each reading with no match. Pair those rows by their
    # order on the same scan page, so the tag is flagged as a disagreement
    # instead of the tree appearing twice.
    page = lambda r: (r.get("source") or "").split("_")[0]
    left1 = [r for r in rows1 if r["tag"].strip() not in by_tag2]
    left2 = [r for r in rows2 if r["tag"].strip() not in by_tag1]
    for r1 in left1:
        same = [r2 for r2 in left2 if page(r2) == page(r1)]
        if same:
            r2 = same[0]
            left2.remove(r2)
            by_tag2[r1["tag"].strip()] = r2
            by_tag1[r2["tag"].strip()] = r1
    n_dis = 0
    out = []
    for row in rows1:
        tag = row["tag"].strip()
        notes = [n for n in (row.get("unclear_flags") or "").split(" | ") if n.strip()]
        other = by_tag2.get(tag)
        if other is None:
            notes.append("Row not found in the second independent reading - check the scan")
        else:
            struck = norm(row.get("crossed_out")).upper() == "Y" == norm(other.get("crossed_out")).upper()
            for f in fields:
                if f in SKIP:
                    continue
                # Spacing between handwritten marks ("10% R" / "10%R") is not
                # a reading difference; on a struck row a blank cell becomes
                # "-" in the build, so blank and "-" are the same entry there.
                a, b = (norm(row.get(f)).replace(" ", ""), norm(other.get(f)).replace(" ", ""))
                if struck and {a, b} <= {"", "-"}:
                    continue
                if a != b:
                    b = norm(other.get(f))
                    n_dis += 1
                    notes.append(f"{f}: second independent reading disagrees "
                                 f"(other read: '{b or 'blank'}') - check the scan")
            for n in (other.get("unclear_flags") or "").split(" | "):
                if n.strip():
                    field, sep, text = n.partition(":")
                    notes.append(f"{field}: (2nd reading) {text.strip()}" if sep and field.strip() in fields
                                 else f"(2nd reading) {n.strip()}")
        row = dict(row)
        row["unclear_flags"] = " | ".join(notes)
        out.append(row)
    for row in rows2:
        tag = row["tag"].strip()
        if tag not in by_tag1:
            row = dict(row)
            row["unclear_flags"] = " | ".join(
                ["Row only in the second independent reading; its values are entered - check the scan"]
                + [n for n in (row.get("unclear_flags") or "").split(" | ") if n.strip()])
            out.append(row)
    out.sort(key=lambda r: (0, int(r["tag"])) if r["tag"].strip().isdigit() else (1, r["tag"]))
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} rows, {n_dis} disagreeing cells -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
