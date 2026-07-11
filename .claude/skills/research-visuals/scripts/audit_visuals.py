#!/usr/bin/env python3
"""audit_visuals.py — first-pass, fact-only audit of figures/tables in PDF(s).

SCOPE (deliberately narrow): this script only extracts facts that Poppler reports
authoritatively, then renders page previews. It does NOT judge overlap, colour, or
aesthetics — those are delegated to a human / vision-model review of the previews
(see references/audit.md). Two layers back each other up.

FAIL-LOUD: if a tool is missing or its output can't be parsed (encrypted/corrupt
PDF, unexpected Poppler version), the affected check reports "could not check —
manual review required" and the run is NOT clean. It never prints a false "clean".

Checks (read-only on the PDFs; paths are CLI args — no hardcoded paths):
  fonts   pdffonts   -> # typeface families, non-embedded fonts, Type 3 (bitmap) fonts
  raster  pdfimages  -> embedded-image DPI vs the print floor; raster-heavy flag
  render  pdftocairo -> page PNGs for the visual-review layer

Usage:
  python audit_visuals.py FILE.pdf [more.pdf ...] [--out DIR] [--render-dpi N]
         [--max-families N] [--min-dpi N] [--no-render] [--json]

Exit 0 = all checks ran and found nothing; 1 = defects found OR a check could not run.
Stdlib + Poppler only. Unit-tested: the parse_* functions are pure (see
test_audit_visuals.py).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SUBSET_RE = re.compile(r"^[A-Z]{6}\+")  # subset tag, e.g. ABCDEF+
# anchor on the fixed tail of a pdffonts row: emb sub uni object ID
FONTROW_RE = re.compile(r"\b(yes|no)\s+(yes|no|sub|----)\s+(yes|no)\s+(\d+)\s+(\d+)\s*$")


# --------------------------------------------------------------------------- #
# Pure parsers (unit-tested; no I/O — feed them captured tool output)
# --------------------------------------------------------------------------- #
def family_of(name: str) -> str:
    """Collapse a font name to its typeface family (drop subset tag + style suffix)."""
    n = SUBSET_RE.sub("", name)          # ABCDEF+Arial-BoldMT -> Arial-BoldMT
    n = n.split("-")[0].split(",")[0]    # -> Arial
    n = re.sub(r"(PSMT|PS|MT)$", "", n)  # TimesNewRomanPS -> TimesNewRoman
    return n or name


def parse_fonts(text: str) -> dict:
    """Parse `pdffonts` stdout. parse_ok=False if it doesn't look like pdffonts output."""
    lines = text.splitlines()
    header_idx = next((i for i, ln in enumerate(lines)
                       if ln.lower().startswith("name") and "emb" in ln.lower()), None)
    if header_idx is None:
        return {"parse_ok": False, "rows": 0, "families": [], "n_families": 0,
                "non_embedded": [], "type3": []}
    families, non_embedded, type3 = set(), [], []
    rows = 0
    for line in lines[header_idx + 2:]:   # skip header + dashed rule
        if not line.strip():
            continue
        rows += 1
        name = line.split()[0]
        m = FONTROW_RE.search(line)
        emb = m.group(1) if m else "?"
        if "Type 3" in line:
            type3.append(name)
        if emb == "no":
            non_embedded.append(name)
        families.add(family_of(name))
    return {"parse_ok": True, "rows": rows, "families": sorted(families),
            "n_families": len(families), "non_embedded": non_embedded, "type3": type3}


def parse_raster(text: str, min_dpi: int) -> dict:
    """Parse `pdfimages -list` stdout. parse_ok=False if it doesn't look right."""
    lines = text.splitlines()
    header_idx = next((i for i, ln in enumerate(lines)
                       if ln.lower().startswith("page") and "ppi" in ln.lower()), None)
    if header_idx is None:
        return {"parse_ok": False, "n_images": 0, "low_dpi": [], "min_dpi_seen": None}
    images, low = [], []
    for line in lines[header_idx + 2:]:
        f = line.split()
        if len(f) < 14:
            continue
        try:
            page, xppi, yppi = int(f[0]), int(f[12]), int(f[13])
        except ValueError:
            continue
        dpi = min(xppi, yppi)
        rec = {"page": page, "dpi": dpi, "size": f"{f[3]}x{f[4]}"}
        images.append(rec)
        if 0 < dpi < min_dpi:
            low.append(rec)
    return {"parse_ok": True, "n_images": len(images), "low_dpi": low,
            "min_dpi_seen": min((i["dpi"] for i in images), default=None)}


# --------------------------------------------------------------------------- #
# I/O wrappers
# --------------------------------------------------------------------------- #
def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def render_previews(pdf: Path, out_dir: Path, dpi: int) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / pdf.stem
    run(["pdftocairo", "-png", "-r", str(dpi), str(pdf), str(prefix)])
    return sorted(str(p) for p in out_dir.glob(pdf.stem + "*.png"))


