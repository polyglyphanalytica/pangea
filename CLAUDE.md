# Pangea Atlas — Complete Build Bible

> This document is the authoritative guide for building any atlas in The Pangea Project. Every new atlas — regardless of subject — must follow everything here. It is written for AI agents starting a build in a fresh chat session. Read it fully before writing a single line of code.

---

## 1. The Prime Directive

**`civilitas/index.html` is the gold standard for everything.**

All atlases must match civilitas exactly in:
- HTML document structure
- CSS architecture and variable system
- JavaScript engine patterns
- UX, interaction, and mode behaviour
- Content quality and depth
- Accessibility standards

When in doubt about how anything should work, look at civilitas first. Do not invent new patterns. Adapt civilitas patterns to the subject domain — do not replace them.

---

## 2. The Copy-First Build Approach

**Every new atlas starts as a copy of `civilitas/index.html`. Never build from scratch.**

This is the single most important process rule. Building from scratch violates the prime directive, wastes effort, and introduces drift from the tested reference implementation.

### The correct workflow for every new atlas

```
cp civilitas/index.html atlasname/index.html
```

Then work through these adaptations in order:

1. **Metadata** — Update `<title>`, `<meta name="description">`, Open Graph tags, Twitter tags, JSON-LD, and the favicon emoji
2. **Logo text** — Replace `CIVILITAS` and `The Human Atlas` in the header with the new atlas name and subtitle
3. **Domain language** — Find and replace civilitas-specific strings:
   - `CIVS` → `ITEMS`
   - `civClick` → `itemClick`
   - `navigateToCiv` → `navigateToItem`
   - `"Civilization Arc"` → `"[Subject] Arc"`
   - `"Concept Threads"` → `"[Domain] Chains"` (or equivalent)
   - `"Heritage"` → `"[Domain equivalent]"`
   - `"civilizations active"` → `"[items] known"` (or equivalent)
   - All ARIA labels and map descriptions
   - **Do NOT touch Herstory** — the burger label `♀ Herstory`, the `#c060a0` marker colour, the `WOMEN` object, the `toggleHerstory()` function, and all related IDs are copied verbatim and never changed
   - **Do NOT touch the colour scheme** — the entire `:root`, `[data-theme="light"]`, and `@media prefers-color-scheme` blocks are copied verbatim. No values change.
4. **Map** — If using the civilitas world map, keep `renderWorldMap()` exactly as-is. If using a different coordinate space (e.g. sky atlas), replace only the map rendering function and `itemPt()` — everything else stays
5. **Data** — Replace `LENSES`, `ERAS`, `FP_LABELS`, `FP_KEYS`, `ITEMS`, `TRANSMISSIONS`, `HERITAGE_REGIONS` with the new domain's data. Populate the `WOMEN` object for Herstory — this is mandatory.
6. **Timeline labels** — Update the `<span class="tl-lbl">` labels to reflect the new timeline range
7. **About modal** — Rewrite the about modal content for the new atlas
8. **Back link** — Verify `../index.html` points correctly to the Pangea homepage

### Why copy-first is mandatory

- **Correctness** — civilitas's zoom/pan, mobile sheet, lens dropdown, thread animation, URL state, and cluster picker are all intricate and already correct. Rewriting them from memory introduces bugs.
- **Continuous experience** — A user moving between Civilitas, Bellum, Numen, Cosmos, and any other atlas must feel they are in the same product. Same amber/gold palette. Same Herstory feature. Same layout. Same keyboard behaviour. Same interactions. Every pixel of drift erodes that experience.
- **Efficiency** — The CSS is ~80% identical across atlases. The JS engine is ~70% identical. Rewriting is pure overhead with no upside.

**What changes per atlas:**
- The `<title>`, metadata, favicon, and about modal content
- The logo text in the header
- Domain-specific strings (arc name, mode names, count label, ARIA labels)
- The map type if non-geographic (sky atlas, abstract space, etc.)
- All data arrays: `ITEMS`, `LENSES`, `ERAS`, `FP_LABELS/KEYS`, `TRANSMISSIONS`, `HERITAGE_REGIONS`, `WOMEN`

**What never changes:**
- The entire colour scheme — every CSS variable value, in both themes
- The `Herstory` feature — name, colour, logic, structure
- The full JS engine — zoom/pan, modes, URL state, timeline, drawer, cluster picker
- The HTML structure and layout
- The typography stack

### What Phase 1 actually means for a new atlas

Phase 1 is not "write a new shell." Phase 1 is a sequence of small commits, each building on the last:

- **Phase 1A** — `cp civilitas/index.html atlasname/index.html`. Verify it opens. Nothing else.
- **Phase 1B** — Update metadata only: `<title>`, description, OG tags, Twitter tags, JSON-LD, favicon emoji, canonical URL. Commit.
- **Phase 1C** — Update logo text (header `CIVILITAS` → new name, subtitle). Update about modal content. Update back-link text if needed. Commit.
- **Phase 1D** — Find/replace all domain language (see Section 3 adaptation list). Update timeline labels, count label, ARIA labels, map aria-label, arc name, mode panel title. Commit.
- **Phase 1E** — If using a non-geographic map (e.g. sky atlas): replace only `renderWorldMap()` and `itemPt()`. Leave all CSS, all other engine code, and all colour values completely untouched. Commit.
- **Phase 1F** — Clear all data arrays to empty: `ITEMS=[]`, `TRANSMISSIONS=[]`, `HERITAGE_REGIONS={}`, `WOMEN={}`, `LENSES=[]`, `ERAS=[]`. Verify the file opens and shows the welcome state with no errors. Commit.

The result after Phase 1F is a working, styled, interactive shell that is pixel-for-pixel identical to civilitas in colour, layout, and behaviour — with only text and domain language changed. **This is the only acceptable starting point for data phases.**

---

## 3. The One-File Rule

Every atlas is a **single self-contained HTML file**. No build tools. No bundlers. No separate CSS or JS files. No backend. No database. The file must open correctly by double-clicking it locally, with no server required, with the sole exception of:

- Google Fonts (loaded from `fonts.googleapis.com`)
- The world map TopoJSON (loaded from jsDelivr CDN — see Section 9)
- D3 and TopoJSON libraries (loaded from CDN — see Section 9)

