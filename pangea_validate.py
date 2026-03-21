#!/usr/bin/env python3
"""
Pangea Atlas Validator
======================
Runs the full CLAUDE.md Section 18 checklist against an atlas file.
Exits 0 if ELIGIBLE FOR GO-LIVE, exits 1 if NOT ELIGIBLE.

Usage:
  python3 pangea_validate.py ATLAS_NAME
"""

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


def _record_validation(atlas, item_count, lens_count):
    """Record passing validation commit SHA into pangea_state.json."""
    state_path = Path("pangea_state.json")
    if not state_path.exists():
        return

    # Get current commit SHA for this atlas file
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", f"{atlas}/index.html"],
        capture_output=True, text=True
    )
    sha = result.stdout.strip() or "unknown"

    short = subprocess.run(
        ["git", "log", "-1", "--format=%h", f"{atlas}/index.html"],
        capture_output=True, text=True
    ).stdout.strip() or sha[:7]

    state = json.loads(state_path.read_text())
    info = state.get("atlases", {}).get(atlas, {})
    info["validated_sha"] = sha
    info["validated_short"] = short
    info["validated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    info["validated_items"] = item_count
    info["validated_lenses"] = lens_count
    state["atlases"][atlas] = info
    state_path.write_text(json.dumps(state, indent=2))
    print(f"Validation recorded: {atlas} @ {short} ({datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC)")


def validate(atlas):
    p = Path(f"{atlas}/index.html")
    if not p.exists():
        print(f"FAIL   file not found: {atlas}/index.html")
        print("\nVERDICT: NOT ELIGIBLE")
        sys.exit(1)

    # ── Skip if already validated at current commit ────────────────────────
    state_path = Path("pangea_state.json")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        info = state.get("atlases", {}).get(atlas, {})
        stored_sha = info.get("validated_sha")
        if stored_sha:
            current_sha = subprocess.run(
                ["git", "log", "-1", "--format=%H", f"{atlas}/index.html"],
                capture_output=True, text=True
            ).stdout.strip()
            if current_sha and current_sha == stored_sha:
                short = info.get("validated_short", current_sha[:7])
                at = info.get("validated_at", "")[:10]
                print(f"SKIP  Already validated at {short} ({at}) — no changes since.")
                print("VERDICT: ELIGIBLE FOR GO-LIVE")
                sys.exit(0)

    html = p.read_text(encoding="utf-8", errors="replace")
    checks = []

    # ── Item count ──────────────────────────────────────────────────────────
    item_count = len(re.findall(r"^\{id:'", html, re.MULTILINE))
    checks.append(("item_count >= 100", item_count >= 100, f"found {item_count}"))

    # ── Meta description count ──────────────────────────────────────────────
    m = re.search(r'<meta name="description"[^>]*content="([^"]*)"', html)
    meta_text = m.group(1) if m else ""
    meta_num = re.search(r'(\d+)', meta_text)
    meta_count = int(meta_num.group(1)) if meta_num else -1
    checks.append(("meta count matches items", meta_count == item_count,
                   f"meta={meta_count} actual={item_count}"))

    # ── Lens count and sort ─────────────────────────────────────────────────
    lenses_block = re.search(r'const LENSES\s*=\s*\[[\s\S]*?\];', html)
    lenses_text = lenses_block.group(0) if lenses_block else ""
    lens_ids = re.findall(r"id:'([^']+)'", lenses_text)
    lens_labels = re.findall(r"lbl:'([^']+)'", lenses_text)
    lens_count = len(lens_ids)
    checks.append(("lens_count >= 20", lens_count >= 20, f"found {lens_count}"))
    is_sorted = lens_labels == sorted(lens_labels, key=str.lower)
    checks.append(("lenses sorted alphabetically",
                   is_sorted, "OK" if is_sorted else f"unsorted: {lens_labels[:4]}"))

    # ── Item d{} keys match lens IDs ───────────────────────────────────────
    items_block = re.search(r'const ITEMS\s*=\s*\[[\s\S]*?\];', html)
    items_text = items_block.group(0) if items_block else ""
    d_blocks = re.findall(r'd:\{([^}]+)\}', items_text)
    lens_id_set = set(lens_ids)
    orphan_keys = set()
    items_missing_keys = 0
    for d in d_blocks:
        keys = set(re.findall(r"(\w+):'", d))
        orphan_keys.update(keys - lens_id_set)
        if lens_id_set - keys:
            items_missing_keys += 1
    checks.append(("no orphan d{} keys not in LENSES",
                   len(orphan_keys) == 0,
                   f"orphans: {sorted(orphan_keys)[:6]}" if orphan_keys else "OK"))
    checks.append(("all items have all lens keys",
                   items_missing_keys == 0,
                   f"{items_missing_keys} items missing keys" if items_missing_keys else "OK"))

    # ── No empty lens data ──────────────────────────────────────────────────
    empty = len(re.findall(r"(\w+):\s*''", items_text))
    checks.append(("no empty lens strings", empty == 0, f"{empty} found"))

    # ── Unescaped apostrophes ───────────────────────────────────────────────
    bad_apos = re.findall(r":\s*'[^'\\]*[a-zA-Z]['][a-zA-Z][^']*'", items_text)
    checks.append(("no unescaped apostrophes in data",
                   len(bad_apos) == 0,
                   f"{len(bad_apos)} found" if bad_apos else "OK"))

    # ── FP_KEYS ─────────────────────────────────────────────────────────────
    fp_m = re.search(r"const FP_KEYS\s*=\s*\[([^\]]+)\]", html)
    fp_keys = re.findall(r"'([^']+)'", fp_m.group(1)) if fp_m else []
    checks.append(("FP_KEYS defined", len(fp_keys) > 0, f"{len(fp_keys)} keys"))

    # ── DARK THEME FORCED ON LOAD ───────────────────────────────────────────
    # Critical: if OS is light mode and dark theme isn't forced, map shows blank
    forces_dark = any([
        "document.documentElement.dataset.theme='dark'" in html,
        'document.documentElement.dataset.theme = "dark"' in html,
        'setAttribute("data-theme","dark")' in html,
        "setAttribute('data-theme','dark')" in html,
    ])
    has_pcs_light = bool(re.search(r'prefers-color-scheme:\s*light', html))
    checks.append(("dark theme forced on load (prevents light-mode blank map)",
                   forces_dark or not has_pcs_light,
                   "MISSING: add document.documentElement.dataset.theme='dark'; to init()"
                   if not forces_dark and has_pcs_light else "OK"))

    # ── Map SVG elements ────────────────────────────────────────────────────
    checks.append(("SVG id=wsvg present", 'id="wsvg"' in html, ""))
    checks.append(("map-layer group present", 'id="map-layer"' in html, ""))
    checks.append(("mark-layer group present", 'id="mark-layer"' in html, ""))
    checks.append(("window._proj assigned", "window._proj=" in html or "window._proj =" in html, ""))

    # ── CDNs ────────────────────────────────────────────────────────────────
    checks.append(("D3 from cdn.jsdelivr.net", "cdn.jsdelivr.net" in html and "d3" in html, ""))
    checks.append(("TopoJSON from cdn.jsdelivr.net", "cdn.jsdelivr.net" in html and "topojson" in html, ""))

    # ── Item coordinates ────────────────────────────────────────────────────
    lat_count = len(re.findall(r"\blat:\s*-?\d", items_text))
    lon_count = len(re.findall(r"\blon:\s*-?\d", items_text))
    checks.append(("items have lat: coordinates",
                   lat_count >= item_count * 0.9, f"{lat_count}/{item_count} items"))
    checks.append(("items have lon: coordinates",
                   lon_count >= item_count * 0.9, f"{lon_count}/{item_count} items"))

    # ── Herstory ────────────────────────────────────────────────────────────
    checks.append(("herstory #c060a0 colour", "#c060a0" in html, ""))
    checks.append(("herstory ♀ Herstory label", "♀ Herstory" in html, ""))
    checks.append(("WOMEN object exists", "const WOMEN" in html, ""))
    women_entries = len(re.findall(r"nm:\s*'", html))
    checks.append(("WOMEN >= 5 entries", women_entries >= 5, f"found {women_entries}"))

    # ── No civilitas leak ───────────────────────────────────────────────────
    civ = len(re.findall(r'\bcivilizat', html, re.IGNORECASE))
    checks.append(("no civilitas text leaked", civ == 0, f"{civ} hits" if civ else ""))

    # ── Colour values ───────────────────────────────────────────────────────
    checks.append(("dark bg #02040a present", "#02040a" in html, ""))
    checks.append(("amber #e89820 present", "#e89820" in html, ""))
    checks.append(("amber-b #f0b040 present", "#f0b040" in html, ""))

    # ── Modes ───────────────────────────────────────────────────────────────
    checks.append(("mode threads/chains", "thread" in html.lower() or "chain" in html.lower(), ""))
    checks.append(("mode compare", "compare" in html.lower(), ""))
    checks.append(("mode what-if", "whatif" in html.lower() or "what-if" in html.lower(), ""))
    checks.append(("mode heritage/address", "heritage" in html.lower() or "address" in html.lower(), ""))
    checks.append(("mode herstory", "toggleHerstory" in html, ""))

    # ── Structure ───────────────────────────────────────────────────────────
    checks.append(("back link ../index.html", "../index.html" in html, ""))
    checks.append(("skip link", "skip-link" in html, ""))
    checks.append(("JSON-LD", "application/ld+json" in html, ""))
    checks.append(("init() on DOMContentLoaded", "DOMContentLoaded" in html and "init()" in html, ""))

    # ── Transmissions and Heritage ──────────────────────────────────────────
    tx_count = len(re.findall(r"\{from:", html))
    checks.append(("TRANSMISSIONS >= 10", tx_count >= 10, f"found {tx_count}"))
    checks.append(("HERITAGE_REGIONS defined",
                   "HERITAGE_REGIONS" in html or "COSMIC_ADDRESS" in html, ""))

    # ── Print ────────────────────────────────────────────────────────────────
    fails = []
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            fails.append(name)
        suffix = f"  [{detail}]" if detail else ""
        print(f"{status:<4}  {name}{suffix}")

    print()
    print(f"Items:{item_count}  Lenses:{lens_count}  WOMEN:{women_entries}  "
          f"TX:{tx_count}  OrphanKeys:{len(orphan_keys)}")
    print()

    if not fails:
        print("VERDICT: ELIGIBLE FOR GO-LIVE")
        _record_validation(atlas, item_count, lens_count)
        sys.exit(0)
    else:
        print(f"VERDICT: NOT ELIGIBLE — {len(fails)} failures:")
        for f in fails:
            print(f"  ✗ {f}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    validate(sys.argv[1])
