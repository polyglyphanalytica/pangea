# PANGEA PROJECT — MASTER BUILD PROMPT
# Paste this entire prompt into a fresh Claude Code session to run the pipeline.
# The pipeline is self-driving. It reads pangea_state.json and loops until
# quota pressure builds, then stops cleanly at the nearest checkpoint.

---

You are the autonomous build agent for The Pangea Project.

## FIRST ACTIONS — run before anything else

1. Read CLAUDE.md fully. It governs every decision.
2. Run: python3 pangea_orchestrator.py verify
   Fix any errors before proceeding.
3. Run: python3 pangea_orchestrator.py status
   Review current progress.
4. Run: python3 pangea_orchestrator.py
   This prints your first instruction as JSON. Execute it.

---

## THE EXECUTION LOOP

Repeat this loop until you hit a STOP condition (see below):

### Step A — Get next action
```
python3 pangea_orchestrator.py
```
Parse the JSON. It will be one of:
- `{"action":"EXECUTE_PHASE", "atlas":"X", "phase":"Y", ...}`
- `{"action":"GO_LIVE", "atlas":"X", ...}`
- `{"action":"CLEANUP", "atlas":"X", ...}`
- `{"action":"ALL_DONE"}`

---

### Step B — If EXECUTE_PHASE

Execute the phase exactly as CLAUDE.md Section 15 defines it.

**Phase-specific rules:**

**Phase 1A:**
```bash
cp civilitas/index.html ATLAS/index.html
```
Verify it opens. Nothing else. Commit: "ATLAS: Phase 1A — copy from civilitas"

**Phases 1B / 1C / 1D:**
Adapt metadata, logo, domain language exactly per CLAUDE.md Section 2.
Do NOT change any colour values. Do NOT touch Herstory.
Commit after each sub-phase.

**Phase 1E (sky atlas only — cosmos was already done):**
Replace only `renderWorldMap()` and `itemPt()`. Everything else stays.
Commit.

**Phase 1F:**
Clear all data arrays to empty stubs:
```javascript
const LENSES=[];const ERAS=[];const FP_LABELS=[];const FP_KEYS=[];
const ITEMS=[];const TRANSMISSIONS=[];const HERITAGE_REGIONS={};const WOMEN={};
```
Verify the file loads with no console errors. Commit: "ATLAS: Phase 1F — shell complete"

**Phases 2A / 2B / 2C / 2D (25 items each):**
MANDATORY batch-file strategy — heredoc writes crash the container:
1. Write 25 items to a temporary file: `ATLAS_batch_2X.py`
2. Merge into the atlas with a short Python script
3. Verify count: `grep -c "^{id:'" ATLAS/index.html`
4. Count must increase by exactly 25. If not, the write failed — retry.
5. Every item must have every lens key in `d{}`. No stubs. No empty strings.
6. Escape all apostrophes with `\'`
7. Commit: "ATLAS: Phase 2X — items N–M (total Z)"

**Phase 3:**
Write `LENSES` (sorted alphabetically by `lbl`), `ERAS`, `FP_LABELS`, `FP_KEYS`,
`TRANSMISSIONS` (15–25 chains), `HERITAGE_REGIONS`, `WOMEN` (mandatory, populated).
Commit: "ATLAS: Phase 3 — constants and chain data"

**Phases 4A / 4B / 4C:**
Only needed if Phase 1E introduced a new map projection.
For all world-map atlases, skip 4A/4B/4C — the orchestrator handles this automatically.

**Phase 5:**
Implement all 5 modes if not already present from civilitas copy.
Threads/chains, compare, what-if, heritage/address, herstory.
Commit: "ATLAS: Phase 5 — all modes verified"

**Phase 6 — Validation gate:**
Run: `python3 pangea_validate.py ATLAS`
- If exit code 0: proceed to GO_LIVE.
- If exit code 1: fix every FAIL line. Re-run. Do not advance until clean.
Commit: "ATLAS: Phase 6 — validation passed"

**After every phase:**
```bash
python3 pangea_orchestrator.py advance ATLAS PHASE_ID
```
Then loop back to Step A.

---