The file path follows the pattern: `atlasname/index.html`

---

## 4. Item Count & Scale

- **Minimum 100 items per atlas.** This is non-negotiable. The meta description tag in the `<head>` must state the item count. Do not ship with fewer.
- Civilitas has 100 items and 30 lenses — treat this as the reference scale.
- All other atlases: minimum 100 items, 20 lenses minimum.
- Never assume a lower count is acceptable. Verify the meta description against the actual `ITEMS` array length.

---

## 5. Document Structure

The HTML file is always structured in exactly this order:

```
<!DOCTYPE html>
<html lang="en">
<head>
  <!-- charset, viewport, title -->
  <!-- SEO meta tags (description, keywords, author, robots, canonical) -->
  <!-- Open Graph tags -->
  <!-- Twitter card tags -->
  <!-- JSON-LD structured data -->
  <!-- Favicon (inline SVG data URI) -->
  <!-- Google Fonts link -->
  <style>
    /* ALL CSS — dark theme :root vars first, then light theme overrides,
       then @media prefers-color-scheme, then all component styles */
  </style>
</head>
<body>
  <!-- Skip link (accessibility) -->
  <!-- <header> with logo, era display, count display, burger menu -->
  <!-- Thread/chain panel (fixed left, hidden by default) -->
  <!-- Share toast -->
  <!-- <div class="main"> containing: -->
  <!--   map-tl-col (SVG map + timeline bar) -->
  <!--   info-panel (right drawer) -->
  <!-- About modal -->
  <script>
    /* ALL JavaScript — data first, then engine, then boot */
  </script>
</body>
</html>
```

No exceptions. Do not put `<script>` tags in `<head>`. Do not split CSS across multiple `<style>` blocks.

---

## 6. CSS Architecture

### 6.1 CSS Variable System

Every atlas uses the same CSS variable names **and the same CSS variable values**. Nothing changes between atlases.

**Dark theme (`:root` — always default):**
```css
:root {
  --bg:        /* near-black background */
  --panel:     /* slightly lighter panel bg */
  --panel2:    /* slightly lighter still, for nested panels */
  --amber:     /* primary accent colour (named amber regardless of actual hue) */
  --amber-b:   /* brighter/lighter variant of accent */
  --amber-d:   /* dark variant of accent */
  --amber-x:   /* accent with ~14% opacity — hover states */
  --amber-xx:  /* accent with ~8% opacity — subtle fills */
  --txt:       /* primary text — near-white */
  --txt2:      /* secondary text — slightly dimmer */
  --txt3:      /* tertiary text — subdued labels */
  --bdr:       /* primary border — accent at ~22% opacity */
  --bdr2:      /* secondary border — accent at ~10% opacity */
  --hint:      /* map hint text */
  --tl-bg:     /* timeline bar background */
  --hdr-bg:    /* header background */
  --conn-bdr:  /* connection item borders */
  --shadow:    /* box shadows */
  /* Map-specific: --land, --land-s, --ocean-start, --ocean-end */
  /* (only for atlases using the world map) */
}
```

**Light theme (`[data-theme="light"]`):**
Same variable names, with appropriate light values. The accent inverts to dark-on-light. Always provide a full light theme override.

**System preference fallback:**
```css
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    /* same values as [data-theme="light"] */
  }
}
```

### 6.2 The Colour Scheme Is Fixed Across All Atlases — NEVER CHANGE IT

**This is a hard rule with zero exceptions. Do not invent a new palette. Do not change any colour value. Do not use a "thematic" colour for a new atlas.**

The Pangea Project is one product. Every atlas is a room in the same house. The amber/gold colour scheme is the visual language that makes every atlas feel like part of the same family. When a user moves from Civilitas to Bellum to Cosmos, the interface is immediately familiar because it looks identical. The subject changes. The colour does not.

**Do not do any of the following:**
- Invent a "space blue" for Cosmos
- Invent a "blood red" for Bellum (beyond the existing What-If red, which is already in civilitas)
- Invent a "nature green" for Flora
- Change `--amber` from gold to anything else
- Change `--bg` from near-black to deep navy or any other dark hue
- Change `--txt` from warm cream to cold white
- Introduce any new CSS variable not present in civilitas

**The exact values that must be copied verbatim — dark theme:**
```css
:root {
  --bg:#02040a;
  --panel:#070b12;
  --panel2:#0c1018;
  --ocean-start:#0a1628;--ocean-end:#061020;
  --land:#2a4a18;--land-s:#3a6020;
  --amber:#e89820;--amber-b:#f0b040;--amber-d:#3a2204;
  --amber-x:rgba(232,152,32,0.14);--amber-xx:rgba(232,152,32,0.08);
  --txt:#f2e8d5;--txt2:#e0d4b4;--txt3:#c8aa78;
  --bdr:rgba(232,152,32,0.22);--bdr2:rgba(232,152,32,0.10);
  --hint:rgba(224,212,180,0.65);
  --tl-bg:rgba(2,4,10,0.99);
  --hdr-bg:rgba(2,4,10,0.97);
  --conn-bdr:rgba(232,152,32,0.10);
  --shadow:rgba(0,0,0,0.6);
}
```

**The exact values that must be copied verbatim — light theme:**
```css
[data-theme="light"] {
  --bg:#f0ebe0;
  --panel:#e8e0d0;
  --panel2:#ddd4c0;
  --ocean-start:#b8cce0;--ocean-end:#a8bcd4;
  --land:#8ca860;--land-s:#7a9850;
  --amber:#4a2c00;--amber-b:#5a3800;--amber-d:#f0d8a0;
  --amber-x:rgba(122,78,0,0.10);--amber-xx:rgba(122,78,0,0.06);
  --txt:#1a1206;--txt2:#1a1206;--txt3:#2e2010;
  --bdr:rgba(122,78,0,0.28);--bdr2:rgba(122,78,0,0.14);
  --hint:rgba(30,18,6,0.6);
  --tl-bg:rgba(236,228,214,0.99);
  --hdr-bg:rgba(236,228,214,0.97);
  --conn-bdr:rgba(122,78,0,0.12);
  --shadow:rgba(0,0,0,0.18);
}
```

