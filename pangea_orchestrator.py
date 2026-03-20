#!/usr/bin/env python3
"""
Pangea Project Orchestrator v3
================================
Usage:
  python3 pangea_orchestrator.py                     — print next action as JSON
  python3 pangea_orchestrator.py advance ATLAS PHASE — mark shell/constants/modes phase done
  python3 pangea_orchestrator.py item_done ATLAS     — increment item count by 1
  python3 pangea_orchestrator.py golive ATLAS        — mark atlas live
  python3 pangea_orchestrator.py status              — human-readable progress report
  python3 pangea_orchestrator.py verify              — check state file integrity
"""

import json
import os
import subprocess
import sys
from pathlib import Path

STATE_FILE = Path("pangea_state.json")

# Phases in order — DATA is a single phase covering all item writing
PHASES_ORDERED = [
    "1A", "1B", "1C", "1D", "1E", "1F",
    "DATA",
    "3",
    "4A", "4B", "4C",
    "5",
    "6",
    "DONE"
]

SKIP_IF_WORLD_MAP = {"1E", "4A", "4B", "4C"}


def load_state():
    if not STATE_FILE.exists():
        print("ERROR: pangea_state.json not found.", file=sys.stderr)
        sys.exit(1)
    return json.loads(STATE_FILE.read_text())


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))


def self_invoke():
    """Re-exec the orchestrator with no args so output chains automatically."""
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, __file__])


