#!/usr/bin/env python3
"""
Pangea Atlas Validator v3
=========================
Runs the full CLAUDE.md Section 18 checklist against an atlas file.
Exits 0 if ELIGIBLE FOR GO-LIVE, exits 1 if NOT ELIGIBLE.

Also validates the Pangea homepage (index.html) when --homepage is used.

Usage:
  python3 pangea_validate.py ATLAS_NAME
  python3 pangea_validate.py ATLAS_NAME --force   (skip cached result)
  python3 pangea_validate.py --homepage            (validate homepage only)
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


def _count_unescaped_apostrophes(items_text):
    """Count unescaped apostrophes inside single-quoted data strings.

    Walks through lines that look like data (contain key:'value' patterns)
    and tracks string state to find apostrophes that prematurely close strings.
    Returns the count of likely-broken apostrophes.
    """
    count = 0
    for line in items_text.split('\n'):
        # Only check lines that contain data values (key:'...')
        if ":'" not in line:
            continue
        in_string = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '\\' and in_string and i + 1 < len(line):
                i += 2  # skip escaped character
                continue
            if c == "'":
                if not in_string:
                    in_string = True
                else:
                    # Check if this looks like a premature string close
                    # (followed by a lowercase letter = likely contraction/possessive)
                    rest = line[i + 1:i + 3]
                    if rest and rest[0].isalpha() and rest[0].islower():
                        count += 1
                        # Stay in string mode (the real close is later)
                    elif rest and rest[0] == ' ' and len(rest) > 1 and rest[1].islower():
                        count += 1
                    else:
                        in_string = False
            i += 1
    return count


def _check_js_parse(html, atlas):
    """Run the inline <script> block through Node.js vm.Script to catch syntax errors."""
    # Extract the main inline script block (skip JSON-LD)
    lines = html.split('\n')
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if line.strip() == '<script>' and start == -1 and i > 100:
            start = i
        if start > 0 and line.strip() == '</script>' and i > start + 100:
            end = i
            break

    if start == -1 or end == -1:
        return False, "could not find inline <script> block"

    script = '\n'.join(lines[start + 1:end])

    # Write to temp file and parse with Node.js
    tmp_path = Path(f"/tmp/_pangea_validate_{atlas}.js")
    tmp_path.write_text(script, encoding='utf-8')

    result = subprocess.run(
        ["node", "-e", f"""