**The `@media prefers-color-scheme` block** must duplicate the light theme values exactly — copy from civilitas verbatim.

**Special-state colours** (these are already in civilitas and are equally fixed across all atlases):
- Herstory marker: `#c060a0`
- Heritage/Address highlight: `#4a9fc0`
- What-If broken path: `#e8251a`
- Selected marker: `#f0d060`
- Herstory dimmed marker: `#884468`

No new special-state colours may be introduced. If a new atlas domain seems to need a new special colour, it doesn't — use the existing set.

**How to verify you have not changed the colour scheme:** Open your new atlas and civilitas side by side. If anything looks different in terms of colour — backgrounds, text, borders, accent, hover states — you have made an error. Fix it before proceeding to the next phase.

### 6.3 Accessibility & Contrast

**WCAG AA is the minimum standard.** Every text/background combination must meet 4.5:1 contrast ratio for normal text, 3:1 for large text and UI components.

Critical pairs to verify:
- `--txt` on `--bg` (body text on background)
- `--txt` on `--panel` (drawer text)
- `--txt2` on `--panel` (secondary text)
- `--txt3` on `--panel` (label text — this is the most likely to fail; check carefully)
- `--amber-b` on `--panel` (accent text — headings, dates)
- `--amber-b` on `--bg` (accent text on main background)
- All text in light theme — do not assume light theme passes just because dark theme does

**In light theme:** The accent colour must flip to a dark value. Light theme with a light accent on a light background will fail contrast. The `--amber-b` in light theme should be a dark, saturated version of the hue.

### 6.4 Typography

Three fonts only, always loaded from Google Fonts in one `<link>` tag:

```html
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;900&family=Cinzel+Decorative:wght@700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&display=swap" rel="stylesheet">
```

Usage rules:
- **Cinzel Decorative** — logo title, item name in drawer, modal title. Display use only.
- **Cinzel** — all UI labels, era names, lens labels, dates, button text, header counts, section headers. Always uppercase or small-caps contexts.
- **Crimson Pro** — all body/content text: overviews, lens content, connection descriptions. Italic for lens content. Default `font-family` on `body`.

Never use any other fonts. Never use system fonts for UI elements.

### 6.5 Layout

The layout is always a fixed full-screen three-part structure:

```
┌─────────────────────────────────────────┬──────────┐
│ HEADER (fixed, full width, 52px tall)   │          │
├──────────────────────────────┬──────────┤          │
│                              │          │          │
│   MAP (SVG, fills all space) │ TIMELINE │  PANEL   │
│                              │ (88px    │  (320px  │
│                              │  bottom) │  fixed)  │
└──────────────────────────────┴──────────┴──────────┘
```

- Header: `position:fixed; top:0; left:0; right:0; z-index:200`
- Main: `position:fixed; top:52px; left:0; right:0; bottom:0; display:flex`
- Map column: `display:flex; flex-direction:column; flex:1`
- Map: `flex:1; overflow:hidden`
- Timeline: `height:88px; flex-shrink:0`
- Panel: `width:320px; flex-shrink:0`

**Mobile (portrait, ≤768px):** The panel becomes a bottom sheet that slides up from the bottom, showing only a drag handle at rest. The map fills the full screen. A "map" button appears when the panel is expanded. See civilitas for the exact implementation.

---

## 7. Data Architecture

### 6.1 The ITEMS Array

Every item in the atlas is an object in the `ITEMS` array (named `CIVS` in civilitas — always rename to `ITEMS` in new atlases for clarity). Items are ordered by `s` (start year) ascending.

**Full item object shape:**
```javascript
{
  id:       'unique_snake_case_id',        // string, unique, URL-safe
  nm:       'Display Name',                // string — shown in UI
  sb:       'Subtitle · Context',          // string — shown below name
  s:        -3000,                         // number — start year (negative = BCE)
  e:        1500,                          // number — end year (use 2024 if ongoing)
  lon:      44.4,                          // number — longitude (–180 to 180) for world map
  lat:      33.3,                          // number — latitude (–90 to 90) for world map
  fp: {                                    // fingerprint radar — 6 keys, values 0–10
    key1: 8, key2: 5, key3: 7,
    key4: 6, key5: 9, key6: 4
  },
  conns:    ['id_a', 'id_b', 'id_c'],     // array of related item IDs
  overview: 'Two to four sentence overview of this item. Written as a single string with escaped apostrophes (don\'t, it\'s). Substantive, authoritative, not a Wikipedia stub.',
  disc: [                                  // optional — key figures / discoverers
    {
      nm:   'Person Name',
      role: 'Their role',
      yr:   1905,
      desc: 'Two sentences about their contribution.'
    }
  ],
  d: {                                     // lens data — one key per lens id
    lens_id_1: 'Two to four sentences of substantive content for this lens. Written as a single-line string. All apostrophes escaped. No markdown. No bullet points.',
    lens_id_2: 'Two to four sentences...',
    // ... one entry per lens
  }
}
```

**Content quality rules:**
- Every `d` field must be 2–4 sentences. Never one sentence. Never a list.
- Content must be substantive and domain-accurate. Not encyclopaedia stubs.
- Single-line strings only — no template literals with newlines inside data.
- All apostrophes escaped: `it\'s`, `don\'t`, `world\'s`.
- No markdown inside content strings (no `**bold**`, no `## headers`).
- Write in an authoritative, slightly elevated register — not academic jargon, not casual.

### 6.2 The LENSES Array

```javascript
const LENSES = [
  { id: 'lens_id', ico: '⊕', lbl: 'Label Text', col: '#hex' },
  // ...
];
```

**Critical rule: LENSES must be sorted alphabetically by `lbl`.** The lens picker renders the array as-is. An unsorted entry will appear out of place. Always verify sort order before shipping.

- `id` — snake_case, matches keys in `item.d`
- `ico` — a single Unicode character or symbol
- `lbl` — title case, shown in the dropdown
- `col` — hex colour used for the fingerprint polygon when this lens is active

Aim for 20–30 lenses. Civilitas has 30; other atlases have 20 minimum.

