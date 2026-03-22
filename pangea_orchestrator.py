#!/usr/bin/env python3
"""
Pangea Project Orchestrator v3
================================
Usage:
  python3 pangea_orchestrator.py                     — print next action as JSON
  python3 pangea_orchestrator.py advance ATLAS PHASE — mark shell/constants/modes phase done
  python3 pangea_orchestrator.py batch_done ATLAS    — record a batch of items written (up to 10)
  python3 pangea_orchestrator.py item_done ATLAS     — legacy alias for batch_done
  python3 pangea_orchestrator.py golive ATLAS        — mark atlas live
  python3 pangea_orchestrator.py status              — human-readable progress report
  python3 pangea_orchestrator.py verify              — check state file integrity
  python3 pangea_orchestrator.py sync                — pull & rebase before committing (prevents merge conflicts)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

STATE_FILE = Path("pangea_state.json")


# ── Merge-conflict prevention ────────────────────────────────────────────────

def _run_git(*args, **kwargs):
    """Run a git command and return the CompletedProcess."""
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, **kwargs)


def _merge_state_json(ours_path):
    """Smart-merge pangea_state.json after a rebase/merge conflict.

    Strategy: load both versions, merge atlases (union of keys, prefer the
    version with more progress), merge queue (union preserving order), merge
    completed (union), merge session_log (concatenate and deduplicate).
    Returns True if resolved, False if unresolvable.
    """
    try:
        # Get the two conflicting versions
        ours_result = _run_git("show", ":2:pangea_state.json")   # ours
        theirs_result = _run_git("show", ":3:pangea_state.json") # theirs
        if ours_result.returncode != 0 or theirs_result.returncode != 0:
            return False
        ours = json.loads(ours_result.stdout)
        theirs = json.loads(theirs_result.stdout)
    except (json.JSONDecodeError, KeyError):
        return False

    merged = dict(ours)

    # Merge atlases: union of keys; for shared keys, pick the one further along
    phase_rank = {p: i for i, p in enumerate(PHASES_ORDERED)}
    their_atlases = theirs.get("atlases", {})
    our_atlases = merged.get("atlases", {})
    for key, their_info in their_atlases.items():
        if key not in our_atlases:
            our_atlases[key] = their_info
        else:
            our_info = our_atlases[key]
            our_phase = phase_rank.get(our_info.get("phase", "1A"), 0)
            their_phase = phase_rank.get(their_info.get("phase", "1A"), 0)
            # Pick whichever is further along (higher phase or more items)
            if their_phase > our_phase or (
                their_phase == our_phase
                and their_info.get("items", 0) > our_info.get("items", 0)
            ):
                our_atlases[key] = their_info
            # If theirs is live and ours isn't, take theirs
            if their_info.get("live") and not our_info.get("live"):
                our_atlases[key] = their_info
    merged["atlases"] = our_atlases

    # Merge queue: union preserving order (ours first, then any new from theirs)
    our_queue = merged.get("queue", [])
    their_queue = theirs.get("queue", [])
    seen = set(our_queue)
    for item in their_queue:
        if item not in seen:
            our_queue.append(item)
            seen.add(item)
    # Remove anything that's now live or completed from the queue
    completed_set = set(merged.get("completed", []))
    for key, info in our_atlases.items():
        if info.get("live"):
            completed_set.add(key)
    our_queue = [q for q in our_queue if q not in completed_set]
    merged["queue"] = our_queue

    # Merge completed: union
    our_completed = set(merged.get("completed", []))
    their_completed = set(theirs.get("completed", []))
    merged["completed"] = list(our_completed | their_completed)

    # Merge session_log: concatenate, deduplicate by content
    our_log = merged.get("session_log", [])
    their_log = theirs.get("session_log", [])
    seen_entries = {json.dumps(e, sort_keys=True) for e in our_log}
    for entry in their_log:
        key = json.dumps(entry, sort_keys=True)
        if key not in seen_entries:
            our_log.append(entry)
            seen_entries.add(key)
    merged["session_log"] = our_log

    # Write merged result
    Path(ours_path).write_text(json.dumps(merged, indent=2))
    _run_git("add", ours_path)
    return True


def pull_and_rebase():
    """Pull latest changes from origin, rebasing local commits on top.

    Handles conflicts on pangea_state.json with smart JSON merge.
    Returns True if sync succeeded, False if manual intervention needed.
    """
    # Detect current branch
    branch_result = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    if branch_result.returncode != 0:
        return True  # not in a git repo or detached HEAD — skip
    branch = branch_result.stdout.strip()

    # Fetch with retry
    for attempt in range(4):
        fetch = _run_git("fetch", "origin", branch)
        if fetch.returncode == 0:
            break
        wait = 2 ** (attempt + 1)
        print(f"  fetch failed (attempt {attempt+1}/4), retrying in {wait}s...")
        time.sleep(wait)
    else:
        print("WARNING: Could not fetch from origin — committing locally only.")
        return True

    # Check if there are upstream changes to incorporate
    diff_check = _run_git("rev-list", "--count", f"HEAD..origin/{branch}")
    if diff_check.returncode != 0 or diff_check.stdout.strip() == "0":
        return True  # nothing to rebase onto

    # Stash any unstaged changes so rebase doesn't fail on dirty tree
    _run_git("stash", "--include-untracked", "-m", "orchestrator-auto-stash")
    stashed = True

    # Attempt rebase
    rebase = _run_git("rebase", f"origin/{branch}")
    if rebase.returncode != 0:
        # Check if the conflict is only on pangea_state.json
        status = _run_git("diff", "--name-only", "--diff-filter=U")
        conflicted = [f.strip() for f in status.stdout.strip().split("\n") if f.strip()]

        resolvable = True
        for f in conflicted:
            if f == "pangea_state.json":
                if not _merge_state_json(f):
                    resolvable = False
                    break
            else:
                resolvable = False
                break

        if resolvable and conflicted:
            cont = _run_git("rebase", "--continue")
            if cont.returncode != 0:
                # Try with a no-edit env to skip editor
                env = os.environ.copy()
                env["GIT_EDITOR"] = "true"
                subprocess.run(
                    ["git", "rebase", "--continue"],
                    capture_output=True, text=True, env=env
                )
        elif not resolvable:
            _run_git("rebase", "--abort")
            print("WARNING: Rebase conflict could not be auto-resolved. Committing without rebase.")

    # Restore stash
    if stashed:
        _run_git("stash", "pop")

    return True


def safe_git_commit(files, message):
    """Stage files, sync with remote, then commit. Returns True on success.

    This is the single commit entry-point for the orchestrator.  It:
      1. Stages the given files
      2. Pulls & rebases to avoid merge conflicts
      3. Re-stages files (in case rebase changed them)
      4. Commits
    """
    # Stage
    for f in files:
        _run_git("add", f)

    # Sync with remote before committing
    pull_and_rebase()

    # Re-stage in case rebase changed working tree
    for f in files:
        if Path(f).exists():
            _run_git("add", f)

    # Commit
    result = _run_git("commit", "-m", message)
    if result.returncode != 0:
        # Might be "nothing to commit" after rebase incorporated our changes
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print("  (changes already incorporated by rebase — no new commit needed)")
            return True
        print(f"WARNING: git commit failed: {result.stderr.strip()}")
        return False
    return True


def cmd_sync():
    """Pull latest changes and rebase local work on top. Called by agents
    before they make their own commits to avoid merge conflicts."""
    pull_and_rebase()
    print("Sync complete.")

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
    state = json.loads(STATE_FILE.read_text())
    state = prioritise_building(state)
    return state


def prioritise_building(state):
    """Move any atlas marked card--building on the homepage to the front of the queue."""
    index_path = Path("index.html")
    if not index_path.exists():
        return state

    html = index_path.read_text(encoding="utf-8")
    queue = state.get("queue", [])

    # Find all atlas directory names that have card--building on the homepage.
    # The pattern is: card--building ... href="ATLAS/index.html"
    import re
    building_hrefs = re.findall(
        r'card--building[\s\S]*?href="([^/]+)/index\.html"',
        html
    )
    building_keys = []
    for href in building_hrefs:
        key = href.lower().replace("-", "_").replace(" ", "_")
        # Also try exact match
        if key in state["atlases"] and key in queue:
            building_keys.append(key)
        elif href in state["atlases"] and href in queue:
            building_keys.append(href)

    if not building_keys:
        return state

    # Reorder queue: building atlases first, then the rest
    rest = [a for a in queue if a not in building_keys]
    new_queue = building_keys + rest

    if new_queue != queue:
        state["queue"] = new_queue
        save_state(state)
        print(f"Prioritised building atlases: {building_keys}")

    return state


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
    """Auto-generate and register a new atlas when the queue is empty.

    Draws from a large pool of pre-defined atlas ideas, skipping any whose key
    already exists in state.  If the pool is exhausted, synthesises a key from
    a rotating pattern so the pipeline never stops.
    """
    existing = set(state["atlases"].keys())

    # ── Atlas idea pool ─────────────────────────────────────────────────
    # Each tuple: (key, display_name, section, icon, tagline, tags)
    # Rules: global scope, 5 000+ year span, clear Herstory angle, Latin key.
    IDEA_POOL = [
        # ── Batch 1: Original pool ──────────────────────────────────────────
        ("colonia",    "Colonia",    "V",    "🏴",  "Every empire planted a flag — every colony pulled it down.",            "Colonialism,Empire,Resistance"),
        ("orbis",      "Orbis",      "IX",   "🌍",  "The story of maps, borders, and who drew them.",                        "Geography,Cartography,Borders"),
        ("nexus",      "Nexus",      "IX",   "🔗",  "Networks that connected civilisations before the internet.",            "Networks,Communication,Trade"),
        ("ferrum",     "Ferrum",     "II",   "⛏️",  "Every metal humanity pulled from the earth changed history.",           "Metallurgy,Mining,Industry"),
        ("navigium",   "Navigium",   "VIII", "⛵",  "From reed boats to aircraft carriers — the sea changed everything.",   "Ships,Navigation,Maritime"),
        ("scholae",    "Scholae",    "IV",   "🏫",  "How humanity learned to teach itself.",                                "Education,Schools,Literacy"),
        ("caelum",     "Caelum",     "II",   "☁️",  "The atmosphere is the thinnest page in Earth's biography.",             "Weather,Climate,Atmosphere"),
        ("hospitium",  "Hospitium",  "X",    "🏥",  "Every hospital, healer, and plague that reshaped medicine.",            "Medicine,Healing,Epidemics"),
        ("pratum",     "Pratum",     "I",    "🌾",  "Agriculture invented civilisation — then civilisation forgot.",         "Farming,Land,Food"),
        ("textilis",   "Textilis",   "VIII", "🧵",  "Thread, loom, and needle wove the fabric of every society.",            "Textiles,Fashion,Industry"),
        ("numerus",    "Numerus",    "III",  "🔢",  "From tally sticks to quantum computers — the number shaped the world.","Numbers,Counting,Data"),
        ("asylum",     "Asylum",     "VI",   "🕊️",  "Every refugee carried a civilisation in their memory.",                "Refugees,Migration,Sanctuary"),
        ("carcere",    "Carcere",    "VI",   "🔒",  "Walls built to confine changed the societies that built them.",        "Prisons,Punishment,Justice"),
        ("aeris",      "Aeris",      "II",   "✈️",  "From Icarus to orbit — the conquest of the sky.",                      "Aviation,Flight,Aerospace"),
        ("aquaeductus","Aquaeductus","VIII", "🚰",  "Every civilisation rose on water engineering and fell without it.",     "Water,Infrastructure,Sanitation"),
        ("sapientia",  "Sapientia",  "IV",   "🦉",  "The libraries, universities, and thinkers who kept knowledge alive.",  "Wisdom,Philosophy,Scholarship"),
        ("tyrannis",   "Tyrannis",   "V",    "👑",  "Every tyrant thought the throne was permanent.",                       "Tyranny,Autocracy,Revolution"),
        ("aether",     "Aether",     "II",   "📡",  "Invisible waves that rewrote how humanity communicates.",              "Radio,Signals,Telecom"),
        ("ruina",      "Ruina",      "III",  "🏚️",  "The archaeology of collapse — what survived and what didn't.",         "Ruins,Archaeology,Collapse"),
        ("hereditas",  "Hereditas",  "X",    "🧬",  "Blood, lineage, and inheritance shaped every throne and farm.",        "Genetics,Inheritance,Lineage"),
        ("patronus",   "Patronus",   "VIII", "🎭",  "Patrons made art possible — and controlled what it said.",             "Patronage,Arts,Power"),
        ("exsilium",   "Exsilium",   "VI",   "🚪",  "Banishment created new worlds wherever the exiled landed.",            "Exile,Diaspora,Identity"),
        ("oraculum",   "Oraculum",   "IV",   "🔮",  "Prophecy, divination, and the futures humanity tried to read.",        "Prophecy,Divination,Fate"),
        ("foedus",     "Foedus",     "V",    "🤝",  "Every treaty was a bet that peace could be written down.",             "Treaties,Diplomacy,Alliances"),
        ("pons",       "Pons",       "VIII", "🌉",  "Bridges connected what geography kept apart.",                         "Bridges,Engineering,Connection"),
        ("glacies",    "Glacies",    "II",   "🧊",  "Ice ages and frozen frontiers that shaped human migration.",           "Ice,Glaciers,Climate"),
        ("nummularius","Nummularius","VII",  "🏦",  "Banking invented modern power — and modern crisis.",                   "Banking,Finance,Credit"),
        ("censor",     "Censor",     "VI",   "✂️",  "What was silenced tells us as much as what was spoken.",               "Censorship,Suppression,Freedom"),
        ("elementum",  "Elementum",  "II",   "⚗️",  "From four elements to 118 — chemistry remade the world.",             "Chemistry,Elements,Alchemy"),
        ("bibliotheca","Bibliotheca","IV",   "📚",  "Every burned library was a civilisation's memory erased.",             "Libraries,Books,Knowledge"),
        # ── Batch 2: Extended pool ──────────────────────────────────────────
        ("veneficium", "Veneficium", "IV",   "🧪",  "Poison, pharmacy, and the thin line between cure and kill.",           "Poison,Medicine,Alchemy"),
        ("ludus",      "Ludus",      "IX",   "🎲",  "Games, sport, and spectacle — how humanity learned to compete.",       "Games,Sport,Competition"),
        ("vestis",     "Vestis",     "VIII", "👘",  "Clothing told the world who you were before you spoke.",               "Clothing,Fashion,Identity"),
        ("fames",      "Fames",      "I",    "🍞",  "Every famine reshaped the politics of the full.",                      "Famine,Food,Scarcity"),
        ("pestis",     "Pestis",     "X",    "🦠",  "Plagues killed more than wars — and changed more than revolutions.",   "Plague,Disease,Pandemic"),
        ("specula",    "Specula",    "III",  "🔭",  "Observation towers, lighthouses, and the architecture of watching.",   "Observation,Surveillance,Towers"),
        ("silva",      "Silva",      "I",    "🌲",  "Forests fed, sheltered, and terrified every civilisation.",             "Forests,Timber,Ecology"),
        ("vinum",      "Vinum",      "VII",  "🍷",  "Wine, beer, and spirits — fermentation shaped trade and ritual.",      "Alcohol,Brewing,Trade"),
        ("clavus",     "Clavus",     "VIII", "🔑",  "Locks, keys, and the invention of private property.",                  "Security,Property,Trust"),
        ("theatrum",   "Theatrum",   "IX",   "🎭",  "The stage held a mirror to every society that built one.",             "Theatre,Performance,Drama"),
        ("moneta",     "Moneta",     "VII",  "🪙",  "Coins carried power further than any army.",                           "Coins,Currency,Minting"),
        ("desertum",   "Desertum",   "I",    "🏜️",  "Deserts were never empty — they were full of adaptation.",             "Deserts,Arid,Survival"),
        ("servitus",   "Servitus",   "VI",   "⛓️",  "Slavery built empires — abolition rebuilt the world.",                 "Slavery,Abolition,Labour"),
        ("census",     "Census",     "III",  "📋",  "Counting people was the first act of governance.",                     "Census,Population,Data"),
        ("ars_bellica","Ars Bellica","V",    "🏰",  "Fortifications, sieges, and the architecture of survival.",            "Fortifications,Sieges,Defence"),
        ("dolium",     "Dolium",     "VIII", "🏺",  "Pottery, ceramics, and the containers that carried civilisation.",     "Pottery,Ceramics,Storage"),
        ("sal",        "Sal",        "VII",  "🧂",  "Salt preserved food, funded empires, and started wars.",               "Salt,Preservation,Trade"),
        ("ignis",      "Ignis",      "II",   "🔥",  "Fire was humanity's first technology — and its most dangerous.",       "Fire,Energy,Industry"),
        ("calendarium","Calendarium","III",  "📅",  "Calendars decided when to plant, pray, and fight.",                    "Calendars,Time,Astronomy"),
        ("mythologia", "Mythologia", "IV",   "🐉",  "Myths explained the world before science tried.",                     "Mythology,Legend,Folklore"),
        ("metallum",   "Metallum",   "II",   "⚙️",  "Bronze, iron, steel — each metal age remade the balance of power.",   "Metals,Smelting,Industry"),
        ("taberna",    "Taberna",     "VII",  "🏪",  "Markets, bazaars, and shops — where strangers became neighbours.",     "Markets,Commerce,Exchange"),
        ("musica",     "Musica",     "IX",   "🎵",  "Every culture sang before it wrote.",                                  "Music,Song,Instruments"),
        ("portus",     "Portus",     "VIII", "⚓",  "Ports were the mouths through which civilisations spoke to each other.","Ports,Harbours,Trade"),
        ("mons",       "Mons",       "I",    "🏔️",  "Mountains divided peoples and sheltered the defiant.",                 "Mountains,Terrain,Isolation"),
        ("papyrus",    "Papyrus",    "III",  "📜",  "Writing surfaces — from clay to cloud — shaped what survived.",        "Writing,Paper,Records"),
        ("pirata",     "Pirata",     "V",    "🏴‍☠️",  "Pirates policed the margins of every maritime empire.",                "Piracy,Smuggling,Maritime"),
        ("lingua",     "Lingua",     "IV",   "🗣️",  "Languages carried worldviews — when they died, worlds ended.",        "Language,Linguistics,Translation"),
        ("fossilia",   "Fossilia",   "II",   "🦴",  "Fossils rewrote the story humanity told about itself.",                "Fossils,Palaeontology,Evolution"),
        ("color",      "Color",      "IX",   "🎨",  "Pigments, dyes, and colours — the chemistry of beauty.",               "Colour,Dyes,Pigments"),
    ]

    # Filter out any ideas whose key already exists
    available = [idea for idea in IDEA_POOL if idea[0] not in existing]

    if not available:
        # Pool exhausted — synthesise with meaningful names from a secondary list
        OVERFLOW_THEMES = [
            ("labyrinthus", "Labyrinthus", "🌀", "Mazes, puzzles, and the architecture of confusion.", "Mazes,Puzzles,Architecture"),
            ("umbra",       "Umbra",       "🌑", "Shadows, eclipses, and the science of darkness.",    "Shadows,Eclipses,Optics"),
            ("harena",      "Harena",      "🏟️", "Arenas, amphitheatres, and spectacles of power.",   "Arenas,Gladiators,Spectacle"),
            ("horologium",  "Horologium",  "⏳", "Clocks, sundials, and humanity's obsession with time.", "Clocks,Time,Horology"),
            ("spectrum",    "Spectrum",    "🌈", "Light, optics, and the science of seeing.",          "Light,Optics,Colour"),
            ("apotheca",    "Apotheca",    "💊", "Pharmacies, apothecaries, and the business of healing.", "Pharmacy,Remedies,Healing"),
            ("coemeterium", "Coemeterium", "⚰️", "Burial, mourning, and the architecture of death.",  "Death,Burial,Mourning"),
            ("nummus",      "Nummus",      "💰", "Debt, credit, and the invisible architecture of obligation.", "Debt,Credit,Obligation"),
            ("machina",     "Machina",     "🔧", "Machines, automation, and the labour they displaced.", "Machines,Automation,Labour"),
            ("turris",      "Turris",      "🗼", "Towers — from Babel to broadcast — reaching upward.", "Towers,Height,Ambition"),
        ]
        for okey, oname, oicon, otagline, otags in OVERFLOW_THEMES:
            if okey not in existing:
                # Pick section with fewest atlases
                section_counts = {}
                for info in state["atlases"].values():
                    s = info.get("section", "I")
                    section_counts[s] = section_counts.get(s, 0) + 1
                all_sections = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]
                section = min(all_sections, key=lambda s: section_counts.get(s, 0))
                chosen = (okey, oname, section, oicon, otagline, otags)
                break
        else:
            # Even overflow exhausted — synthesise from counter
            counter = len(existing)
            key = f"atlas_{counter}"
            while key in existing:
                counter += 1
                key = f"atlas_{counter}"
            section_counts = {}
            for info in state["atlases"].values():
                s = info.get("section", "I")
                section_counts[s] = section_counts.get(s, 0) + 1
            all_sections = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]
            section = min(all_sections, key=lambda s: section_counts.get(s, 0))
            chosen = (key, key.replace("_", " ").title(), section, "🗺️",
                      "Another chapter in humanity's unfinished story.",
                      "History,Culture,Civilization")
    else:
        # Pick the first available (deterministic order, not random)
        chosen = available[0]

    key, name, section, icon, tagline, tags = chosen
    print(f"Queue empty — auto-generating new atlas: {name} ({key})")
    cmd_new_atlas(key, name, section, icon, tagline, tags)


def get_next_action(state):
    queue = state.get("queue", [])
    if not queue:
        # Auto-generate a new atlas and continue the loop.
        # generate_new_atlas() calls cmd_new_atlas() which calls self_invoke(),
        # so this branch never returns — the process re-execs with the new queue.
        generate_new_atlas(state)
        return None  # unreachable, but keeps the type signature consistent

    atlas = queue[0]
    info = state["atlases"].get(atlas)

    if info is None:
        return {"action": "ERROR", "message": f"'{atlas}' in queue but not in atlases.", "atlas": atlas}

    if info.get("live"):
        return {"action": "CLEANUP", "atlas": atlas}

    phase = info.get("phase", "1A")

    # If atlas has data.js and is still in Phase 1, skip to DATA
    if phase.startswith("1") and Path(f"{atlas}/data.js").exists():
        print(f"  {atlas}: data.js found — skipping Phase 1 shell (scaffold handles it).")
        print(f"  Run: python3 build.py {atlas}  — to build index.html from data.js")
        info["phase"] = "DATA"
        state["atlases"][atlas] = info
        save_state(state)
        phase = "DATA"

    if phase == "DONE" and not info.get("live"):
        # Auto-golive: validate, flip card, commit, and chain to next atlas
        print(f"{atlas} is DONE but not live — auto-triggering go-live...")
        cmd_golive(atlas)  # chains into self_invoke() → next atlas
        return None  # unreachable — cmd_golive calls self_invoke()

    # Sync item count
    real_count = count_items(atlas)
    if real_count != info.get("items", 0):
        info["items"] = real_count
        state["atlases"][atlas] = info
        save_state(state)

    target = info.get("target", 100)

    # DATA phase: emit WRITE_BATCH until target reached
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
        batch_start = real_count + 1
        batch_end = min(real_count + 1, target)
        batch_size = batch_end - real_count
        # Print imperative directly so agent has no decision gap
        print(
            f"WRITE_BATCH {batch_start}-{batch_end}/{target} for {atlas}. "
            f"Write {batch_size} item.\n"
            f"1. Append {batch_size} item to the ITEMS array in {atlas}/index.html\n"
            f"   (or in {atlas}/data.js if using the build system)\n"
            f"2. grep -c '^{{id:\'' {atlas}/index.html  →  must equal {batch_end}\n"
            f"3. python3 pangea_orchestrator.py sync\n"
            f"4. git add {atlas}/ && git commit -m '{atlas}: item {batch_start}/{target}'\n"
            f"5. python3 pangea_orchestrator.py batch_done {atlas}"
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


def run_validation(atlas):
    """Run pangea_validate.py for atlas. Returns True if passed, False if failed."""
    result = subprocess.run(
        [sys.executable, "pangea_validate.py", atlas],
        capture_output=False  # let output stream to terminal
    )
    return result.returncode == 0


def cmd_advance(atlas, completed_phase):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    real_count = count_items(atlas)
    info["items"] = real_count

    # Phase 5 complete → run validation, then auto-golive and chain to next atlas
    if completed_phase == "5":
        print(f"Phase 5 complete. Running validation automatically...")
        passed = run_validation(atlas)
        if not passed:
            print()
            print(f"VALIDATION FAILED. Fix all FAIL items in {atlas}/index.html.")
            print(f"Then re-run: python3 pangea_orchestrator.py advance {atlas} 5")
            sys.exit(1)
        # Validation passed — go live immediately, no manual GO_LIVE step
        info["phase"] = "DONE"
        state["atlases"][atlas] = info
        state.setdefault("session_log", []).append({
            "atlas": atlas, "phase_done": "5+6", "phase_next": "GO_LIVE", "items": real_count
        })
        save_state(state)
        print(f"Validation passed. Auto-triggering go-live for {atlas}...")
        cmd_golive(atlas)  # chains into self_invoke() → next atlas
        return

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


def cmd_batch_done(atlas):
    """Record a batch of items written (up to 25 at a time)."""
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)
    real_count = count_items(atlas)
    prev_count = info.get("items", 0)
    target = info.get("target", 100)

    added = real_count - prev_count
    if added == 0:
        print(f"ERROR: No new items detected. Count is still {real_count}.")
        print(f"Write items to {atlas}/index.html (or data.js), then call batch_done again.")
        sys.exit(1)
    if added > 5:
        print(f"WARNING: {added} items added (max batch is 1). Accepted, but prefer 1 at a time.")

    info["items"] = real_count
    remaining = target - real_count

    state["atlases"][atlas] = info
    state.setdefault("session_log", []).append({
        "atlas": atlas, "batch": f"{prev_count+1}-{real_count}", "items": real_count
    })
    save_state(state)

    if remaining <= 0:
        print(f"ITEMS COMPLETE: {real_count}/{target}. Auto-advancing to Phase 3.")
        info["phase"] = next_phase("DATA", info.get("map", "world"))
        state["atlases"][atlas] = info
        save_state(state)
        self_invoke()
    else:
        batch_start = real_count + 1
        batch_end = min(real_count + 1, target)
        batch_size = batch_end - real_count
        print(
            f"batch_recorded {real_count}/{target}. {remaining} remaining.\n"
            f"WRITE NEXT ITEM: item {batch_start}/{target}.\n"
            f"Sync:   python3 pangea_orchestrator.py sync\n"
            f"Commit: git add {atlas}/ && git commit -m '{atlas}: item {batch_start}/{target}'\n"
            f"Then run: python3 pangea_orchestrator.py batch_done {atlas}"
        )


def cmd_item_done(atlas):
    """Legacy single-item mode — redirects to batch_done."""
    cmd_batch_done(atlas)


def cmd_golive(atlas):
    state = load_state()
    info = state["atlases"].get(atlas)
    if info is None:
        print(f"ERROR: '{atlas}' not found.", file=sys.stderr)
        sys.exit(1)

    # Safety gate: validate before going live (skips instantly if already validated at current SHA)
    print(f"Running validation gate before go-live...")
    passed = run_validation(atlas)
    if not passed:
        print(f"BLOCKED: {atlas} failed validation. Fix issues before going live.")
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

            # Validate homepage after update — catch broken HTML before committing
            print("Validating homepage after go-live update...")
            hp_result = subprocess.run(
                [sys.executable, "pangea_validate.py", "--homepage"],
                capture_output=True, text=True
            )
            if hp_result.returncode != 0:
                print("WARNING: Homepage validation failed after go-live update!")
                print(hp_result.stdout)
                print("The homepage HTML may be broken — review index.html manually.")

        commit_files = [f"{atlas}/index.html", "pangea_state.json"]
        if index_updated:
            commit_files.append("index.html")
        safe_git_commit(commit_files, f"{atlas}: go-live — homepage activated")

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


def cmd_validation_status():
    """Show validation state for all atlases."""
    state = load_state()
    print(f"\n{'ATLAS':<22} {'PHASE':<8} {'ITEMS':<8} {'VALIDATED':<12} {'SHA':<10} {'AT'}")
    print("-" * 80)
    for key in sorted(state["atlases"]):
        info = state["atlases"][key]
        phase = info.get("phase", "?")
        items = info.get("items", 0)
        sha = info.get("validated_short", "-")
        at = info.get("validated_at", "-")[:10] if info.get("validated_at") else "-"
        validated = "YES" if info.get("validated_sha") else "no"
        print(f"  {key:<20} {phase:<8} {items:<8} {validated:<12} {sha:<10} {at}")
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

    # Find the complete card block containing this atlas name.
    # Each card is:  <div class="card card--forthcoming">...card-name">NAME</div>...<span class="coming-soon">Coming Soon</span>\n      </div>
    # We search for the card-name line first, then find the enclosing card div.
    name_pattern = r'<div class="card-name">' + re.escape(display_name) + r'</div>'
    name_match = re.search(name_pattern, html)
    if not name_match:
        return html, False

    # Walk backwards from the name to find the card--forthcoming opener
    search_start = max(0, name_match.start() - 500)
    prefix = html[search_start:name_match.start()]
    opener_pos = prefix.rfind('<div class="card card--forthcoming">')
    if opener_pos == -1:
        return html, False
    card_start = search_start + opener_pos

    # Walk forwards from the name to find the closing </div> of the card
    # The card ends with "Coming Soon</span>\n      </div>" or similar
    search_end = min(len(html), name_match.end() + 500)
    suffix = html[name_match.end():search_end]
    # Find the coming-soon span and the closing </div> after it
    cs_match = re.search(r'<span class="coming-soon">Coming Soon</span>\s*</div>', suffix)
    if not cs_match:
        # Fallback: just find the next </div> pair
        cs_match = re.search(r'</div>\s*</div>', suffix)
        if not cs_match:
            return html, False
    card_end = name_match.end() + cs_match.end()

    old_block = html[card_start:card_end]

    # Extract the inner content: icon, name, tagline, tags
    inner = old_block
    inner = re.sub(r'<div class="card card--forthcoming">\s*', '', inner)
    inner = re.sub(r'<span class="coming-soon">Coming Soon</span>\s*</div>\s*$', '', inner)
    inner = inner.strip()

    live_card = (
        f'<div class="card card--live">\n'
        f'        <span class="status status--live">Live</span>\n'
        f'        <a href="{atlas}/index.html" style="text-decoration:none;color:inherit">\n'
        f'        {inner}\n'
        f'        </a>\n'
        f'      </div>'
    )

    html = html[:card_start] + live_card + html[card_end:]
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
        committed = safe_git_commit(
            ["index.html", "pangea_state.json"],
            f"feat: new atlas card — {name}"
        )

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
    elif sys.argv[1] == "batch_done" and len(sys.argv) == 3:
        cmd_batch_done(sys.argv[2])
    elif sys.argv[1] == "golive" and len(sys.argv) == 3:
        cmd_golive(sys.argv[2])
    elif sys.argv[1] == "sync":
        cmd_sync()
    elif sys.argv[1] == "status":
        cmd_status()
    elif sys.argv[1] == "verify":
        cmd_verify()
    elif sys.argv[1] == "validation_status":
        cmd_validation_status()
    elif sys.argv[1] == "new_atlas" and len(sys.argv) >= 7:
        cmd_new_atlas(sys.argv[2], sys.argv[3], sys.argv[4],
                      sys.argv[5], sys.argv[6],
                      sys.argv[7] if len(sys.argv) > 7 else "")
    else:
        print(__doc__)
        sys.exit(1)