def count_items(atlas):
    p = Path(f"{atlas}/index.html")
    if not p.exists():
        return 0
    result = subprocess.run(
        ["grep", "-c", "^{id:'", str(p)],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def next_phase(current, map_type="world"):
    try:
        i = PHASES_ORDERED.index(current)
    except ValueError:
        return PHASES_ORDERED[0]
    for j in range(i + 1, len(PHASES_ORDERED)):
        candidate = PHASES_ORDERED[j]
        if map_type == "world" and candidate in SKIP_IF_WORLD_MAP:
            continue
        return candidate
    return "DONE"


def generate_new_atlas(state):
    existing = sorted(state["atlases"].keys())
    print("=" * 60)
    print("QUEUE EMPTY - GENERATE A NEW ATLAS NOW")
    print("=" * 60)
    print(f"All {len(existing)} atlases are built or queued.")
    print()
    print("You are Claude. Use your knowledge to invent ONE new atlas.")
    print("It must not overlap any existing atlas.")
    print("It must be global, span 5000+ years, have a Herstory angle.")
    print()
    print("Existing keys:", ", ".join(existing[:15]), "... (and more)")
    print()
    print("When you have an idea, register it with:")
    cmd = "python3 pangea_orchestrator.py new_atlas KEY NAME SECTION ICON TAGLINE TAGS"
    print(" ", cmd)
    print()
    print("Where:")
    print("  KEY     = lowercase latin word, no spaces")
    print("  NAME    = display name")
    print("  SECTION = roman numeral I through XII")
    print("  ICON    = single emoji")
    print("  TAGLINE = quoted sentence max 12 words")
    print("  TAGS    = quoted comma-separated list e.g. 'Tag1,Tag2,Tag3'")
    print()
    print("Run that command now. The loop will continue automatically.")


def get_next_action(state):
    queue = state.get("queue", [])
    if not queue:
        print("Queue empty — generating new atlas idea via Claude API...")
        generate_new_atlas(state)
        return None

    atlas = queue[0]
    info = state["atlases"].get(atlas)

    if info is None:
        return {"action": "ERROR", "message": f"'{atlas}' in queue but not in atlases.", "atlas": atlas}

    if info.get("live"):
        return {"action": "CLEANUP", "atlas": atlas}

    phase = info.get("phase", "1A")

    if phase == "DONE" and not info.get("live"):
        return {
            "action": "GO_LIVE",
            "atlas": atlas,
            "items": count_items(atlas),
            "target": info.get("target", 100),
            "section": info.get("section", "?"),
            "homepage_name": info.get("homepage_name", atlas.capitalize())
        }

    # Sync item count
    real_count = count_items(atlas)
    if real_count != info.get("items", 0):
        info["items"] = real_count
        state["atlases"][atlas] = info
        save_state(state)

    target = info.get("target", 100)

    # DATA phase: emit WRITE_ITEM until target reached
    if phase == "DATA":
        if real_count >= target:
            # All items written — auto-advance to Phase 3
            info["phase"] = "3"
            state["atlases"][atlas] = info
            save_state(state)
            return {
                "action": "EXECUTE_PHASE",
                "atlas": atlas,
                "phase": "3",
                "items": real_count,
                "target": target,
                "map": info.get("map", "world")
            }
        n = real_count + 1
        # Print imperative directly so agent has no decision gap
        print(
            f"WRITE_ITEM {n}/{target} for {atlas}. ONE item only.\n"
            f"1. Append ONE item to the ITEMS array in {atlas}/index.html\n"
            f"2. grep -c '^{{id:\'' {atlas}/index.html  →  must equal {n}\n"
            f"3. git add {atlas}/index.html && git commit -m '{atlas}: item {n}/{target}'\n"
            f"4. python3 pangea_orchestrator.py item_done {atlas}"
        )
        return None

    return {
        "action": "EXECUTE_PHASE",
        "atlas": atlas,
        "phase": phase,
        "items": real_count,
        "target": target,
        "map": info.get("map", "world"),
        "file_exists": Path(f"{atlas}/index.html").exists()
    }


def cmd_advance(atlas, completed_phase):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    real_count = count_items(atlas)
    info["items"] = real_count
    info["phase"] = next_phase(completed_phase, info.get("map", "world"))
    state["atlases"][atlas] = info
    state.setdefault("session_log", []).append({
        "atlas": atlas, "phase_done": completed_phase,
        "phase_next": info["phase"], "items": real_count
    })
    save_state(state)
    print(json.dumps({"status": "advanced", "atlas": atlas,
                      "phase_done": completed_phase, "phase_next": info["phase"],
                      "items": real_count}))
    self_invoke()


def cmd_item_done(atlas):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    real_count = count_items(atlas)
    prev_count = info.get("items", 0)
    target = info.get("target", 100)

    # HARD CHECK: must have increased by exactly 1
    added = real_count - prev_count
    if added == 0:
        print(f"ERROR: No new item detected. Count is still {real_count}.")
        print(f"You must write ONE item to {atlas}/index.html before calling item_done.")
        print(f"The item must start with {{id:\' at the beginning of a line.")
        print(f"Write the item now, then run: python3 pangea_orchestrator.py item_done {atlas}")
        sys.exit(1)
    if added > 1:
        print(f"VIOLATION: {added} items were written at once. Only 1 is permitted per call.")
        print(f"Count went from {prev_count} to {real_count}.")
        print(f"This is not allowed. The instructions say ONE item per commit.")
        print(f"State has been recorded at {real_count}. Next call must add exactly 1 more.")

    info["items"] = real_count
    remaining = target - real_count

    if remaining <= 0:
        print(f"ITEMS COMPLETE: {real_count}/{target}. Auto-advancing to Phase 3.")
        info["phase"] = next_phase("DATA", info.get("map", "world"))
        state["atlases"][atlas] = info
        save_state(state)
        self_invoke()
    else:
        state["atlases"][atlas] = info
        save_state(state)
        n = real_count + 1
        print(
            f"item_recorded {real_count}/{target}. {remaining} remaining.\n"
            f"NOW WRITE ITEM {n}. ONE item only. One. Not two. Not ten. One.\n"
            f"Append to ITEMS array in {atlas}/index.html.\n"
            f"Verify: grep -c '^{{id:\'' {atlas}/index.html must equal {n}.\n"
            f"Commit: git add {atlas}/index.html && git commit -m '{atlas}: item {n}/{target}'\n"
            f"Then run: python3 pangea_orchestrator.py item_done {atlas}"
        )


def cmd_golive(atlas):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    info["live"] = True
    info["phase"] = "DONE"
    info["items"] = count_items(atlas)
    state["atlases"][atlas] = info
    if atlas in state.get("queue", []):
        state["queue"].remove(atlas)
    if atlas not in state.get("completed", []):
        state.setdefault("completed", []).append(atlas)
    state.setdefault("session_log", []).append(
        {"atlas": atlas, "phase_done": "GO_LIVE", "items": info["items"]}
    )
    save_state(state)

    # Update index.html: flip card--forthcoming → card--live
    display_name = info.get("homepage_name", atlas.capitalize())
    index_path = Path("index.html")
    index_updated = False
    if index_path.exists():
        html = index_path.read_text(encoding="utf-8")
        html, index_updated = update_index_card_to_live(html, atlas, display_name)
        if index_updated:
            # Also add to JSON-LD hasPart if not already there
            hasPart_entry = f'{{"@type":"Dataset","name":"{display_name}","url":"https://polyglyphanalytica.github.io/pangea/{atlas}/"}}' 
            if hasPart_entry not in html and '"hasPart"' in html:
                html = html.replace(
                    '"hasPart":[',
                    f'"hasPart":[{hasPart_entry},',
                    1
                )
            index_path.write_text(html, encoding="utf-8")
            subprocess.run(["git", "add", "index.html"], capture_output=True)
        subprocess.run(["git", "add", f"{atlas}/index.html"], capture_output=True)
        subprocess.run(["git", "commit", "-m", f"{atlas}: go-live — homepage activated"],
                       capture_output=True)

    print(json.dumps({"status": "live", "atlas": atlas, "items": info["items"],
                      "homepage_updated": index_updated}))
    self_invoke()


def cmd_status():
    state = load_state()
    completed = state.get("completed", [])
    queue = state.get("queue", [])
    total = len(state["atlases"])
    print(f"\n{'='*50}")
    print(f"  PANGEA PROJECT STATUS")
    print(f"{'='*50}")
    print(f"  Total:     {total}")
    print(f"  Live:      {len(completed)}")
    print(f"  Remaining: {len(queue)}")
    print(f"  Progress:  {len(completed)}/{total} ({100*len(completed)//total}%)")
    if queue:
        a = queue[0]
        info = state["atlases"].get(a, {})
        n = count_items(a)
        t = info.get("target", 100)
        print(f"\n  Next: {a}  phase={info.get('phase','?')}  items={n}/{t}")
        bar = int(30 * n / t) if t else 0
        print(f"  [{'█'*bar}{'░'*(30-bar)}] {n}/{t}")
    print(f"\n  Queue preview:")
    for a in queue[:10]:
        info = state["atlases"].get(a, {})
        n = count_items(a)
        print(f"    {a:<20} phase={info.get('phase','?'):<6} {n}/{info.get('target',100)}")
    print()


def cmd_verify():
    state = load_state()
    errors = []
    queue = state.get("queue", [])
    seen = set()
    for a in queue:
        if a in seen:
            errors.append(f"DUPLICATE: {a}")
        seen.add(a)
        if a not in state["atlases"]:
            errors.append(f"In queue but missing from atlases: {a}")
    for a in state.get("completed", []):
        if a not in state["atlases"]:
            errors.append(f"In completed but missing from atlases: {a}")
    print(f"Atlases: {len(state['atlases'])}  Queue: {len(set(queue))}  "
          f"Completed: {len(state.get('completed',[]))}  "
          f"Total: {len(set(queue)) + len(state.get('completed',[]))}")
    if errors:
        print(f"\nERRORS:")
        for e in errors: print(f"  {e}")
        sys.exit(1)
    else:
        print("OK — no errors.")



# ── Roman numeral → section ID map ──────────────────────────────────────────
SECTION_NUM = {
    "I":"1","II":"2","III":"3","IV":"4","V":"5","VI":"6",
    "VII":"7","VIII":"8","IX":"9","X":"10","XI":"11","XII":"12"
}


def insert_card_into_section(html, section_roman, card_html):
    """Insert a forthcoming card into the correct section grid in index.html.
    Falls back to inserting before the footer if section not found."""
    sec_id = SECTION_NUM.get(section_roman.upper(), "")
    if sec_id:
        # Find the section and insert before its closing </div>\n  </section>
        marker = f'aria-labelledby="sec{sec_id}"'
        idx = html.find(marker)
        if idx != -1:
            # Find the closing grid div for this section
            close = html.find("    </div>\n  </section>", idx)
            if close != -1:
                return html[:close] + card_html + "\n" + html[close:]
    # Fallback: insert before footer
    for fb in ["\n<footer", "\n\n<footer"]:
        if fb in html:
            return html.replace(fb, card_html + "\n" + fb, 1)
    return html + card_html


def update_index_card_to_live(html, atlas, display_name):
    """Flip a card--forthcoming card to card--live in index.html.
    Handles both plain name match and homepage_name variants.
    Returns updated html."""
    import re

    # Find the card block by atlas display name
    # Pattern: card--forthcoming ... card-name">NAME< ... </div>\n      </div>
    pattern = (
        r'(<div class="card card--forthcoming">)'
        r'((?:(?!</div>\n    </div>).)*?)'
        r'(<div class="card-name">' + re.escape(display_name) + r'</div>)'
        r'((?:(?!</div>\n    </div>).)*?)'
        r'(<span class="coming-soon">Coming Soon</span>\n      </div>)'
    )
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return html, False

    original_block = m.group(0)

    # Build the live card — extract inner content between forthcoming opener and coming-soon span
    inner_start = m.start(2)
    inner_end = m.end(4)
    inner = html[m.start(2):m.end(4)]

    live_card = (
        f'''<div class="card card--live">\n'''
        f'''        <span class="status status--live">Live</span>\n'''
        f'''        <a href="{atlas}/index.html">'''
        + inner.strip("\n") +
        f'''\n        </a>\n'''
        f'''      </div>'''
    )

    html = html[:m.start()] + live_card + html[m.end():]
    return html, True


def cmd_new_atlas(key, name, section, icon, tagline, tags_str):
    """Register a new atlas idea invented by Claude Code."""
    state = load_state()

    key = key.lower().replace(" ", "_").replace("-", "_")
    if key in state["atlases"]:
        key = key + "_x"

    state["atlases"][key] = {
        "phase": "1A",
        "items": 0,
        "target": 100,
        "live": False,
        "map": "world",
        "section": section,
        "homepage_name": name
    }
    state["queue"].append(key)
    save_state(state)

    tags = [t.strip() for t in tags_str.split(",")][:3]
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    card = (
        '\n      <div class="card card--forthcoming">\n'
        f'        <span class="card-icon">{icon}</span>\n'
        f'        <div class="card-name">{name}</div>\n'
        f'        <div class="card-tagline">{tagline}</div>\n'
        f'        <div class="card-tags">{tag_html}</div>\n'
        '        <span class="coming-soon">Coming Soon</span>\n'
        '      </div>'
    )

    index_path = Path("index.html")
    committed = False
    if index_path.exists():
        html = index_path.read_text(encoding="utf-8")
        html = insert_card_into_section(html, section, card)
        index_path.write_text(html, encoding="utf-8")
        subprocess.run(["git", "add", "index.html", "pangea_state.json"], capture_output=True)
        r = subprocess.run(["git", "commit", "-m", f"feat: new atlas card — {name}"],
                           capture_output=True, text=True)
        committed = r.returncode == 0

    print(f"Registered: {name} ({key}) | section {section}")
    print(f"Homepage card inserted into section {section}: {committed}")
    print("Now building. Continuing loop.")
    sys.stdout.flush()
    self_invoke()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        result = get_next_action(load_state())
        if result is not None:
            print(json.dumps(result, indent=2))
    elif sys.argv[1] == "advance" and len(sys.argv) == 4:
        cmd_advance(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "item_done" and len(sys.argv) == 3:
        cmd_item_done(sys.argv[2])
    elif sys.argv[1] == "golive" and len(sys.argv) == 3:
        cmd_golive(sys.argv[2])
    elif sys.argv[1] == "status":
        cmd_status()
    elif sys.argv[1] == "verify":
        cmd_verify()
    elif sys.argv[1] == "new_atlas" and len(sys.argv) >= 7:
        cmd_new_atlas(sys.argv[2], sys.argv[3], sys.argv[4],
                      sys.argv[5], sys.argv[6],
                      sys.argv[7] if len(sys.argv) > 7 else "")
    else:
        print(__doc__)
        sys.exit(1)