### 6.3 The ERAS Array

```javascript
const ERAS = [
  { y: -3000, n: 'ERA NAME' },  // y = year this era begins
  { y: -1200, n: 'NEXT ERA' },
  // ...
];
```

Era names appear in the header (`era-n` element) as the timeline scrubs. All uppercase. Typically 10–18 eras spanning the atlas's full timeline range.

### 6.4 Fingerprint Axes

Every atlas defines 6 fingerprint axes appropriate to its domain:

```javascript
const FP_LABELS = ['Axis One', 'Axis Two', 'Axis Three', 'Axis Four', 'Axis Five', 'Axis Six'];
const FP_KEYS   = ['key1',    'key2',     'key3',       'key4',      'key5',      'key6'];
```

Keys in `FP_KEYS` must match the keys used in every item's `fp` object. Values are 0–10. Design axes that are meaningfully different and reveal interesting comparisons between items.

Examples:
- Civilitas: Military · Commerce · Arts · Science · Reach · Longevity
- Cosmos: Mass · Size · Luminosity · Complexity · Reach · Age

### 6.5 The TRANSMISSIONS Array (Discovery/Influence Chains)

```javascript
const TRANSMISSIONS = [
  {
    from:    'item_id',        // origin item
    to:      'item_id',        // destination item
    concept: 'Chain Name',     // the named chain this belongs to (groups steps)
    year:    1543,             // year of transmission
    desc:    'One sentence describing this specific link.'
  },
  // ...
];
```

Aim for 15–25 named chains, each with 2–5 steps. Chains animate as gold arrows in Threads/Discovery Chains mode.

### 6.6 The HERITAGE_REGIONS Object (or equivalent)

```javascript
const HERITAGE_REGIONS = {
  'Region Name': ['item_id_a', 'item_id_b', 'item_id_c'],
  // ...
};
```

This powers the Heritage / Cosmic Address / equivalent mode. Keys are human-readable region names shown as buttons. Values are arrays of item IDs associated with that region. Aim for 8–15 regions covering the atlas's full scope.

For non-geographic atlases, this becomes a conceptual grouping (e.g. "Your Cosmic Address" → nested scale zones). The data shape is identical; only the framing changes.

---

## 8. The World Map

### 7.1 When to Use It

**Use the civilitas world map for any atlas whose items have geographic locations on Earth.** This covers all historical, cultural, economic, biological, and political atlases. Do not invent a new map; do not use a different projection.

### 7.2 CDN Dependencies (loaded in `<script>` tags before the main script)

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
```

### 7.3 TopoJSON Data Source

```javascript
fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
  .then(r => r.json())
  .then(world => {
    renderWorldMap(world);
    renderMap();
  })
  .catch(() => console.warn('World map data unavailable — using fallback'));
```

### 7.4 The Exact Projection

Copy this exactly from civilitas. Do not change scale or translate values:

```javascript
function renderWorldMap(world) {
  const svg = document.getElementById('wsvg');
  const W = 1000, H = 520;
  const proj = d3.geoMercator().scale(158).translate([W/2, H/2 + 40]);
  window._proj = proj;
  const pathGen = d3.geoPath().projection(proj);
  const land = topojson.feature(world, world.objects.land);
  const borders = topojson.mesh(world, world.objects.countries, (a, b) => a !== b);
  const graticule = d3.geoGraticule()();
  const g = document.getElementById('map-layer');
  g.innerHTML =
    `<path d="${pathGen(graticule)}" fill="none" stroke="var(--bdr2)" stroke-width=".3"/>` +
    `<path d="${pathGen(land)}" fill="var(--land)" stroke="var(--land-s)" stroke-width=".4"/>` +
    `<path d="${pathGen(borders)}" fill="none" stroke="var(--land-s)" stroke-width=".3" opacity=".6"/>`;
}
```

Map colours use CSS variables: `--land` for land fill, `--land-s` for land stroke. These must be defined in both dark and light themes.

### 7.5 Converting lon/lat to SVG Coordinates

```javascript
function itemPt(item) {
  if (!window._proj) return [item.lon * (1000/360) + 500, -item.lat * (520/180) + 260];
  return window._proj([item.lon, item.lat]);
}
```

The fallback (before the projection loads) uses a simple linear mapping. Always provide the fallback.

### 7.6 SVG Canvas

The SVG always has `viewBox="0 0 1000 520"`. The map layer `<g id="map-layer">` sits inside it. The SVG structure inside the `<svg id="wsvg">` element is always:

```html
<g id="map-layer"></g>    <!-- World map paths rendered here -->
<g id="conn-layer"></g>   <!-- Connection lines between items -->
<g id="thread-layer"></g> <!-- Thread/chain animated arrows -->
<g id="label-layer" pointer-events="none"></g> <!-- Item labels -->
<g id="mark-layer"></g>   <!-- Item marker circles -->
```

Order matters — markers must render above map paths and labels above markers.

### 7.7 When Not to Use the World Map

For atlases whose items exist in non-geographic space (e.g. Cosmos — celestial objects), use an appropriate alternative coordinate system:

- Define your own `lon`/`lat` equivalents (e.g. Right Ascension / Declination)
- Keep the same SVG canvas size (1000×520) and zoom/pan system
- Keep the same layer structure (map-layer, conn-layer, thread-layer, label-layer, mark-layer)
- Replace the world map background with an appropriate alternative (e.g. star field, abstract grid)
- The `itemPt()` function maps your coordinates to SVG x/y

---

## 9. The JavaScript Engine

### 8.1 State Variables

Always declare these at the top of the `<script>` block:

```javascript
let year = /* starting year (e.g. first item's s value) */;
let sel = null;      // currently selected item
let sel2 = null;     // second selected item (compare mode)
let mode = 'explore'; // current mode
let lenses = new Set(); // active lens IDs
let lensDD = false;  // lens dropdown open state
let activeThread = null; // active transmission chain name
// Mode-specific state:
let whatifItem = null;
let heritageRegion = null;
let herstory = false;        // Herstory toggle — identical in every atlas
```

### 8.2 The `active()` Function

Determines whether an item is visible at the current year:

```javascript
function active(item) {
  return item && year >= item.s && year <= item.e;
}
```

### 8.3 Timeline Conversion

The slider always runs 0–1000. Convert to the atlas's year range:

```javascript
const YEAR_MIN = /* e.g. -3000 */;
const YEAR_MAX = 2024;

