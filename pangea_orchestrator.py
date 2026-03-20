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


def get_next_action(state):
    queue = state.get("queue", [])
    if not queue:
        return {"action": "ALL_DONE", "completed": state.get("completed", [])}

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


def cmd_item_done(atlas):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    real_count = count_items(atlas)
    info["items"] = real_count
    state["atlases"][atlas] = info
    save_state(state)
    target = info.get("target", 100)
    remaining = target - real_count
    if remaining <= 0:
        print(f"ITEMS COMPLETE: {real_count}/{target}. Now execute: python3 pangea_orchestrator.py advance {atlas} DATA")
    else:
        n = real_count + 1
        print(
            f"item_recorded {real_count}/{target}. {remaining} remaining.\n"
            f"NOW WRITE ITEM {n}. ONE item. Append to ITEMS array in {atlas}/index.html.\n"
            f"Verify: grep -c '^{{id:\'' {atlas}/index.html must equal {n}.\n"
            f"Then commit: git add {atlas}/index.html && git commit -m '{atlas}: item {n}/{target}'\n"
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
    print(json.dumps({"status": "live", "atlas": atlas, "items": info["items"]}))


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
    else:
        print(__doc__)
        sys.exit(1)
