#!/usr/bin/env python3
"""
Pangea Project Orchestrator v2
================================
Usage:
  python3 pangea_orchestrator.py              — print next action as JSON
  python3 pangea_orchestrator.py advance ATLAS PHASE   — mark phase done, advance state
  python3 pangea_orchestrator.py golive ATLAS          — mark atlas live, update completed
  python3 pangea_orchestrator.py status                — human-readable progress report
  python3 pangea_orchestrator.py verify                — check state file integrity
"""

import json
import subprocess
import sys
from pathlib import Path

STATE_FILE = Path("pangea_state.json")

PHASES_ORDERED = [
    "1A", "1B", "1C", "1D", "1E", "1F",
    "2A", "2B", "2C", "2D",
    "3",
    "4A", "4B", "4C",
    "5",
    "6",
    "DONE"
]

# Phases that are skipped for standard world-map atlases
SKIP_IF_WORLD_MAP = {"1E", "4A", "4B", "4C"}

# Phases that are data-heavy (use batch-file merge strategy)
DATA_PHASES = {"2A", "2B", "2C", "2D"}


def load_state():
    if not STATE_FILE.exists():
        print("ERROR: pangea_state.json not found. Run from repo root.", file=sys.stderr)
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


def atlas_file_exists(atlas):
    return Path(f"{atlas}/index.html").exists()


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
        return {
            "action": "ALL_DONE",
            "message": "All atlases complete. Project finished.",
            "completed": state.get("completed", [])
        }

    atlas = queue[0]
    info = state["atlases"].get(atlas)

    if info is None:
        return {
            "action": "ERROR",
            "message": f"Atlas '{atlas}' is in queue but not in atlases object.",
            "atlas": atlas
        }

    # Already live — just need queue cleanup
    if info.get("live"):
        return {
            "action": "CLEANUP",
            "atlas": atlas,
            "message": f"{atlas} is already live but still in queue. Run: python3 pangea_orchestrator.py golive {atlas}"
        }

    phase = info.get("phase", "1A")

    # File complete, homepage not yet updated
    if phase == "DONE" and not info.get("live"):
        return {
            "action": "GO_LIVE",
            "atlas": atlas,
            "items": count_items(atlas),
            "target": info.get("target", 100),
            "section": info.get("section", "?"),
            "homepage_name": info.get("homepage_name", atlas.capitalize())
        }

    # Sync item count from disk
    real_count = count_items(atlas)
    if real_count != info.get("items", 0):
        info["items"] = real_count
        state["atlases"][atlas] = info
        save_state(state)

    return {
        "action": "EXECUTE_PHASE",
        "atlas": atlas,
        "phase": phase,
        "items": real_count,
        "target": info.get("target", 100),
        "map": info.get("map", "world"),
        "section": info.get("section", "?"),
        "is_data_phase": phase in DATA_PHASES,
        "next_phase": next_phase(phase, info.get("map", "world")),
        "file_exists": atlas_file_exists(atlas)
    }


def cmd_advance(atlas, completed_phase):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: atlas '{atlas}' not found in state.", file=sys.stderr)
        sys.exit(1)

    real_count = count_items(atlas)
    info["items"] = real_count
    info["phase"] = next_phase(completed_phase, info.get("map", "world"))

    log_entry = {
        "atlas": atlas,
        "phase_done": completed_phase,
        "phase_next": info["phase"],
        "items": real_count
    }

    state["atlases"][atlas] = info
    state.setdefault("session_log", []).append(log_entry)
    save_state(state)

    print(json.dumps({"status": "advanced", **log_entry}))


def cmd_golive(atlas):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: atlas '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)

    info["live"] = True
    info["phase"] = "DONE"
    info["items"] = count_items(atlas)
    state["atlases"][atlas] = info

    if atlas in state.get("queue", []):
        state["queue"].remove(atlas)

    if atlas not in state.get("completed", []):
        state.setdefault("completed", []).append(atlas)

    state.setdefault("session_log", []).append({
        "atlas": atlas,
        "phase_done": "GO_LIVE",
        "items": info["items"]
    })
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
    print(f"  Total atlases:    {total}")
    print(f"  Live:             {len(completed)}  {completed}")
    print(f"  Remaining queue:  {len(queue)}")
    print(f"  Progress:         {len(completed)}/{total} ({100*len(completed)//total}%)")
    print(f"\n  Next up: {queue[0] if queue else 'ALL DONE'}")

    if queue:
        next_atlas = queue[0]
        info = state["atlases"].get(next_atlas, {})
        print(f"  Phase:  {info.get('phase','?')}")
        print(f"  Items:  {count_items(next_atlas)}/{info.get('target',100)}")
        print(f"  Map:    {info.get('map','world')}")

    print(f"\n  Queue preview (next 10):")
    for a in queue[:10]:
        info = state["atlases"].get(a, {})
        print(f"    {a:<20} phase={info.get('phase','?'):<6} items={count_items(a)}/{info.get('target',100)}")
    print()


def cmd_verify():
    state = load_state()
    errors = []
    queue = state.get("queue", [])

    # Check for duplicates
    seen = set()
    for a in queue:
        if a in seen:
            errors.append(f"DUPLICATE in queue: {a}")
        seen.add(a)

    # Check queue entries exist in atlases
    for a in queue:
        if a not in state["atlases"]:
            errors.append(f"In queue but not in atlases: {a}")

    # Check completed entries
    for a in state.get("completed", []):
        if a not in state["atlases"]:
            errors.append(f"In completed but not in atlases: {a}")

    total = len(state["atlases"])
    print(f"Atlases object: {total}")
    print(f"Queue unique:   {len(set(queue))}")
    print(f"Completed:      {len(state.get('completed',[]))}")
    print(f"Grand total:    {len(set(queue)) + len(state.get('completed',[]))}")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nState file OK. No errors.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        state = load_state()
        action = get_next_action(state)
        print(json.dumps(action, indent=2))

    elif sys.argv[1] == "advance" and len(sys.argv) == 4:
        cmd_advance(sys.argv[2], sys.argv[3])

    elif sys.argv[1] == "golive" and len(sys.argv) == 3:
        cmd_golive(sys.argv[2])

    elif sys.argv[1] == "status":
        cmd_status()

    elif sys.argv[1] == "verify":
        cmd_verify()

    else:
        print(__doc__)
        sys.exit(1)