function sliderToYear(v) {
  return Math.round(YEAR_MIN + (v / 1000) * (YEAR_MAX - YEAR_MIN));
}

function yearToSlider(y) {
  return Math.round(((y - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)) * 1000);
}
```

### 8.4 Date Formatter

```javascript
function fmt(y) {
  if (y === null || y === undefined) return '?';
  const abs = Math.abs(Math.round(y));
  return y < 0 ? `${abs} BCE` : (y === 0 ? '1 CE' : `${y} CE`);
}
```

### 8.5 Era Name Lookup

```javascript
function eraName(y) {
  let name = ERAS[0].n;
  for (const e of ERAS) { if (y >= e.y) name = e.n; }
  return name;
}
```

### 8.6 `setYear()` — The Central Update Function

When the timeline changes, `setYear()` must:
1. Update `year`
2. Sync the slider value
3. Move the thumb to the correct position
4. Update `tl-fill` width
5. Update ARIA attributes on the range input
6. Update `era-y` (formatted year display)
7. Update `era-n` (era name)
8. Update `cnt-n` (count of active items)
9. Call `renderMap()`
10. If `sel` is no longer active, call `closeInfo()`; else call `renderDrawer()`
11. Call `updateURL()`
12. If in what-if mode with an active item, re-render what-if paths

### 8.7 `renderMap()` — Marker Rendering

```javascript
function renderMap() {
  const markLayer = document.getElementById('mark-layer');
  const labelLayer = document.getElementById('label-layer');
  // Render one circle per active item
  // Selected item gets glow filter and larger radius
  // Discoverers-mode items get alternate colour
  // Heritage-mode items get blue highlight
}
```

Marker radii: standard = 5–6px at full zoom. Grow on selection. Scale inversely with zoom level so markers don't become giant when zoomed in.

### 8.8 Zoom & Pan

Copy the full zoom/pan system from civilitas verbatim. It handles:
- Mouse wheel zoom (toward cursor position)
- Mouse drag pan
- Pinch-to-zoom on touch
- Single-finger pan on touch
- ViewBox clamping to prevent panning outside the canvas
- `screenToSVG()` — converts screen coordinates to SVG space accounting for letterboxing
- Cluster picker — when 3+ items are within tap radius, show a picker instead of selecting the nearest

### 8.9 The Density Bar

A sparkline showing how many items are active at each point in the timeline. Renders as an SVG bar chart above the timeline track. Computed once at init from the ITEMS array.

### 8.10 URL State

Encode and decode state in the URL hash so that shares and bookmarks restore the exact view:

```javascript
function encodeState() {
  const params = new URLSearchParams();
  params.set('y', year);
  if (sel) params.set('c', sel.id);
  if (sel2) params.set('c2', sel2.id);
  if (lenses.size) params.set('l', [...lenses].join(','));
  if (mode !== 'explore') params.set('m', mode);
  if (activeThread) params.set('t', activeThread);
  return params.toString();
}

function decodeState() {
  // Parse window.location.hash, restore year/sel/sel2/lenses/mode/activeThread
  // Wrap in try/catch — may be sandboxed
}

function updateURL() {
  try {
    const state = encodeState();
    if (history.replaceState && window.location.href !== 'about:srcdoc') {
      history.replaceState(null, '', state ? '#' + state : '#');
    }
  } catch(e) { /* sandboxed iframe */ }
}
```

### 8.11 The `init()` Boot Sequence

Called on `DOMContentLoaded`:

```javascript
function init() {
  renderDensityBar();
  document.getElementById('tl').addEventListener('input', e => setYear(sliderToYear(e.target.value)));
  decodeState();
  renderDrawer();
  document.getElementById('tl').value = yearToSlider(year);
  setYear(year);
  // Restore thread mode if encoded in URL
  if (activeThread && mode === 'threads') {
    setTimeout(() => { setMode('threads'); activateThread(activeThread); }, 1000);
  }
  // Load world map (if using geographic map)
  fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
    .then(r => r.json())
    .then(world => { renderWorldMap(world); renderMap(); })
    .catch(() => console.warn('World map unavailable'));
  initMapInteraction();
}
document.addEventListener('DOMContentLoaded', init);
```

---

## 10. External Libraries

Always loaded from CDN in `<script>` tags immediately before the main `<script>` block. For geographic atlases:

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
```

No other external libraries are used.

---

## 11. The Five Modes

Every atlas implements all five modes. The mode names adapt to the subject domain; the UX is identical.

### Mode 1: Explore (always the default)
Standard map + drawer. Click an item to select it, read its overview and lens content, navigate connections. This is the base mode.

### Mode 2: Threads / Chains
A sliding panel opens from the left showing named transmission chains. Each chain shows a list of concept-card buttons. Selecting a chain renders the chain in the drawer and draws animated SVG arrows (dashed lines with animated `stroke-dashoffset`) on the map between linked items. The panel has back navigation from chain detail to chain list.

Domain adaptations:
- Civilitas: "Concept Threads" — ideas travelling between civilisations
- Cosmos: "Discovery Chains" — each discovery enabling the next
- Flora: "Trade Routes" — plants spreading through trade
- Bellum: "Military Threads" — tactics and weapons spreading

### Mode 3: Compare
Two items selected simultaneously. The drawer splits into two columns, each showing the same lens content for its item. A "diff" highlight marks substantially different content. Either column can be cleared and a new item selected from the map.

### Mode 4: What If
User selects one item to remove from history. The engine identifies all TRANSMISSIONS where this item appears as `from`, renders broken red dashed lines on the map, and generates a narrative in the drawer about what would not exist. Items downstream in the chain are listed as "lost."

### Mode 5: Heritage / Address / Equivalent
A region-picker grid appears in the drawer. User selects a region. Items associated with that region are highlighted in a distinct colour on the map. The drawer lists those items with brief descriptions of their connection to the region.

