# Pangea Project — Drift Specifications

> This document records deliberate, approved departures from `CLAUDE.md` that apply across **all** Pangea atlases. Where a drift spec conflicts with CLAUDE.md, this document takes precedence. Atlas-specific deviations should be noted at the end of this file under [Per-Atlas Notes](#per-atlas-notes).

---

## 1. Map Labels — Hover-Only

**CLAUDE.md default:** Persistent text labels render below every active item marker on the map.

**Revised behaviour:** No persistent labels. Labels appear only in two contexts:

1. **Selected item** — when an item is open in the drawer, its name renders in gold (`#f0d060`) below its enlarged dot. This label is removed when the drawer closes or another item is selected.
2. **Hover tooltip** — moving the cursor within the hit threshold of any unselected active dot shows a pill tooltip (dark background, `--bdr` border, `--txt` text, Cinzel font) floating above the dot. It clears on mouseout, on click, and when the cursor leaves the SVG.

**Rationale:** At 100+ items, persistent labels overlap catastrophically in any geographically dense region. Overlapping labels actively mislead — a user reads the wrong label for a nearby dot. Hover-only eliminates all overlap while preserving full discoverability. The selected-item label is retained because that dot is already visually differentiated and surrounding items are contextually suppressed.

**Implementation:**
- `label-layer` SVG group receives only the selected item label, gated on `isSel`
- `hover-label-layer` SVG group sits above `mark-layer`, managed by `_renderHoverLabel(c)`
- `_onMapMouseMove` fires on `window.mousemove`, separate from the drag handler `_onMouseMove`
- `itemClick()` calls `_renderHoverLabel(null)` before `navigateToItem()` to clear any residual hover label
- Touch devices: hover layer is never populated. Selected-item label still works.

---

## 2. Inactive Items — Fully Hidden on Timeline Scrub

**CLAUDE.md default:** Items outside the current timeline window dim to `opacity: 0.06` — nearly invisible but present on the map.

**Revised behaviour:** Items outside the current timeline window render at `opacity: 0`. They are completely absent from the map. The ghost dot branch (the `else` path in the dot renderer) is gated on `op > 0` and therefore also suppresses.

**Rationale:** Showing a ghost of an item that has a defined end date implies continuity that does not exist. The `0.06` value in civilitas was appropriate for civilizations (cultural influence persists after political collapse) but is inappropriate for items with hard historical end-points — extinct religions, ended conflicts, collapsed economies. Complete removal is honest.

**Herstory and Heritage modes are unaffected** — those modes use their own opacity paths (`0.15` and `0.06` respectively), so dimming across the full item set still works correctly in those contexts.

**Implementation:**
```javascript
// CLAUDE.md default:
const op = on ? (herstory && !womenCount ? 0.35 : 1) : (heritageIds ? (isHeritage ? 0.45 : 0.06) : herstory ? 0.15 : 0.06);

// Drift:
const op = on ? (herstory && !womenCount ? 0 : 1) : (heritageIds ? (isHeritage ? 0.45 : 0.06) : herstory ? 0.15 : 0);
```

---

## 3. Herstory — Filter Mode, Not Overlay Mode

**CLAUDE.md default:** Herstory is a toggleable overlay. When active, all items remain on the map. Items *with* WOMEN entries show the pink/magenta marker (`#c060a0`); items *without* WOMEN entries are dimmed to `opacity: 0.35` but remain visible.

**Revised behaviour:** Herstory is a **filter**. When active:

- Items **with** WOMEN entries: fully visible at `opacity: 1` with the `#c060a0` marker colour.
- Items **without** WOMEN entries: **completely hidden** (`opacity: 0`). They do not appear on the map.

**Rationale:** Showing ghost markers for items without women's entries implies those items simply have no notable women, when the real cause is often historical erasure, inaccessibility of records, or suppression. Removing them entirely focuses the map on what is documented without implying a negative judgment about the rest.

**Implementation:** Change the `herstory && !womenCount` opacity value from `0.35` to `0` in the `op` formula (see Drift 2 above). The ghost dot branch is already gated on `op > 0`, so no further change is needed.

---

## 4. Herstory Drawer — Dedicated Women Panel

**CLAUDE.md default:** When Herstory is active and an item is selected, the drawer shows WOMEN entries as part of the standard lens display — the Women & Gender lens renders alongside all other active lenses in the normal lens row layout.

**Revised behaviour:** When Herstory is active and an item is selected, the drawer shows a **dedicated Herstory panel** instead of the standard lens layout. This panel:

- Replaces lens content entirely for the duration of the Herstory session
- Shows each WOMEN entry as a named card: name, role, year, and biographical description
- Does not show the lens row, fingerprint chart, or other standard drawer content
- Has its own heading and visual treatment distinct from the lens grid

The domain's Women & Gender lens (e.g. `id: 'women'`) continues to exist in the LENSES array and is selectable outside of Herstory mode. It covers the domain's structural and social gender history. It is **not** the same content as the WOMEN biographical entries and must not be treated as such.

**Rationale:** Folding named biographical entries into a lens row treats individual women as just another interpretive angle, equivalent to architecture or music. A dedicated panel gives their contributions distinct visual weight and makes the Herstory session feel purposeful. The Women & Gender lens covers the structural and doctrinal dimension; the Herstory panel covers the biographical and individual dimension. They are complementary, not duplicative.

---

## 5. CDN Source — jsdelivr Only

**CLAUDE.md:** Specifies `cdn.jsdelivr.net` for D3 and TopoJSON.

**Confirmed and enforced:** All atlas script tags must load D3 and TopoJSON from `cdn.jsdelivr.net` exclusively. `cdnjs.cloudflare.com` is not permitted. Correct tags:

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
```

This is not a departure from CLAUDE.md — it is a clarification that supersedes any atlas file that was built with the wrong CDN source.

---

## Per-Atlas Notes

### Numen (`numen/index.html`)

- **Founding & Origins lens** (`id: 'founding'`): a 20th content lens added between Ethics & Morality and Interfaith Dialogue. No equivalent in civilitas. Covers the historical founder, founding event, founding date/period, and origin conditions of each religious tradition.
- **Maya religion end date**: `e:1697` (fall of Tayasal, last independent Maya polity). Corrected from the erroneous `e:2024`.
- All five generic drifts above apply. Drift 4 (dedicated Herstory drawer) is **specified but not yet implemented** as of March 2026.

---

*Last updated: March 2026. Append new approved drifts before implementation. Per-atlas deviations go in the section above.*
