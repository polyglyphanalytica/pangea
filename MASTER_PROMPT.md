# PANGEA PROJECT — MASTER BUILD PROMPT
# Paste this into a fresh Claude Code session.
# Runs continuously. No artificial pauses.

---

You are the autonomous build agent for The Pangea Project.

## ABSOLUTE RULE — READ FIRST

When the orchestrator says WRITE_ITEM: write ONE item. Then stop.
Run the verify grep. Run item_done. Run the orchestrator again.
The orchestrator will say WRITE_ITEM again. Write ONE more item.
Repeat 100 times until the atlas is done.

Writing multiple items per WRITE_ITEM call is a violation of these instructions.
If you find yourself writing item 3 before item 2 is committed, stop immediately.

---

## SETUP

1. git fetch origin && git pull origin HEAD
2. Read CLAUDE.md fully.
3. python3 pangea_orchestrator.py verify
4. python3 pangea_orchestrator.py status
5. python3 pangea_orchestrator.py → execute immediately.

---

## THE LOOP

After every action: call `python3 pangea_orchestrator.py` and execute what it returns.
Never pause. Never wait for confirmation.

---

## EXECUTE_PHASE

### Phase 1A
```bash
cp civilitas/index.html ATLAS/index.html
```
Verify it opens. Commit: "ATLAS: Phase 1A — copy from civilitas"
`python3 pangea_orchestrator.py advance ATLAS 1A`

### Phases 1B / 1C / 1D
Adapt metadata, logo, domain language per CLAUDE.md Section 2.
No colour changes. No Herstory changes. Commit after each. Advance after each.

### Phase 1E (sky atlas only)
Replace only renderWorldMap() and itemPt(). Commit. Advance.

### Phase 1F
Set all data arrays to empty stubs in the file:
```
const LENSES=[];const ERAS=[];const FP_LABELS=[];const FP_KEYS=[];
const ITEMS=[];const TRANSMISSIONS=[];const HERITAGE_REGIONS={};const WOMEN={};
```
Verify loads with no console errors.
Commit: "ATLAS: Phase 1F — shell complete"
`python3 pangea_orchestrator.py advance ATLAS 1F`

### Phase 3
Write LENSES (sorted a–z by lbl), ERAS, FP_LABELS, FP_KEYS,
TRANSMISSIONS (15–25 chains), HERITAGE_REGIONS, WOMEN (populated).
Commit: "ATLAS: Phase 3 — constants and chain data"
`python3 pangea_orchestrator.py advance ATLAS 3`

### Phase 5
Verify all 5 modes work.
Commit: "ATLAS: Phase 5 — all modes verified"
`python3 pangea_orchestrator.py advance ATLAS 5`

### Phase 6
```bash
python3 pangea_validate.py ATLAS
```
Exit 0 → commit "ATLAS: Phase 6 — validation passed", advance, proceed to GO_LIVE.
Exit 1 → fix every FAIL, re-run, do not advance until clean.
`python3 pangea_orchestrator.py advance ATLAS 6`

---

## WRITE_ITEM — ONE ITEM PER CALL, NO EXCEPTIONS

The orchestrator emits this once per item. You execute it once per item.
The orchestrator output includes an `instruction` field. Read it. Follow it exactly.
Do not write the next item until the current item is committed and item_done is called.

The orchestrator output will look like:
```json
{
  "action": "WRITE_ITEM",
  "atlas": "dynastia",
  "item_number": 7,
  "items_so_far": 6,
  "target": 100,
  "remaining": 94
}
```

### What to do for WRITE_ITEM

1. Look at the existing ITEMS array in ATLAS/index.html to understand the structure.
   Also look at bellum/index.html or numen/index.html for data pattern reference.

2. Write exactly ONE new item using Python str_replace into the ITEMS array.
   Append it before the closing `];` of the ITEMS array.

   The item structure is (adapt field names to the atlas domain):
   ```javascript
   {id:'unique_id', nm:'Display Name', st:-500, en:1200,
    lat:48.8, lng:2.3, fp:[3,7,2,8,1,5],
    d:{
      origins:'2-4 sentences of substantive historically accurate content. Escape apostrophes with backslash.',
      geography:'2-4 sentences.',
      society:'2-4 sentences.',
      religion:'2-4 sentences.',
      economy:'2-4 sentences.',
      military:'2-4 sentences.',
      science:'2-4 sentences.',
      arts:'2-4 sentences.',
      decline:'2-4 sentences.',
      legacy:'2-4 sentences.',
      herstory:'2-4 sentences specifically about women\'s roles.',
      language:'2-4 sentences.',
      trade:'2-4 sentences.',
      environment:'2-4 sentences.',
      politics:'2-4 sentences.',
      philosophy:'2-4 sentences.',
      technology:'2-4 sentences.',
      medicine:'2-4 sentences.',
      architecture:'2-4 sentences.',
      foodways:'2-4 sentences.'
    },
    conns:['other_item_id','another_id']
   },
   ```
   Use the LENSES defined for THIS atlas — check the LENSES array in the file.
   All d{} keys must match the lens IDs exactly. No stubs. No empty strings.

3. Verify the item was written:
   ```bash
   grep -c "^{id:'" ATLAS/index.html
   ```
   Must be exactly item_number. If not — fix before continuing.

4. Commit: "ATLAS: item N/100 — Item Name"

5. Update state:
   ```bash
   python3 pangea_orchestrator.py item_done ATLAS
   ```

6. Call `python3 pangea_orchestrator.py` → write the next item immediately.

---

## GO_LIVE

1. `python3 pangea_validate.py ATLAS` — must exit 0.
2. In index.html update the card:
   - class="card card--forthcoming" → class="card card--live"
   - Remove <span class="coming-soon">Coming Soon</span>
   - Add <span class="status status--live">Live</span> as first child
   - Wrap content in <a href="ATLAS/index.html">...</a>
3. Add to JSON-LD hasPart: {"@type":"Dataset","name":"NAME","url":"https://polyglyphanalytica.github.io/pangea/ATLAS/"}
4. Verify: grep -c "card--live" index.html → increased by 1.
5. Commit: "ATLAS: go-live — homepage activated"
6. `python3 pangea_orchestrator.py golive ATLAS`
7. Call `python3 pangea_orchestrator.py` → begin next atlas.

---

## CLEANUP
`python3 pangea_orchestrator.py golive ATLAS` → continue.

## ALL_DONE
`python3 pangea_orchestrator.py status` → stop.

---

## HARD STOPS (real failures only)

- Item count did not increase after a WRITE_ITEM → stop, report, do not continue.
- pangea_validate.py still failing after two fix attempts → stop, report.
- A git commit fails → stop, report.
- civilitas/index.html or pangea_state.json missing → stop, report.

Do NOT stop for: phase completions, item completions, atlas completions, go-lives.
The orchestrator chains automatically after advance, item_done, and golive calls.

---

## HARD CONSTRAINTS

- Never change any CSS variable value. Amber/gold palette is fixed.
- Never rename/recolour/remove Herstory. ♀ Herstory, #c060a0, toggleHerstory().
- Never build two atlases simultaneously.
- Never skip a phase.
- Never activate a card before pangea_validate.py exits 0.
- Never rewrite the civilitas engine — copy and adapt only.
- Check bellum or numen for data patterns before inventing new schemas.

---

Begin: python3 pangea_orchestrator.py verify → enter the loop.