Domain adaptations:
- Civilitas: "Heritage" — geographic ancestry regions
- Cosmos: "Cosmic Address" — nested scale zones (Universe → Supercluster → Galaxy → Solar System)
- Numen: "Faith Heritage" — religious tradition families

### Herstory — Universal Across Every Atlas

**Herstory is not renamed, recoloured, or adapted per atlas. It is identical in every atlas.**

Herstory is a core feature of the Pangea Project, not a civilitas-specific concept. Every atlas surfaces the contributions of women in the relevant field — women scientists, mathematicians, philosophers, leaders, artists, rulers, and thinkers whose work has been overlooked, credited to others, or simply under-documented. Every subject domain has them.

**Implementation is copied verbatim from civilitas:**
- The burger menu item is labelled `♀ Herstory` in every atlas
- The badge reads `ON` when active
- The marker colour is `#c060a0` (pink-purple) — this never changes
- The `body.herstory` class is toggled — CSS targets it for map marker colouring
- The `WOMEN` object (or equivalent) maps item IDs to arrays of women figures
- Each woman entry has: `nm` (name), `role` (role/title), `yr` (year active), `desc` (2–3 sentences)
- The drawer in Herstory mode shows the woman's name in `#c060a0`, role in `--txt3`, year in `--amber-b`, and description in `--txt2`

**Every atlas must have a populated `WOMEN` object.** No atlas ships with an empty Herstory. Research the women. Every field has them — astronomy, law, economics, botany, military history, religion, linguistics. Finding them and giving them their place in the atlas is part of the work.

**Do not** rename it "Discoverers", "Pioneers", "Women in Science", or anything else. The name is Herstory. It is a deliberate piece of framing that is consistent across the project.

### Mode State Management

```javascript
function setMode(m) {
  if (m !== 'whatif') whatifItem = null;
  if (m !== 'heritage') heritageRegion = null;
  mode = m;
  ['explore','threads','compare','whatif','heritage'].forEach(id => {
    const b = document.getElementById('btn-' + id);
    if (b) { b.classList.toggle('active', id === m); b.setAttribute('aria-pressed', id === m); }
  });
  const tp = document.getElementById('thread-panel');
  if (tp) tp.classList.toggle('open', m === 'threads');
  if (m === 'threads') renderThreadConceptList();
  if (m !== 'threads') { activeThread = null; document.getElementById('thread-layer').innerHTML = ''; }
  if (m === 'compare' && !sel2) renderDrawer();
  if (m === 'explore' && sel2) sel2 = null;
  renderMap();
  renderDrawer();
  updateURL();
}
```

---

## 12. The Drawer

### 11.1 Structure

The right-side info panel always contains:
- `#drawer-top` — rendered by `renderDrawerTop()` — contains item name, subtitle, dates, lens dropdown
- `#drawer-content` — rendered by `renderDrawerContent()` — contains the current lens body, fingerprint chart, connections, discoverers

### 11.2 Welcome State

When no item is selected, the drawer shows a welcome state explaining:
- What this atlas covers (one sentence)
- The 5 modes and what each does
- "Tap any item on the map to begin"

### 11.3 The Lens Dropdown

Renders as a bordered box with a clickable header showing the current lens summary. Opens to show all lenses as checkable rows. "Arc" (the default overview state) is always the first row, separated from lenses by a divider. Multiple lenses can be active simultaneously. When lenses are active, each renders as a separate section with icon, label, and content below the item header.

### 11.4 The Fingerprint Chart

An SVG radar/spider chart with 6 axes. Rendered inline in the drawer below the lens content. Grid rings at values 2, 4, 6, 8, 10. Labels placed outside the outermost ring with anchor determined by angle (start/middle/end). The data polygon uses a transparent fill with the accent colour stroke.

### 11.5 The Span Bar

A thin horizontal bar showing the item's temporal span relative to the full atlas timeline. Labelled with start and end years.

### 11.6 Connections

Listed below the span bar. Each connection shows the connected item's name with an "ACTIVE" badge if it's visible at the current year, or "→ JUMP" if not. Clicking navigates to that item (and adjusts the timeline if needed via `navigateToItem()`).

---

## 13. The Header

Always three zones:

**Left:** Logo title (Cinzel Decorative, accent colour, 20px) + subtitle (Cinzel, txt3, 13px, uppercase, 3px letter-spacing). The subtitle is hidden on mobile.

**Centre:** Current year display (Cinzel, accent-b, 22px) + era name below it (Cinzel, txt2, 12px, uppercase).

**Right:** Item count display + burger menu button.

The burger menu contains (in order):
1. Back link → `../index.html` (The Pangea Project)
2. Divider
3. All 5 mode buttons (with `active` class on current mode)
4. The discoverers/herstory toggle button (with badge)
5. Divider
6. Theme toggle button
7. Divider
8. About button

---

## 14. Accessibility

### 13.1 Landmarks & ARIA
- `<header role="banner">`
- `<div class="main">` contains map and panel
- Timeline `<div role="navigation" aria-label="Timeline">`
- Panel `<div role="complementary" aria-label="[Atlas subject] details" tabindex="-1">`
- Thread panel `<div role="complementary" aria-label="[Mode name]">`
- About `<div role="dialog" aria-modal="true" aria-label="About [Atlas name]">`
- All mode buttons: `aria-pressed="true/false"`
- Burger: `aria-expanded`, `aria-haspopup="true"`
- Timeline range input: `aria-label`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext`
- SVG map: `role="img" aria-label="[Description]"`

### 13.2 Skip Link
Always the first child of `<body>`:
```html
<button class="skip-link" onclick="document.getElementById('info-panel').focus()">
  Skip to [subject] panel
