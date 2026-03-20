# Pangea Project — Agentic Pipeline Setup
## Complete instructions for autonomous atlas completion

---

## What this pipeline does

Reads `pangea_state.json` to determine the next action, executes exactly one
checkpoint-sized unit of work (one phase, one data batch, or one go-live),
commits, updates state, and stops. Each Claude Code session picks up exactly
where the last one left off.

Current status: **6 live, 113 to build** (119 total atlases).

---

## One-time setup

### 1. Copy these four files into your repo root

```
pangea_state.json       ← state machine / progress tracker
pangea_orchestrator.py  ← determines next action
pangea_validate.py      ← runs Section 18 checks before go-live
MASTER_PROMPT.md        ← the prompt you paste into Claude Code
```

### 2. Verify setup
```bash
cd /path/to/pangea
python3 pangea_orchestrator.py verify
python3 pangea_orchestrator.py status
```

Expected output from `status`:
```
Total atlases:    119
Live:             6
Remaining queue:  113
Progress:         6/119 (5%)
Next up:          cosmos
Phase:            DONE
```

### 3. Commit the pipeline files
```bash
git add pangea_state.json pangea_orchestrator.py pangea_validate.py MASTER_PROMPT.md
git commit -m "chore: add autonomous build pipeline"
```

---

## How to run a session

### Every session — same three steps:

**Step 1.** Open Claude Code in your repo directory.

**Step 2.** Paste the entire contents of `MASTER_PROMPT.md` as your first message.

**Step 3.** Let it run. It will stop itself at the nearest safe checkpoint.

That's it. Claude Code reads the state file, does the work, commits, updates
state, and stops with a summary telling you exactly what to do next session.

---

## Quota-aware design

The pipeline is designed around Claude's usage limits:

| Session type | What happens | Typical duration |
|---|---|---|
| GO_LIVE only | Homepage activation for cosmos (first run) | ~5 min |
| Shell session | Phases 1A→1F for one atlas | ~15–20 min |
| Data session | One 25-item batch (2A/2B/2C/2D) | ~20–30 min |
| Validation+live | Phase 6 + GO_LIVE | ~10 min |

**Each atlas requires approximately 7–8 sessions to complete:**
- 1 session: shell (1A–1F)
- 4 sessions: data batches (2A, 2B, 2C, 2D)
- 1 session: constants (Phase 3)
- 1 session: validation + go-live (Phase 6)

**At 2 sessions per day:** ~4 sessions/week × 113 atlases ÷ 8 sessions each
= approximately **226 weeks** at minimum pace, or faster if you run more sessions.

**At maximum pace (Pro plan, ~4 hours/day):**
- Morning: shell + 2A
- Afternoon: 2B + 2C
- Evening: 2D + Phase 3
- Next day: Phase 6 + GO_LIVE + next atlas shell

That's roughly 1 atlas every 2 days at full pace = ~226 atlases-worth of work
spread over the queue. Realistic completion at full pace: 6–9 months.

---

## Resuming after interruption

The state file is updated after every commit. If a session is interrupted:

1. Check what was last committed: `git log --oneline -5`
2. Check current state: `python3 pangea_orchestrator.py status`
3. If state and git are out of sync, manually advance:
   ```bash
   python3 pangea_orchestrator.py advance ATLAS_NAME LAST_COMPLETED_PHASE
   ```
4. Start a fresh session with MASTER_PROMPT.md as normal.

---

## Manual state corrections

If you need to correct the state file directly:

```bash
# Mark an atlas as being at a specific phase
python3 -c "
import json
s = json.load(open('pangea_state.json'))
s['atlases']['dynastia']['phase'] = '2B'
s['atlases']['dynastia']['items'] = 50
json.dump(s, open('pangea_state.json','w'), indent=2)
print('done')
"

# Re-run verification after any manual edit
python3 pangea_orchestrator.py verify
```

---

## Monitoring progress

```bash
# Quick status
python3 pangea_orchestrator.py status

# See next action
python3 pangea_orchestrator.py

# Count live atlases on homepage
grep -c "card--live" index.html

# Count items in a specific atlas
grep -c "^{id:'" dynastia/index.html

# Validate a specific atlas without going live
python3 pangea_validate.py dynastia
```

---

## Adding new atlases

If you add new atlas cards to `index.html`, also add them to `pangea_state.json`:

```bash
python3 -c "
import json
s = json.load(open('pangea_state.json'))
new_atlas = 'newname'
s['atlases'][new_atlas] = {
    'phase': '1A', 'items': 0, 'target': 100,
    'live': False, 'map': 'world', 'section': 'X'
}
s['queue'].append(new_atlas)
json.dump(s, open('pangea_state.json','w'), indent=2)
print('added', new_atlas)
"
python3 pangea_orchestrator.py verify
```

---

## Troubleshooting

**"Item count didn't increase by 25 after batch write"**
The heredoc write failed silently. The batch-file merge strategy prevents this —
ensure Claude Code is writing items to a separate `.py` file first, then merging.
Never write directly to the HTML file for data phases.

**"pangea_validate.py exits 1 after what looks like a complete atlas"**
Most common causes:
- Lens not sorted alphabetically — check `LENSES` array order
- Civilitas terminology leaked — `grep -i "civilizat" ATLAS/index.html`
- WOMEN object empty — must have ≥ 5 entries
- Meta description count doesn't match `ITEMS` length

**"Claude Code says it can't find a section in index.html"**
The homepage card uses a display name with special characters (e.g. `Exōdus`, `Lūdus`).
Check the `homepage_name` field in `pangea_state.json` for that atlas.

**"State file and git log disagree"**
Always trust git log over state file. Manually advance state to match last commit:
`python3 pangea_orchestrator.py advance ATLAS PHASE`

---

## File reference

| File | Purpose | Edit manually? |
|---|---|---|
| `pangea_state.json` | Progress tracker | Only for corrections |
| `pangea_orchestrator.py` | State machine | No |
| `pangea_validate.py` | Go-live gate | No |
| `MASTER_PROMPT.md` | Claude Code prompt | No |
| `CLAUDE.md` | Build bible | No |
| `civilitas/index.html` | Gold standard template | No |