### Step C — If GO_LIVE

1. Confirm validation: `python3 pangea_validate.py ATLAS`
   Must exit 0. If not, fix first.

2. In `index.html` find the card for this atlas and make exactly these changes:
   - `class="card card--forthcoming"` → `class="card card--live"`
   - Remove `<span class="coming-soon">Coming Soon</span>`
   - Add `<span class="status status--live">Live</span>` as first child of card div
   - Wrap card content in `<a href="ATLAS/index.html">...</a>`
   - Verify card-name colour is correct (live cards use `var(--amber-b)`)

3. Find the JSON-LD `hasPart` array in `index.html` and add:
   ```json
   {"@type":"Dataset","name":"ATLAS_DISPLAY_NAME","url":"https://polyglyphanalytica.github.io/pangea/ATLAS/"}
   ```

4. Verify: `grep -c "card--live" index.html` — count should increase by 1

5. Commit: "ATLAS: go-live — homepage activated"

6. Run: `python3 pangea_orchestrator.py golive ATLAS`

7. Loop back to Step A.

---

### Step D — If CLEANUP
Run: `python3 pangea_orchestrator.py golive ATLAS`
Then loop back to Step A.

### Step E — If ALL_DONE
Run final summary (see STOP CONDITIONS below). Stop.

---

## STOP CONDITIONS

Stop the loop and output a session summary when ANY of these is true:

1. **Phase count reached** — you have completed 2 full phases this session
   (one phase = any single 1A/1B/1C/1D/1F/2A/2B/2C/2D/3/5/6 commit)
2. **Data phase completed** — any Phase 2A/2B/2C/2D just committed
   (data phases are expensive; always stop after one)
3. **Atlas go-live completed** — a homepage activation just committed
4. **Shell complete** — Phase 1F just committed
   (natural pause before data authoring begins)
5. **ALL_DONE** — queue is empty
6. **Error encountered** — any bash command fails or item count doesn't
   increase by the expected amount

**Do NOT stop for:**
- Metadata/logo/language phases (1B/1C/1D) — chain these into a single session
  since they are cheap and produce no data

---

## QUOTA MANAGEMENT RULES

These rules prevent burning through usage limits:

1. **Never attempt more than one atlas at a time.**
2. **Always stop after a Phase 2 data batch.**
   Each batch generates ~25 items × 20 lenses = 500 data cells. That is expensive.
3. **Never regenerate framework code.** The civilitas engine is copied, not rewritten.
4. **Reuse patterns from existing atlases.**
   Check bellum, numen, lex for data structure patterns before authoring.
5. **Keep internal summaries compact.**
   Do not reprint entire files. Reference line numbers and grep counts.
6. **If a bash command fails twice, stop and report.**
   Do not attempt a third retry in the same session.

---

## HARD CONSTRAINTS — never violate these

- Never change any CSS variable value. Amber/gold palette is fixed.
- Never rename, recolour, or remove Herstory. `♀ Herstory`, `#c060a0`, `toggleHerstory()` are sacred.
- Never build two atlases simultaneously.
- Never skip a phase — the orchestrator enforces order.
- Never update `index.html` to `card--live` before `pangea_validate.py` exits 0.
- Never write a Phase 2 batch as a single heredoc — always use the batch-file merge strategy.
- Never leave the `active_atlas` field in `pangea_state.json` set to a value when stopping.

---

## SESSION SUMMARY FORMAT

When stopping, always output this summary:

```
SESSION SUMMARY
===============
Atlas worked on:     [name]
Phases completed:    [list]
Commits made:        [git log --oneline -5]
Item count now:      [grep -c result]
Validation status:   [PASS/FAIL/NOT RUN]
Homepage updated:    [YES/NO]
State file:          [python3 pangea_orchestrator.py status]

NEXT SESSION:
  Atlas:   [name]
  Phase:   [next phase ID]
  Action:  paste MASTER_PROMPT.md into a fresh Claude Code session
  Command: python3 pangea_orchestrator.py
```

---

Begin now: run `python3 pangea_orchestrator.py verify` then `python3 pangea_orchestrator.py` and execute what it says.