</button>
```

### 13.3 Keyboard Navigation
- Arrow keys on the timeline: advance/retreat by 1 step (Shift: 10, Ctrl/Cmd: 50)
- Escape closes burger menu
- All interactive elements reachable by Tab
- Burger closes on outside click and Escape

### 13.4 Focus Management
When the about modal opens, focus moves into it. When it closes, focus returns to the trigger button. Mobile sheet drag handle is keyboard-accessible.

---

## 15. Phased Build Approach

Large atlases must be built in phases with explicit commits. This is mandatory — do not attempt to write the entire file in one pass, and do not chain phases without stopping for confirmation.

### The Full Phase Plan

---

**Phase 1A — Copy**
`cp civilitas/index.html atlasname/index.html`
Open the file. Verify it renders identically to civilitas. Commit.

**Phase 1B — Metadata**
Update `<title>`, `<meta name="description">`, all Open Graph tags, Twitter tags, JSON-LD structured data, canonical URL, and favicon emoji. Do not touch anything else. Commit.

**Phase 1C — Logo & Modal**
Update the header logo text (`CIVILITAS` → new name, subtitle). Rewrite the about modal content for the new atlas. Commit.

**Phase 1D — Domain Language**
Find and replace all domain-specific strings throughout the file:
- `CIVS` → `ITEMS`
- `civClick` → `itemClick`
- `navigateToCiv` → `navigateToItem`
- `"Civilization Arc"` → `"[Subject] Arc"`
- `"Concept Threads"` → `"[Domain] Chains"` (or equivalent)
- `"Heritage"` → `"[Domain equivalent]"`
- `"civilizations active"` → `"[items] known"` (or equivalent)
- Timeline `<span class="tl-lbl">` labels updated to match the new timeline range
- All ARIA labels and map `aria-label` descriptions
- Thread panel title
- Count display suffix
**Do not touch Herstory. Do not touch any colour values.** Commit.

**Phase 1E — Map Adaptation (if non-geographic only)**
If the atlas uses a non-geographic coordinate space (e.g. sky atlas): replace `renderWorldMap()` with the new background renderer, and replace `itemPt()` with the new coordinate projection. Remove D3/TopoJSON `<script>` tags if not needed. Leave every other line of CSS, HTML, and JS exactly as copied from civilitas. Commit.
*(Skip this phase entirely if using the standard world map.)*

**Phase 1F — Clear Data Arrays**
Set all data arrays to empty stubs:
```javascript
const LENSES=[];
const ERAS=[];
const ITEMS=[];
const TRANSMISSIONS=[];
const HERITAGE_REGIONS={};
const WOMEN={};
```
Open the file. Verify it loads, shows the welcome state in the drawer, and has no console errors. Commit.

*After Phase 1F: the shell is complete. The file is pixel-identical to civilitas in colour, layout, and behaviour. Only text and domain language differ. This is the mandatory starting point for all data phases.*

---

**Phase 2A — Data Batch 1 (items 1–25)**
Write 25 fully populated items. Every item must have every lens field written — no stubs, no placeholders. Commit.

**Phase 2B — Data Batch 2 (items 26–50)**
25 more fully populated items. Commit.

**Phase 2C — Data Batch 3 (items 51–75)**
25 more fully populated items. Commit.

**Phase 2D — Data Batch 4 (items 76–100+)**
Remaining items to reach the 100+ minimum. Commit.

---

**Phase 3 — Constants & Chain Data**
Write `LENSES` (sorted alphabetically by `lbl`), `ERAS`, `FP_LABELS`, `FP_KEYS`, `TRANSMISSIONS` (~15–25 chains), `HERITAGE_REGIONS` (or domain equivalent), `WOMEN` (Herstory data — mandatory). Commit.

---

**Phase 4A — Engine: Map, Timeline, Projection**
*(This phase is usually already complete from civilitas — only needed if Phase 1E introduced a new projection.)*
Wire up `renderDensityBar()`, `setYear()`, timeline slider events, era labels, `active()` function, `renderMap()` markers, zoom/pan. Commit.

**Phase 4B — Engine: Drawer & Lenses**
Wire up `renderDrawer()`, lens dropdown `renderLensDD()` / `toggleLens()`, fingerprint chart `renderFingerprint()`, span bar, connections list, welcome state. Commit.

**Phase 4C — Engine: Utilities & Boot**
URL encode/decode, `shareState()`, `toggleTheme()`, `toggleBurger()`, `showAbout()` / `closeAbout()`, keyboard listeners, outside-click handlers, `init()`, `DOMContentLoaded` / `window.load` boot. Commit.

---

**Phase 5 — All Five Modes**
Threads/chains panel + animated SVG arrows, compare dual-drawer, what-if removal + broken path rendering, heritage/address region picker, Herstory toggle + drawer. Commit.

---

**Phase 6 — Polish & QA**
Run the full verification checklist (Section 18). Fix any issues found. Final commit.

---

### Phase Confirmation Protocol

**Stop after every phase and sub-phase. Wait for explicit confirmation before beginning the next.** Do not chain phases. After each commit, state:
1. What was built in this phase
2. What file was output
3. What the next phase will do
4. Whether confirmation is required before proceeding

### The Most Common Phase 1 Error

The most common mistake is **changing colour values during Phase 1**. This happens when an agent decides the new atlas "needs" a different colour palette and introduces new CSS variable values instead of copying them from civilitas. This is always wrong. If the file looks any different from civilitas in colour — even slightly bluer, greener, or cooler — Phase 1 has failed and must be redone before proceeding.

---

## 16. Herstory — Mandatory Across All Atlases

**Herstory is a permanent, non-negotiable feature of every Pangea atlas. It is never renamed, recoloured, or omitted.**

### What Herstory is

Herstory is a toggleable overlay mode that highlights the contributions of women across every subject domain covered by an atlas. When active, items with associated women figures show a distinct pink/magenta marker (`#c060a0`) on the map. The drawer shows those women's names, roles, dates, and descriptions instead of the standard lens content.

This is not a "women in science" feature specific to Cosmos, nor a "female rulers" feature specific to Civilitas. It is a universal commitment across the entire Pangea Project: every domain of human knowledge has women whose contributions are overlooked, erased, or underattributed. Herstory makes them visible.

### What never changes across atlases

- **The name** — always `Herstory`. Not "Discoverers", not "Trailblazers", not "Women in [Field]". Always `Herstory`.
- **The burger menu item** — always `♀ Herstory` with a badge showing `ON` when active
- **The marker colour** — always `#c060a0` (pink/magenta)
- **The body class** — always `body.herstory` toggled by `toggleHerstory()`
- **The badge ID** — always `id="herstory-badge"`
- **The menu item ID** — always `id="menu-herstory"`
- **The `WOMEN` object** — always `const WOMEN = { item_id: [ {...}, {...} ] }`

