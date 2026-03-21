#!/usr/bin/env python3
"""
Pangea Atlas Validator v2
=========================
Runs the full CLAUDE.md Section 18 checklist against an atlas file.
Exits 0 if ELIGIBLE FOR GO-LIVE, exits 1 if NOT ELIGIBLE.

Usage:
  python3 pangea_validate.py ATLAS_NAME
  python3 pangea_validate.py ATLAS_NAME --force   (skip cached result)
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


def _extract_item_ids(items_text):
    """Extract all item IDs from the ITEMS block."""
    return set(re.findall(r"^\{id:'([^']+)'", items_text, re.MULTILINE))


def _extract_women_keys(html):
    """Extract item-ID keys from the WOMEN object (both 'key':[ and key:[ formats)."""
    women_block = re.search(r'const WOMEN\s*=\s*\{([\s\S]*?)\};', html)
    if not women_block:
        return []
    text = women_block.group(1)
    return re.findall(r"['\"]?(\w+)['\"]?\s*:\s*\[", text)


def _count_women_persons(html):
    """Count person entries inside the WOMEN object only (not the whole file)."""
    women_block = re.search(r'const WOMEN\s*=\s*\{([\s\S]*?)\};', html)
    if not women_block:
        return 0
    return len(re.findall(r"\{nm:", women_block.group(1)))


def _extract_heritage_item_refs(html):
    """Extract item-ID references from HERITAGE_REGIONS values."""
    hr_block = re.search(r'const HERITAGE_REGIONS\s*=\s*\{([\s\S]*?)\};', html)
    if not hr_block:
        return set()
    refs = set()
    # Find all array values: ['id1','id2',...]
    for arr_match in re.finditer(r":\s*\[([^\]]+)\]", hr_block.group(1)):
        refs.update(re.findall(r"'([^']+)'", arr_match.group(1)))
    return refs


def validate(atlas, force=False):
    p = Path(f"{atlas}/index.html")
    if not p.exists():
        print(f"FAIL   file not found: {atlas}/index.html")
        print("\nVERDICT: NOT ELIGIBLE")
        sys.exit(1)

    # ── Skip if already validated at current commit ────────────────────────
    if not force:
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
    warnings = []  # non-blocking issues

    # ── Item count (inside ITEMS block only) ────────────────────────────────
    # Find the region between 'const ITEMS=[' and 'const TRANSMISSIONS'
    # (or next const declaration) to avoid matching LENSES entries
    items_start_m = re.search(r'const ITEMS\s*=\s*\[', html)
    items_end_m = re.search(r'const TRANSMISSIONS\s*=', html)
    if items_start_m and items_end_m:
        items_region = html[items_start_m.end():items_end_m.start()]
    elif items_start_m:
        items_region = html[items_start_m.end():]
    else:
        items_region = ""
    item_count = len(re.findall(r"^\{id:'", items_region, re.MULTILINE))
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

    # ── Item d{} keys match lens IDs ────────────────────────────────────────
    # Find the first ]; that appears after all items have been seen
    items_text = items_region
    for m in re.finditer(r'^\];', items_region, re.MULTILINE):
        candidate = items_region[:m.start()]
        count = len(re.findall(r"^\{id:'", candidate, re.MULTILINE))
        if count >= item_count:
            items_text = candidate
            break
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

    # ── FP_KEYS match item fp{} keys ─────────────────────────────────────
    if fp_keys:
        fp_key_set = set(fp_keys)
        item_fp_blocks = re.findall(r"fp:\{([^}]+)\}", items_text)
        fp_mismatches = 0
        for fp_block in item_fp_blocks:
            fp_item_keys = set(re.findall(r"(\w+):", fp_block))
            if fp_item_keys != fp_key_set:
                fp_mismatches += 1
        checks.append(("FP_KEYS match item fp{} keys",
                       fp_mismatches == 0,
                       f"{fp_mismatches} items have wrong fp keys" if fp_mismatches else "OK"))

    # ══════════════════════════════════════════════════════════════════════════
    # Cross-reference validation
    # ══════════════════════════════════════════════════════════════════════════

    item_ids = _extract_item_ids(items_text)

    # ── conns[] resolve to real item IDs ─────────────────────────────────────
    all_conn_ids = set()
    for c_match in re.finditer(r"conns:\s*\[([^\]]*)\]", items_text):
        all_conn_ids.update(re.findall(r"'([^']+)'", c_match.group(1)))
    broken_conns = all_conn_ids - item_ids
    checks.append(("all conns[] reference real item IDs",
                   len(broken_conns) == 0,
                   f"{len(broken_conns)} broken: {sorted(broken_conns)[:5]}" if broken_conns else "OK"))

    # ── TRANSMISSIONS from/to resolve to real item IDs ───────────────────────
    tx_block = re.search(r'const TRANSMISSIONS\s*=\s*\[[\s\S]*?\];', html)
    tx_text = tx_block.group(0) if tx_block else ""
    tx_froms = set(re.findall(r"from:\s*'([^']+)'", tx_text))
    tx_tos = set(re.findall(r"to:\s*'([^']+)'", tx_text))
    broken_tx = (tx_froms | tx_tos) - item_ids
    checks.append(("all TRANSMISSIONS from/to reference real items",
                   len(broken_tx) == 0,
                   f"{len(broken_tx)} broken: {sorted(broken_tx)[:5]}" if broken_tx else "OK"))

    # ── WOMEN keys resolve to real item IDs ──────────────────────────────────
    women_keys = _extract_women_keys(html)
    broken_women = set(women_keys) - item_ids
    checks.append(("all WOMEN keys reference real item IDs",
                   len(broken_women) == 0,
                   f"{len(broken_women)} broken: {sorted(broken_women)[:5]}" if broken_women else "OK"))

    # ── HERITAGE_REGIONS values resolve to real item IDs ─────────────────────
    hr_refs = _extract_heritage_item_refs(html)
    broken_hr = hr_refs - item_ids
    checks.append(("all HERITAGE_REGIONS values reference real items",
                   len(broken_hr) == 0,
                   f"{len(broken_hr)} broken: {sorted(broken_hr)[:5]}" if broken_hr else "OK"))

    # ══════════════════════════════════════════════════════════════════════════
    # NEW: WOMEN data quality (count within WOMEN object, not whole file)
    # ══════════════════════════════════════════════════════════════════════════
    women_person_count = _count_women_persons(html)
    checks.append(("WOMEN has person entries (inside WOMEN object)",
                   women_person_count >= 5,
                   f"found {women_person_count}"))

    # ══════════════════════════════════════════════════════════════════════════
    # NEW: Drift spec compliance
    # ══════════════════════════════════════════════════════════════════════════

    # ── Drift 1: hover-label-layer SVG group ─────────────────────────────────
    checks.append(("Drift 1: hover-label-layer SVG group",
                   'id="hover-label-layer"' in html, ""))

    # ── Drift 2: inactive items fully hidden (opacity 0, not 0.06) ────────
    # Check for the old 0.06 ghost-dot opacity in the opacity formula
    has_006_ghost = bool(re.search(r'herstory\s*\?\s*0\.15\s*:\s*0\.06', html))
    checks.append(("Drift 2: inactive items hidden (no 0.06 ghost dots)",
                   not has_006_ghost,
                   "found 0.06 ghost opacity — should be 0" if has_006_ghost else "OK"))

    # ── Drift 3: herstory filter (items without WOMEN fully hidden) ───────
    # Check that the herstory && !womenCount branch uses 0, not 0.35
    has_035_herstory = bool(re.search(r'herstory\s*&&\s*!womenCount.*?0\.35', html))
    checks.append(("Drift 3: herstory filter hides non-WOMEN items (no 0.35)",
                   not has_035_herstory,
                   "found 0.35 dimming — should be 0 (filter, not overlay)" if has_035_herstory else "OK"))

    # ── Drift 4: Herstory dedicated panel ────────────────────────────────────
    checks.append(("Drift 4: Herstory dedicated panel (hs-panel-hdr)",
                   "hs-panel-hdr" in html, ""))

    # ── About modal matches atlas name ────────────────────────────────────
    about_label = re.search(r'aria-label="About\s+([^"]+)"', html)
    if about_label and atlas != "civilitas":
        about_name = about_label.group(1).lower()
        checks.append(("about modal matches atlas",
                       atlas.lower() in about_name or about_name in atlas.lower(),
                       f"aria-label says '{about_label.group(1)}', atlas is '{atlas}'"))

    # ══════════════════════════════════════════════════════════════════════════
    # NEW: Code-level naming leaks (not content — function/variable names)
    # ══════════════════════════════════════════════════════════════════════════

    # ── DARK THEME FORCED ON LOAD ───────────────────────────────────────────
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

    # ── CDNs (Drift 5) ──────────────────────────────────────────────────────
    checks.append(("D3 from cdn.jsdelivr.net", "cdn.jsdelivr.net" in html and "d3" in html, ""))
    checks.append(("TopoJSON from cdn.jsdelivr.net", "cdn.jsdelivr.net" in html and "topojson" in html, ""))
    checks.append(("Drift 5: no cdnjs.cloudflare.com",
                   "cdnjs.cloudflare.com" not in html, ""))

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

    # ── No civilitas leak ───────────────────────────────────────────────────
    # Skip for civilitas itself (it's the reference atlas)
    if atlas != "civilitas":
        # Code-level leaks: function/variable names that should have been renamed
        code_leaks = []
        if re.search(r'\bnavigateToCiv\b', html):
            code_leaks.append("navigateToCiv")
        if re.search(r'\bcivClick\b', html):
            code_leaks.append("civClick")
        if re.search(r'\bCIVS\b', html):
            code_leaks.append("CIVS")
        # Check for "Civilitas" as proper noun in UI strings (not in content data)
        # Look in header, modal, share title — not inside item data strings
        logo_text = re.search(r'class="logo-t">([^<]+)<', html)
        if logo_text and "CIVILITAS" in logo_text.group(1):
            code_leaks.append("CIVILITAS in logo")
        share_title = re.search(r"shareTitle\s*=\s*'([^']+)'", html)
        if share_title and "Civilitas" in share_title.group(1):
            code_leaks.append("Civilitas in shareTitle")

        checks.append(("no civilitas code leaks",
                       len(code_leaks) == 0,
                       f"found: {code_leaks}" if code_leaks else "OK"))

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
    init_booted = (
        ("DOMContentLoaded" in html and "init()" in html) or
        ("addEventListener('load',init)" in html) or
        ('addEventListener("load",init)' in html) or
        ("addEventListener('load', init)" in html)
    )
    checks.append(("init() called on page load", init_booted, ""))

    # ── Transmissions and Heritage ──────────────────────────────────────────
    tx_count = len(re.findall(r"\{from:", html))
    checks.append(("TRANSMISSIONS >= 10", tx_count >= 10, f"found {tx_count}"))
    checks.append(("HERITAGE_REGIONS defined",
                   "HERITAGE_REGIONS" in html or "COSMIC_ADDRESS" in html, ""))

    # ══════════════════════════════════════════════════════════════════════════
    # NEW: Overview and conns fields exist on items
    # ══════════════════════════════════════════════════════════════════════════
    overview_count = len(re.findall(r"\boverview:\s*'", items_text))
    checks.append(("all items have overview field",
                   overview_count >= item_count,
                   f"{overview_count}/{item_count}" if overview_count < item_count else "OK"))

    conns_count = len(re.findall(r"\bconns:\s*\[", items_text))
    checks.append(("all items have conns field",
                   conns_count >= item_count,
                   f"{conns_count}/{item_count}" if conns_count < item_count else "OK"))

    # ── Lens content sentence count (warning, not blocking) ───────────────
    # CLAUDE.md requires 2-4 sentences per d{} value
    short_lens_count = 0
    for d in d_blocks:
        for val_match in re.finditer(r"\w+:'((?:[^'\\]|\\.)+)'", d):
            val = val_match.group(1)
            sentences = len(re.findall(r'[.!?]\s+[A-Z]', val)) + 1
            if sentences < 2 and len(val) > 10:
                short_lens_count += 1
                break  # count per item, not per lens
    if short_lens_count > 0:
        warnings.append(f"lens sentence count: {short_lens_count}/{item_count} items have lens entries under 2 sentences")

    # ══════════════════════════════════════════════════════════════════════════
    # Print results
    # ══════════════════════════════════════════════════════════════════════════
    fails = []
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            fails.append(name)
        suffix = f"  [{detail}]" if detail else ""
        print(f"{status:<4}  {name}{suffix}")

    # Print warnings (non-blocking)
    for w in warnings:
        print(f"WARN  {w}")

    print()
    print(f"Items:{item_count}  Lenses:{lens_count}  WOMEN:{women_person_count}  "
          f"TX:{tx_count}  OrphanKeys:{len(orphan_keys)}  "
          f"BrokenConns:{len(broken_conns)}  BrokenTX:{len(broken_tx)}")
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
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    validate(args[0], force=force)