const vm = require('vm');
const fs = require('fs');
const script = fs.readFileSync('{tmp_path}', 'utf8');
try {{
    new vm.Script(script, {{filename: '{atlas}.js'}});
    process.exit(0);
}} catch(e) {{
    const lineNum = e.stack?.match(/:(\d+)/)?.[1];
    const fileLine = lineNum ? parseInt(lineNum) + {start + 1} : -1;
    console.error('line ' + fileLine + ': ' + e.message);
    process.exit(1);
}}
"""],
        capture_output=True, text=True, timeout=15
    )

    try:
        tmp_path.unlink()
    except OSError:
        pass

    if result.returncode == 0:
        return True, "OK"
    else:
        detail = result.stderr.strip() or result.stdout.strip() or "parse failed"
        return False, detail


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

    # ══════════════════════════════════════════════════════════════════════════
    # CRITICAL: JavaScript parse check (catches ALL syntax errors at once)
    # ══════════════════════════════════════════════════════════════════════════
    js_parse_ok, js_parse_detail = _check_js_parse(html, atlas)
    checks.append(("JavaScript parses without errors", js_parse_ok, js_parse_detail))

    # ══════════════════════════════════════════════════════════════════════════
    # Structural integrity checks — full-file scans (no data region needed)
    # ══════════════════════════════════════════════════════════════════════════

    # ── Escaped backticks in template literals ─────────────────────────────
    escaped_bt = re.findall(r'return\\`', html)
    checks.append(("no escaped backticks in template literals",
                   len(escaped_bt) == 0,
                   f"{len(escaped_bt)} found (return\\` should be return `)" if escaped_bt else "OK"))

    # ── Missing commas between ITEMS array elements ────────────────────────
    missing_comma = re.findall(r"\}\}\n\{id:", html)
    checks.append(("no missing commas between ITEMS",
                   len(missing_comma) == 0,
                   f"{len(missing_comma)} found (}} not followed by comma before next item)" if missing_comma else "OK"))

    # ── WOMEN object closed correctly ──────────────────────────────────────
    women_close = re.search(r'const WOMEN\s*=\s*\{', html)
    if women_close:
        # Find the matching close — should be }; not ];
        women_text = html[women_close.start():]
        bad_women_close = bool(re.search(r'\]\s*;\s*\n\s*let\s+year\b', women_text))
        checks.append(("WOMEN object closed with }; not ];",
                       not bad_women_close,
                       "found ]; closing WOMEN — should be };" if bad_women_close else "OK"))

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

    # ── Duplicate item IDs ───────────────────────────────────────────────────
    all_item_ids = re.findall(r"^\{id:'([^']+)'", items_region, re.MULTILINE)
    seen_ids = set()
    duplicate_ids = []
    for iid in all_item_ids:
        if iid in seen_ids:
            duplicate_ids.append(iid)
        seen_ids.add(iid)
    checks.append(("no duplicate item IDs",
                   len(duplicate_ids) == 0,
                   f"duplicates: {duplicate_ids}" if duplicate_ids else "OK"))

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

    # ── Double-escaped apostrophes in data strings ────────────────────────
    # Only scan data regions (ITEMS + TRANSMISSIONS + WOMEN) to avoid
    # false positives from legitimate JS like replace(/'/g,"\\'")
    data_regions = items_text
    tx_block_m = re.search(r'const TRANSMISSIONS\s*=\s*\[[\s\S]*?\];', html)
    if tx_block_m:
        data_regions += tx_block_m.group(0)
    women_block_m = re.search(r'const WOMEN\s*=\s*\{[\s\S]*?\};', html)
    if women_block_m:
        data_regions += women_block_m.group(0)
    double_esc = re.findall(r"\\\\'", data_regions)
    checks.append(("no double-escaped apostrophes in data",
                   len(double_esc) == 0,
                   f"{len(double_esc)} found (\\\\' should be \\')" if double_esc else "OK"))

    # ── Unescaped apostrophes in data strings ───────────────────────────────
    # The JS parse check above catches these too, but this gives a specific
    # count and helps agents fix them. Scans all single-quoted data values
    # in the ITEMS region for apostrophes that would prematurely close the string.
    bad_apos_count = _count_unescaped_apostrophes(items_text)
    checks.append(("no unescaped apostrophes in data",
                   bad_apos_count == 0,
                   f"{bad_apos_count} found" if bad_apos_count else "OK"))

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

    # ── Fingerprint SHORT labels match FP_LABELS ──────────────────────────
    fp_labels_m = re.search(r"const FP_LABELS\s*=\s*\[([^\]]+)\]", html)
    fp_labels = re.findall(r"'([^']+)'", fp_labels_m.group(1)) if fp_labels_m else []
    short_m = re.search(r"const SHORT\s*=\s*\[([^\]]+)\]", html)
    short_labels = re.findall(r"'([^']+)'", short_m.group(1)) if short_m else []
    if fp_labels and short_labels:
        fp_short_match = short_labels == fp_labels
        checks.append(("fingerprint SHORT labels match FP_LABELS",
                       fp_short_match,
                       f"SHORT={short_labels} vs FP_LABELS={fp_labels}" if not fp_short_match else "OK"))

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

    # ── THEME: system default with light/dark support ────────────────────────
    has_pcs_light = bool(re.search(r'prefers-color-scheme:\s*light', html))
    has_toggle = 'toggleTheme' in html
    checks.append(("theme supports system default (prefers-color-scheme + toggle)",
                   has_pcs_light and has_toggle,
                   "MISSING: @media prefers-color-scheme light block and toggleTheme function"
                   if not (has_pcs_light and has_toggle) else "OK"))

    # ── THEME: must NOT force data-theme on first load (system default) ────
    # The theme IIFE's else branch must not set document.documentElement.dataset.theme
    # when no saved preference exists — CSS @media prefers-color-scheme handles it.
    forces_theme = bool(re.search(
        r'else\s*\{[^}]*document\.documentElement\.dataset\.theme\s*=\s*sys',
        html))
    checks.append(("theme IIFE does not force data-theme on first load",
                   not forces_theme,
                   "FAIL: theme IIFE sets document.documentElement.dataset.theme in else "
                   "branch — remove it so CSS @media prefers-color-scheme handles system default"
                   if forces_theme else "OK"))

    # ── Undefined data constants referenced in functions ────────────────────
    # Detect functions that reference array/object constants (e.g. DIPLOMATIC,
    # CATEGORIES) that are never declared with const/let/var. These cause
    # ReferenceError at runtime, crashing the calling code silently.
    # Extract the main script block for analysis.
    script_lines = html.split('\n')
    script_start = -1
    script_end = -1
    for si, sline in enumerate(script_lines):
        if sline.strip() == '<script>' and si > 100:
            script_start = si
        if script_start > 0 and sline.strip() == '</script>' and si > script_start + 100:
            script_end = si
            break
    if script_start > 0 and script_end > 0:
        script_text = '\n'.join(script_lines[script_start + 1:script_end])
        # Find all UPPER_CASE identifiers used in the script (potential constants)
        used_upper = set(re.findall(r'\b([A-Z][A-Z_]{2,})\b', script_text))
        # Find all declared constants/variables
        declared = set(re.findall(r'(?:const|let|var)\s+([A-Z][A-Z_]{2,})\b', script_text))
        # Known globals/builtins to exclude
        builtins = {'URL', 'JSON', 'SVG', 'CSS', 'DOM', 'NAN', 'SET', 'MAP',
                    'YEAR_MIN', 'YEAR_MAX', 'VB_MIN_W', 'VB_MAX_W',
                    'HTML', 'GET', 'POST', 'IMPORTANT', 'FUTURE', 'AGENTS',
                    'NOTE', 'ALL', 'ACTIVE', 'JUMP', 'MISSING', 'BCE', 'BCE',
                    'DONE', 'CLUSTER', 'RESET', 'ZOOM', 'HERITAGE', 'MARGIN'}
        # Only flag UPPER_CASE names that appear as standalone identifiers
        # (not inside strings) and are used as .filter/.forEach/.map receivers
        undefined_consts = []
        for name in used_upper - declared - builtins:
            # Check if this name is used as a variable (e.g. NAME.filter, NAME.forEach, NAME[)
            if re.search(r'\b' + re.escape(name) + r'\s*[\.\[\(]', script_text):
                # Check if ALL occurrences of NAME.xxx are inside strings.
                # Use per-line check to avoid cross-line false positives.
                has_real_usage = False
                for sline in script_text.split('\n'):
                    if re.search(r'\b' + re.escape(name) + r'\s*[\.\[\(]', sline):
                        # This line uses the name as a variable; check if it's inside a string
                        if not re.search(r"'[^']*" + re.escape(name) + r"[^']*'", sline):
                            has_real_usage = True
                            break
                if has_real_usage:
                    undefined_consts.append(name)
        checks.append(("no undefined data constants referenced in functions",
                       len(undefined_consts) == 0,
                       f"undefined: {sorted(undefined_consts)} — add const declarations"
                       if undefined_consts else "OK"))

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

        if re.search(r'\bwhatifCiv\b', html):
            code_leaks.append("whatifCiv")
        if re.search(r'\bcivPt\b', html):
            code_leaks.append("civPt")

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


def validate_homepage():
    """Validate the Pangea homepage (index.html) for structural integrity.

    Checks for issues that break the card grid layout:
    - Unclosed <a> tags (cause cards to nest inside each other)
    - Mismatched <a> open/close counts
    - Card links pointing to wrong atlas directories
    - Cards with status--live but no <a> link
    - Cards with <a> links but no </a> close
    - Stray </a> tags inside forthcoming cards (no matching open)
    - All live atlas directories actually exist
    """
    p = Path("index.html")
    if not p.exists():
        print("FAIL   index.html not found")
        sys.exit(1)

    html = p.read_text(encoding="utf-8", errors="replace")
    lines = html.split('\n')
    checks = []

    # ── Basic HTML structure ───────────────────────────────────────────────
    a_opens = re.findall(r'<a\s+href="([^"]*)"', html)
    a_closes = html.count('</a>')
    checks.append(("all <a> tags closed",
                   len(a_opens) == a_closes,
                   f"{len(a_opens)} opens vs {a_closes} closes" if len(a_opens) != a_closes else "OK"))

    # ── Per-card validation ────────────────────────────────────────────────
    # Extract cards by tracking div nesting depth from each card-open tag
    unclosed_links = []
    stray_closes = []
    wrong_hrefs = []
    live_no_link = []

    card_starts = list(re.finditer(
        r'<div class="card card--(live|forthcoming)">', html
    ))

    for cs in card_starts:
        card_type = cs.group(1)
        start = cs.start()
        card_line = html[:start].count('\n') + 1

        # Walk forward counting div opens/closes to find the matching </div>
        pos = cs.end()
        depth = 1
        while pos < len(html) and depth > 0:
            next_open = html.find('<div', pos)
            next_close = html.find('</div>', pos)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    pos = next_close + 6
                    break
                pos = next_close + 6

        card_html = html[cs.end():pos]

        # Extract card name
        name_m = re.search(r'<div class="card-name">([^<]+)</div>', card_html)
        card_name = name_m.group(1) if name_m else f"unknown@line{card_line}"

        link_opens = re.findall(r'<a\s+href="([^"]*)"', card_html)
        link_closes = card_html.count('</a>')

        if link_opens and len(link_opens) > link_closes:
            unclosed_links.append(f"{card_name} (line ~{card_line})")

        if not link_opens and link_closes > 0:
            stray_closes.append(f"{card_name} (line ~{card_line})")

        # Check live cards have a link
        if card_type == 'live' and not link_opens:
            live_no_link.append(f"{card_name} (line ~{card_line})")

        # Check link hrefs point to existing directories
        for href in link_opens:
            if href.startswith('#') or href.startswith('http'):
                continue
            expected_dir = href.split('/')[0] if '/' in href else ''
            if expected_dir:
                target = Path(expected_dir)
                if not target.exists():
                    wrong_hrefs.append(f"{card_name} → {href} (dir missing)")

    checks.append(("no unclosed <a> inside cards",
                   len(unclosed_links) == 0,
                   f"unclosed: {unclosed_links}" if unclosed_links else "OK"))

    checks.append(("no stray </a> inside cards",
                   len(stray_closes) == 0,
                   f"stray: {stray_closes}" if stray_closes else "OK"))

    checks.append(("all card hrefs point to existing dirs",
                   len(wrong_hrefs) == 0,
                   f"broken: {wrong_hrefs}" if wrong_hrefs else "OK"))

    if live_no_link:
        checks.append(("all live cards have links",
                       False, f"missing: {live_no_link}"))

    # ── Live atlas directories have index.html ─────────────────────────────
    live_links = []
    for m in re.finditer(
        r'<div class="card card--live">[\s\S]*?<a href="([^"]+)"', html
    ):
        live_links.append(m.group(1))

    missing_files = []
    for href in live_links:
        if not Path(href).exists():
            missing_files.append(href)

    checks.append(("all live atlas links resolve to files",
                   len(missing_files) == 0,
                   f"missing: {missing_files}" if missing_files else "OK"))

    # ── Live atlases in state must have card--live on homepage ─────────────
    state_path = Path("pangea_state.json")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        wrong_status = []
        for atlas_key, info in state.get("atlases", {}).items():
            if not info.get("live"):
                continue
            display_name = info.get("homepage_name", atlas_key.capitalize())
            has_live = bool(re.search(
                rf'card--live.*?{re.escape(display_name)}', html, re.DOTALL
            ))
            if not has_live:
                has_other = "building" if re.search(
                    rf'card--building.*?{re.escape(display_name)}', html, re.DOTALL
                ) else "forthcoming" if re.search(
                    rf'card--forthcoming.*?{re.escape(display_name)}', html, re.DOTALL
                ) else "missing"
                wrong_status.append(f"{atlas_key} ({has_other})")
        checks.append(("all live atlases have card--live on homepage",
                       len(wrong_status) == 0,
                       f"wrong: {wrong_status}" if wrong_status else "OK"))

    # ── Card grid div nesting ──────────────────────────────────────────────
    # Quick check: count card-grid opens/closes
    grid_opens = html.count('class="card-grid"')
    grid_div_closes = 0
    # Each card-grid should be properly closed
    checks.append(("card-grid sections present", grid_opens > 0, f"found {grid_opens}"))

    # ── Print results ──────────────────────────────────────────────────────
    fails = []
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            fails.append(name)
        suffix = f"  [{detail}]" if detail else ""
        print(f"{status:<4}  {name}{suffix}")

    print()
    if not fails:
        print("HOMEPAGE: OK")
        sys.exit(0)
    else:
        print(f"HOMEPAGE: {len(fails)} failures:")
        for f in fails:
            print(f"  ✗ {f}")
        sys.exit(1)


if __name__ == "__main__":
    if "--homepage" in sys.argv:
        validate_homepage()
    else:
        force = "--force" in sys.argv
        args = [a for a in sys.argv[1:] if a != "--force"]
        if len(args) != 1:
            print(__doc__)
            sys.exit(1)
        validate(args[0], force=force)
