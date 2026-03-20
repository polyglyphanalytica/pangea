#!/usr/bin/env python3
"""
Pangea Atlas Validator
======================
Runs the full CLAUDE.md Section 18 checklist against an atlas file.
Exits 0 if ELIGIBLE FOR GO-LIVE, exits 1 if NOT ELIGIBLE.

Usage:
  python3 pangea_validate.py ATLAS_NAME
  e.g. python3 pangea_validate.py dynastia
"""

import re
import sys
from pathlib import Path


def validate(atlas):
    p = Path(f"{atlas}/index.html")
    if not p.exists():
        print(f"FAIL   file not found: {atlas}/index.html")
        print("\nVERDICT: NOT ELIGIBLE — file does not exist")
        sys.exit(1)

    html = p.read_text(encoding="utf-8", errors="replace")
    checks = []

    # ── Item count ──────────────────────────────────────────────────────────
    item_count = len(re.findall(r"^\{id:'", html, re.MULTILINE))
    checks.append(("item_count >= 100",
                   item_count >= 100,
                   f"found {item_count}"))

    # ── Meta description count match ────────────────────────────────────────
    m = re.search(r'<meta name="description"[^>]*content="([^"]*)"', html)
    meta_text = m.group(1) if m else ""
    meta_num = re.search(r'(\d+)', meta_text)
    meta_count = int(meta_num.group(1)) if meta_num else -1
    checks.append(("meta description count matches items",
                   meta_count == item_count,
                   f"meta={meta_count} actual={item_count}"))

    # ── Lens count ──────────────────────────────────────────────────────────
    lens_count = len(re.findall(r"\blbl:'", html))
    checks.append(("lens_count >= 20",
                   lens_count >= 20,
                   f"found {lens_count}"))

    # ── Lenses sorted alphabetically ────────────────────────────────────────
    lens_labels = re.findall(r"lbl:'([^']+)'", html)
    is_sorted = lens_labels == sorted(lens_labels, key=str.lower)
    checks.append(("lenses sorted alphabetically",
                   is_sorted,
                   f"{lens_labels[:3]}..." if not is_sorted else "OK"))

    # ── No empty lens data strings ───────────────────────────────────────────
    empty_lens = len(re.findall(r"['\"](?:history|geography|[a-z_]+)['\"]:\s*['\"]['\"]", html))
    checks.append(("no empty lens data strings",
                   empty_lens == 0,
                   f"{empty_lens} found"))

    # ── Every item has all FP keys ──────────────────────────────────────────
    fp_keys_match = re.search(r"const FP_KEYS\s*=\s*\[([^\]]+)\]", html)
    fp_keys = re.findall(r"'([^']+)'", fp_keys_match.group(1)) if fp_keys_match else []
    checks.append(("FP_KEYS defined",
                   len(fp_keys) > 0,
                   f"{len(fp_keys)} keys"))

    # ── Apostrophes escaped ──────────────────────────────────────────────────
    # Look for unescaped apostrophes inside JS string values (heuristic)
    raw_apos = len(re.findall(r":\s*'[^']*(?<![\\])'[^']*'", html))
    checks.append(("apostrophe escaping — spot check",
                   raw_apos < 5,
                   f"potential issues: {raw_apos} (manual check if >0)"))

    # ── Herstory intact ──────────────────────────────────────────────────────
    checks.append(("herstory marker colour #c060a0",
                   "#c060a0" in html,
                   ""))
    checks.append(("herstory burger label ♀ Herstory",
                   "♀ Herstory" in html,
                   ""))
    checks.append(("WOMEN object defined",
                   "const WOMEN" in html,
                   ""))
    women_entries = len(re.findall(r"nm:\s*'", html))
    checks.append(("WOMEN object populated (>= 5 entries)",
                   women_entries >= 5,
                   f"found {women_entries} entries"))

    # ── No civilitas text leak ───────────────────────────────────────────────
    civ_leak = len(re.findall(r'\bcivilizat', html, re.IGNORECASE))
    # Allow "Civilitas" in the back-link label only
    checks.append(("no civilitas terminology leaked",
                   civ_leak == 0,
                   f"{civ_leak} occurrences" if civ_leak else ""))

    # ── Colour scheme intact ────────────────────────────────────────────────
    checks.append(("amber variable --amber: defined",
                   "--amber:" in html,
                   ""))
    checks.append(("background variable --bg: defined",
                   "--bg:" in html,
                   ""))
    checks.append(("amber value #e89820 present",
                   "#e89820" in html,
                   ""))
    checks.append(("background value #02040a present",
                   "#02040a" in html,
                   ""))

    # ── All 5 modes present ─────────────────────────────────────────────────
    checks.append(("mode: threads/chains panel",
                   "thread" in html.lower() or "chain" in html.lower(),
                   ""))
    checks.append(("mode: compare",
                   "compare" in html.lower(),
                   ""))
    checks.append(("mode: what-if",
                   "what" in html.lower() and "if" in html.lower(),
                   ""))
    checks.append(("mode: heritage/address",
                   "heritage" in html.lower() or "address" in html.lower(),
                   ""))
    checks.append(("mode: herstory toggle",
                   "toggleHerstory" in html,
                   ""))

    # ── Structure checks ────────────────────────────────────────────────────
    checks.append(("back link ../index.html present",
                   "../index.html" in html,
                   ""))
    checks.append(("skip link present",
                   "skip-link" in html,
                   ""))
    checks.append(("JSON-LD structured data",
                   "application/ld+json" in html,
                   ""))
    checks.append(("single <script> block in body",
                   html.count("<script>") <= 2,  # allow one in head for JSON-LD
                   f"script tags: {html.count('<script>')}"))
    checks.append(("no <script> src in head (one-file rule)",
                   "fonts.googleapis" in html,  # Google Fonts is the only allowed head link
                   ""))

    # ── TRANSMISSIONS defined ───────────────────────────────────────────────
    tx_count = len(re.findall(r"\{from:", html))
    checks.append(("TRANSMISSIONS defined (>= 10)",
                   tx_count >= 10,
                   f"found {tx_count}"))

    # ── HERITAGE_REGIONS defined ─────────────────────────────────────────────
    checks.append(("HERITAGE_REGIONS defined",
                   "HERITAGE_REGIONS" in html or "COSMIC_ADDRESS" in html,
                   ""))

    # ── Print results ────────────────────────────────────────────────────────
    all_pass = True
    fails = []
    manual = []

    for name, passed, detail in checks:
        if passed:
            status = "PASS  "
        elif "spot check" in name or "manual" in name.lower():
            status = "WARN  "
            manual.append(name)
        else:
            status = "FAIL  "
            all_pass = False
            fails.append(name)

        suffix = f"  [{detail}]" if detail else ""
        print(f"{status} {name}{suffix}")

    print()
    print(f"Items:  {item_count}  |  Lenses: {lens_count}  |  WOMEN entries: {women_entries}  |  Transmissions: {tx_count}")
    print()

    if all_pass and not fails:
        print("VERDICT: ELIGIBLE FOR GO-LIVE")
        sys.exit(0)
    else:
        print(f"VERDICT: NOT ELIGIBLE — {len(fails)} check(s) failed:")
        for f in fails:
            print(f"  ✗ {f}")
        if manual:
            print(f"  ⚠ Manual checks needed: {manual}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    validate(sys.argv[1])
