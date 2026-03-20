# PANGEA PROJECT — MASTER BUILD PROMPT
# Paste this into a fresh Claude Code session.
# Run continuously until ALL_DONE or a real failure.

---

You are the autonomous build agent for The Pangea Project.

## SETUP — run once before the loop

1. Read CLAUDE.md fully. It governs every decision.
2. python3 pangea_orchestrator.py verify
3. python3 pangea_orchestrator.py status
4. python3 pangea_orchestrator.py → execute the result immediately.

---

## THE LOOP

Call `python3 pangea_orchestrator.py` after every action.
Execute what it returns. Never pause between phases or atlases.

---

### EXECUTE_PHASE

**Phase 1A**
  cp civilitas/index.html ATLAS/index.html
  Verify it opens.
  Commit: "ATLAS: Phase 1A — copy from civilitas"
  python3 pangea_orchestrator.py advance ATLAS 1A

**Phases 1B / 1C / 1D**
  Adapt metadata, logo, domain language per CLAUDE.md Section 2.
  No colour changes. No Herstory changes.
  Commit after each. Advance after each.

**Phase 1E (sky atlas only)**
  Replace only renderWorldMap() and itemPt(). Nothing else.
  Commit. Advance.

**Phase 1F**
  Clear data arrays:
    const LENSES=[];const ERAS=[];const FP_LABELS=[];const FP_KEYS=[];
    const ITEMS=[];const TRANSMISSIONS=[];const HERITAGE_REGIONS={};const WOMEN={};
  Verify loads with no console errors.
  Commit: "ATLAS: Phase 1F — shell complete"
  python3 pangea_orchestrator.py advance ATLAS 1F

**Phases 2A through 2J (10 items each)**
  Batch-file merge strategy — never write directly to the HTML file:
  1. Write 10 items to ATLAS_batch_2X.py
  2. Merge into atlas with a short Python merge script
  3. Verify: grep -c "^{id:'" ATLAS/index.html → must increase by exactly 10
  4. Every item: all lens keys in d{}, no stubs, no empty strings, apostrophes escaped with \'
  Commit: "ATLAS: Phase 2X — items N–M"
  python3 pangea_orchestrator.py advance ATLAS 2X

**Phase 3**
  Write LENSES (sorted alphabetically by lbl), ERAS, FP_LABELS, FP_KEYS,
  TRANSMISSIONS (15–25 chains), HERITAGE_REGIONS, WOMEN (populated, mandatory).
  Commit: "ATLAS: Phase 3 — constants and chain data"
  python3 pangea_orchestrator.py advance ATLAS 3

**Phases 4A / 4B / 4C**
  Only for sky atlases. Orchestrator skips for world-map atlases automatically.

**Phase 5**
  Verify all 5 modes work.
  Commit: "ATLAS: Phase 5 — all modes verified"
  python3 pangea_orchestrator.py advance ATLAS 5

**Phase 6**
  python3 pangea_validate.py ATLAS
  Exit 0 → commit "ATLAS: Phase 6 — validation passed", advance, proceed to GO_LIVE.
  Exit 1 → fix every FAIL, re-run, do not advance until clean.
  python3 pangea_orchestrator.py advance ATLAS 6

---

### GO_LIVE

1. python3 pangea_validate.py ATLAS — must exit 0.
2. In index.html update the atlas card:
   - class="card card--forthcoming" → class="card card--live"
   - Remove <span class="coming-soon">Coming Soon</span>
   - Add <span class="status status--live">Live</span> as first child
   - Wrap content in <a href="ATLAS/index.html">...</a>
3. Add to JSON-LD hasPart in index.html:
   {"@type":"Dataset","name":"NAME","url":"https://polyglyphanalytica.github.io/pangea/ATLAS/"}
4. grep -c "card--live" index.html → must increase by 1.
5. Commit: "ATLAS: go-live — homepage activated"
6. python3 pangea_orchestrator.py golive ATLAS
7. Call python3 pangea_orchestrator.py → begin next atlas immediately.

---

### CLEANUP
  python3 pangea_orchestrator.py golive ATLAS → continue.

### ALL_DONE
  git log --oneline -10
  python3 pangea_orchestrator.py status
  Stop.

---

## STOP ONLY FOR REAL FAILURES

- Batch write did not produce exactly 10 new items
- pangea_validate.py still failing after two fix attempts
- A git commit fails
- civilitas/index.html or pangea_state.json not found
- Claude Code context window genuinely full

Do not stop for: phase completions, atlas completions, go-lives.
After any real failure: report exact error, last commit, and next action.

---

## HARD CONSTRAINTS

- Never change any CSS variable value. Amber/gold palette is fixed.
- Never rename, recolour, or remove Herstory. ♀ Herstory, #c060a0, toggleHerstory().
- Never build two atlases simultaneously.
- Never skip a phase.
- Never activate homepage card before pangea_validate.py exits 0.
- Never write Phase 2 data as a heredoc — always batch-file merge.
- Never rewrite the civilitas engine — copy it, adapt it.
- Reuse data patterns from bellum, numen, lex before authoring new schemas.

---

Begin: python3 pangea_orchestrator.py verify → enter the loop.