def audit_one(pdf: Path, args) -> dict:
    rep = {"pdf": pdf.name, "flags": [], "needs_review": []}

    # ---- fonts ----
    if not have("pdffonts"):
        rep["needs_review"].append("pdffonts not found — cannot check fonts (install poppler-utils)")
    else:
        r = run(["pdffonts", str(pdf)])
        f = parse_fonts(r.stdout)
        rep["fonts"] = f
        if r.returncode != 0 or not f["parse_ok"]:
            rep["needs_review"].append("pdffonts could not analyze this PDF "
                                       "(encrypted/corrupt?) — manual font review required")
        else:
            if f["n_families"] > args.max_families:
                rep["flags"].append(f"{f['n_families']} typeface families (> {args.max_families}) — "
                                    f"inconsistent: {', '.join(f['families'])}")
            if f["non_embedded"]:
                rep["flags"].append(f"{len(f['non_embedded'])} non-embedded font(s): "
                                    f"{', '.join(f['non_embedded'])}")
            if f["type3"]:
                rep["flags"].append(f"{len(f['type3'])} Type 3 (bitmap) font(s) — "
                                    f"forbidden by NeurIPS/IEEE; re-export as vector text")

    # ---- raster ----
    if not have("pdfimages"):
        rep["needs_review"].append("pdfimages not found — cannot check resolution (install poppler-utils)")
    else:
        r = run(["pdfimages", "-list", str(pdf)])
        rr = parse_raster(r.stdout, args.min_dpi)
        rep["raster"] = rr
        if r.returncode != 0 or not rr["parse_ok"]:
            rep["needs_review"].append("pdfimages could not analyze this PDF — manual resolution review required")
        else:
            if rr["low_dpi"]:
                pages = ", ".join(str(i["page"]) for i in rr["low_dpi"])
                rep["flags"].append(f"{len(rr['low_dpi'])} raster image(s) < {args.min_dpi} dpi "
                                    f"(blurry in print) on page(s) {pages}")
            if rr["n_images"] > 0:
                rep["flags"].append(f"{rr['n_images']} embedded raster image(s) — confirm charts are "
                                    f"VECTOR (PDF/SVG), not pasted bitmaps")

    # ---- render previews (for the visual-review layer) ----
    if not args.no_render:
        if have("pdftocairo"):
            rep["previews"] = render_previews(pdf, Path(args.out), args.render_dpi)
        else:
            rep["needs_review"].append("pdftocairo not found — cannot render previews for visual review")

    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+", help="PDF file(s) to audit")
    ap.add_argument("--out", default="qa_previews", help="dir for rendered previews")
    ap.add_argument("--render-dpi", type=int, default=150, help="preview render DPI")
    ap.add_argument("--max-families", type=int, default=3,
                    help="warn above this many typeface families (body+math+mono=3)")
    ap.add_argument("--min-dpi", type=int, default=300, help="raster DPI floor")
    ap.add_argument("--no-render", action="store_true", help="skip preview rendering")
    ap.add_argument("--json", action="store_true", help="emit machine summary")
    args = ap.parse_args()

    reports, not_clean = [], False
    for p in args.pdfs:
        pdf = Path(p)
        if not pdf.is_file():
            print(f"ERROR: not found: {pdf}", file=sys.stderr)
            not_clean = True
            continue
        rep = audit_one(pdf, args)
        reports.append(rep)
        if rep["flags"] or rep["needs_review"]:
            not_clean = True

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for rep in reports:
            print(f"\n=== {rep['pdf']} ===")
            fo = rep.get("fonts")
            if isinstance(fo, dict) and fo.get("parse_ok"):
                print(f"  fonts:  {fo['n_families']} families, "
                      f"{len(fo['non_embedded'])} non-embedded, {len(fo['type3'])} Type 3")
            ra = rep.get("raster")
            if isinstance(ra, dict) and ra.get("parse_ok"):
                print(f"  raster: {ra['n_images']} image(s), "
                      f"min {ra['min_dpi_seen']} dpi, {len(ra['low_dpi'])} below floor")
            if rep.get("previews"):
                print(f"  previews: {len(rep['previews'])} page PNG(s) in {args.out}/ "
                      f"-> review for overlap / colour / spacing (the second layer)")
            for fl in rep["flags"]:
                print(f"  FLAG: {fl}")
            for nr in rep["needs_review"]:
                print(f"  NEEDS REVIEW: {nr}")
            if not rep["flags"] and not rep["needs_review"]:
                print("  clean — mechanical checks passed (still eyeball the previews)")
    return 1 if not_clean else 0


if __name__ == "__main__":
    sys.exit(main())
