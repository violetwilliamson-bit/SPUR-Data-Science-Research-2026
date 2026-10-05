#!/usr/bin/env python3
"""
Render scanned datasheet pages, deskew them, and cut each into zoomed bands so
handwriting can be read reliably (a full page is downscaled too far to tell
e.g. 2.16 from 2.6). Each band is cut into four column groups, narrow enough
that the image is not shrunk when it is read, and each has the tag-number
column attached so rows line up:
    A  prev tag, species, heights, DBH, HOM, DBH method, CII
    B  canopy, survival, DeathDam status, DeathDam mode
    C  living length, % crown, % leaves, degrees leaning, leaf damage, wounded trunk
    D  comment
The groups overlap a little so no column is cut in half.

Usage: scan_crops.py <scan.pdf> <first_page> <last_page> <out_dir> [--bands 3]
Output: <out_dir>/<prefix>-pNN_bK_A.png ... _D.png, plus <prefix>-pNN_full.png
(the whole deskewed page, for the header date and the overall layout)
"""
import argparse, os, subprocess, tempfile, glob
import cv2, numpy as np

# Column groups as fractions of the page width (from the 2026 census sheets).
TAG_STRIP = (0.0, 0.065)
GROUPS = {"A": (0.06, 0.345), "B": (0.325, 0.56), "C": (0.54, 0.78), "D": (0.76, 1.0)}

def deskew(gray):
    # Estimate tilt from the long ruled lines on a downscaled copy; angles of
    # exactly 0 are quantisation/page-border artefacts, so ignore them.
    sc = 2000 / gray.shape[1]
    small = cv2.resize(gray, None, fx=sc, fy=sc)
    edges = cv2.Canny(small, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=150,
                            minLineLength=500, maxLineGap=20)
    angs = []
    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if 0.05 < abs(a) < 6:
                angs.append(a)
    ang = float(np.median(angs)) if angs else 0.0
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return M, (w, h), ang


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("first", type=int); ap.add_argument("last", type=int)
    ap.add_argument("out"); ap.add_argument("--bands", type=int, default=3)
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    prefix = os.path.basename(a.pdf).split("_")[0]
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-png", "-r", str(a.dpi), "-f", str(a.first), "-l", str(a.last),
                        a.pdf, os.path.join(td, "p")], check=True)
        for f in sorted(glob.glob(os.path.join(td, "p-*.png"))):
            n = int(os.path.basename(f)[2:-4])
            img = cv2.imread(f)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            M, size, ang = deskew(gray)
            img = cv2.warpAffine(img, M, size, flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
            h, w = img.shape[:2]
            y0, y1 = int(h * 0.02), int(h * 0.98)
            page = n  # pdftoppm names files by the real page number
            cv2.imwrite(os.path.join(a.out, f"{prefix}-p{page:02d}_full.png"),
                        cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
            tag_strip = img[:, int(w * TAG_STRIP[0]):int(w * TAG_STRIP[1])]
            step = (y1 - y0) / a.bands
            for b in range(a.bands):
                ya = int(y0 + b * step - (h * 0.015 if b else 0)); yb = int(y0 + (b + 1) * step + h * 0.015)
                yb = min(yb, h)
                for g, (fa, fb) in GROUPS.items():
                    crop = np.hstack([tag_strip[ya:yb], img[ya:yb, int(w * fa):int(w * fb)]])
                    cv2.imwrite(os.path.join(a.out, f"{prefix}-p{page:02d}_b{b + 1}_{g}.png"), crop)
            print(f"page {page}: deskewed {ang:.2f} deg")

if __name__ == "__main__":
    main()