### The WOMEN object structure

```javascript
const WOMEN = {
  'item_id': [
    {
      nm:   'Full Name',
      role: 'Her role or title',
      yr:   1905,           // year of key contribution
      desc: 'Two to three sentences describing her specific contribution. Accurate, substantive — her actual work and why it mattered, not just that she did it as a woman.'
    }
  ],
  // ...
};
```

### Domain framing per atlas

The framing of *who* Herstory covers adapts to the domain — but the feature itself does not:

| Atlas | Herstory covers |
|---|---|
| Civilitas | Women who shaped each civilisation — rulers, scholars, revolutionaries |
| Bellum | Women strategists, resistance fighters, military leaders, logisticians |
| Numen | Female religious leaders, mystics, theologians, founders of orders |
| Pecunia | Women economists, bankers, traders, currency innovators |
| Flora | Women botanists, agricultural scientists, seed savers, herbalists |
| Lex | Female jurists, legislators, human rights advocates, legal scholars |
| Cosmos | Women astronomers and physicists — Leavitt, Payne-Gaposchkin, Rubin, Bell Burnell, and others |

### Content quality for WOMEN entries

- Every entry must be **factually accurate** — real person, real contribution, real dates
- **No tokenism** — credit the work itself, not just the gender of the person who did it
- **No atlas ships with an empty or sparse `WOMEN` object** — this is as mandatory as the item data itself

---

## 17. Naming Conventions Per Atlas

Domain-specific terms must be renamed throughout the code and UI. **Herstory is the sole exception — it is never renamed.**

| Component | Civilitas | Adapt to domain |
|---|---|---|
| Items array | `CIVS` | `ITEMS` (always use ITEMS) |
| Item click handler | `civClick()` | `itemClick()` |
| Navigate to item | `navigateToCiv()` | `navigateToItem()` |
| Arc label | "Civilization Arc" | "[Subject] Arc" |
| Threads mode label | "Concept Threads" | "[Domain] Chains/Threads/Routes" |
| Heritage mode label | "Heritage" | "[Domain equivalent]" |
| Count label | "civilizations active" | "[items] known / active / in view" |
| Map aria-label | "World map with civilization markers" | "[appropriate description]" |
| **Herstory toggle** | **`♀ Herstory`** | **Never renamed — always `♀ Herstory`** |

**Never** leave civilitas-specific text (e.g. "civilizations", "Civilization Arc") in a different atlas. But always keep "Herstory" as "Herstory".

---

## 18. File Verification Checklist

Before considering any phase or the full atlas complete, verify:

- [ ] Item count matches the number stated in `<meta name="description">`
- [ ] Item count is ≥ 100
- [ ] Every item has all lens IDs present in `d{}` (no missing keys)
- [ ] Every `d` value is a non-empty string of 2–4 sentences
- [ ] LENSES array is sorted alphabetically by `lbl`
- [ ] All apostrophes in data strings are escaped with `\'`
- [ ] All item IDs in `conns[]` and `TRANSMISSIONS` resolve to real item IDs
- [ ] All FP keys in items match `FP_KEYS`
- [ ] Dark theme contrast passes WCAG AA for all text pairs
- [ ] Light theme contrast passes WCAG AA for all text pairs
- [ ] The atlas opens correctly by double-clicking the HTML file locally
- [ ] The atlas opens correctly when the map CDN is unavailable (fallback renders)
- [ ] All 5 modes are implemented and functional
- [ ] Herstory is implemented with a populated `WOMEN` object (no atlas ships with empty Herstory)
- [ ] Herstory marker colour is `#c060a0` — not recoloured
- [ ] Herstory burger item is labelled `♀ Herstory` — not renamed
- [ ] Mobile portrait layout works (bottom sheet behaviour)
- [ ] URL state encodes and decodes correctly
- [ ] Share link copies correctly (no exception in sandboxed iframe)
- [ ] No civilitas-specific terminology remains in UI strings (except Herstory, which is kept)
- [ ] Colour scheme matches civilitas exactly — no per-atlas accent colour changes
- [ ] About modal content is correct for this atlas
- [ ] The back link points to `../index.html`

---

## 19. Atlas Specifications Reference

| Atlas | Subject | Items | Lenses | Map type |
|---|---|---|---|---|
| civilitas | Human civilisations | 100 | 30 | World map |
| bellum | Wars & conflicts | 100+ | 20 | World map |
| numen | Religion & belief | 100+ | 20 | World map |
| pecunia | Money & economics | 100+ | 20 | World map |
| flora | Plants & agriculture | 100+ | 20 | World map |
| lex | Law & justice | 100+ | 20 | World map |
| cosmos | The universe | 105 | 20 | Sky atlas |

All future atlases: minimum 100 items, minimum 20 lenses.

---

## 20. The Golden Rules

1. **Copy civilitas first.** Every new atlas starts as `cp civilitas/index.html atlasname/index.html`. Never build from scratch.
2. **Civilitas is always right.** When in doubt about any pattern, check civilitas. Copy its approach, then adapt only what must differ.
3. **One file.** Everything goes in `atlasname/index.html`.
4. **100 items minimum.** No exceptions.
5. **Full lens data for every item.** No stubs, no "TODO", no empty strings.
6. **Alphabetical lenses.** Always verify sort order.
7. **Use the civilitas world map.** Identical projection, identical CDN sources, identical layer structure — unless the atlas is explicitly non-geographic.
8. **Never change the colour scheme.** The amber/gold palette is fixed across every atlas. It is the Pangea Project's visual identity. Do not introduce per-atlas accent colours.
9. **Never rename or alter Herstory.** It is called Herstory in every atlas. The marker is `#c060a0` in every atlas. Every atlas has a populated `WOMEN` object. No exceptions.
10. **WCAG AA minimum.** Check contrast in both themes.
11. **Phase confirmation.** Stop after every phase. Wait for explicit go.
12. **Verify the meta description count.** It must match the actual ITEMS array length.
