#!/usr/bin/env python3
"""
Pangea Build System
===================
Assembles atlas HTML files from the shared engine (civilitas) + per-atlas data.

Usage:
  python3 build.py ATLAS_NAME          Build one atlas
  python3 build.py --all               Build all atlases that have data.js
  python3 build.py --verify ATLAS_NAME Build and validate

The per-atlas data file is: ATLAS_NAME/data.js
The engine source is: civilitas/index.html (always the reference)
The output is: ATLAS_NAME/index.html
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def load_atlas_config(atlas):
    """Load the atlas data.js file and extract config + data sections."""
    data_path = Path(f"{atlas}/data.js")
    if not data_path.exists():
        return None
    return data_path.read_text(encoding="utf-8")


def build_atlas(atlas, engine_html=None):
    """Build atlas/index.html from engine + atlas/data.js."""
    if engine_html is None:
        engine_path = Path("civilitas/index.html")
        if not engine_path.exists():
            print(f"ERROR: civilitas/index.html not found (engine source)")
            return False
        engine_html = engine_path.read_text(encoding="utf-8")

    data_js = load_atlas_config(atlas)
    if data_js is None:
        print(f"SKIP: {atlas}/data.js not found")
        return False

    # Parse the config block from data.js
    # Format: const ATLAS_CONFIG = { key: 'value', ... };
    config = {}
    config_m = re.search(r'const ATLAS_CONFIG\s*=\s*\{([\s\S]*?)\};', data_js)
    if config_m:
        for kv in re.finditer(r"(\w+)\s*:\s*'((?:[^'\\]|\\.)*)'", config_m.group(1)):
            config[kv.group(1)] = kv.group(2)
        # Also parse non-string values
        for kv in re.finditer(r"(\w+)\s*:\s*(-?\d+)", config_m.group(1)):
            config[kv.group(1)] = int(kv.group(2))

    if not config.get('name'):
        print(f"ERROR: {atlas}/data.js missing ATLAS_CONFIG with 'name'")
        return False

    html = engine_html

    # ── Replace metadata ──
    name = config['name']
    subtitle = config.get('subtitle', f'The {name} Atlas')
    name_upper = name.upper()
    year_min = config.get('year_min', -8000)
    year_max = config.get('year_max', 2024)
    icon = config.get('icon', '🌍')

    # Title
    html = re.sub(r'<title>[^<]+</title>',
                  f'<title>{name} — {subtitle} | {{items}} Items</title>', html, count=1)

    # Meta description — extract from data.js
    meta_desc = config.get('meta_description', f'Explore 100 items across history in {name}.')
    html = re.sub(r'(<meta name="description"[^>]*content=")[^"]*(")',
                  rf'\g<1>{meta_desc}\2', html, count=1)

    # Keywords
    meta_kw = config.get('meta_keywords', name.lower())
    html = re.sub(r'(<meta name="keywords"[^>]*content=")[^"]*(")',
                  rf'\g<1>{meta_kw}\2', html, count=1)

    # Canonical URL
    html = re.sub(r'(<link rel="canonical" href=")[^"]*(")',
                  rf'\1https://polyglyphanalytica.github.io/pangea/{atlas}/\2', html, count=1)

    # OG tags
    html = re.sub(r'(og:url"[^>]*content=")[^"]*(")',
                  rf'\1https://polyglyphanalytica.github.io/pangea/{atlas}/\2', html, count=1)
    html = re.sub(r'(og:title"[^>]*content=")[^"]*(")',
                  rf'\g<1>{name} — {subtitle}\2', html, count=1)
    og_desc = config.get('og_description', meta_desc)
    html = re.sub(r'(og:description"[^>]*content=")[^"]*(")',
                  rf'\g<1>{og_desc}\2', html, count=1)
    html = re.sub(r'(og:image"[^>]*content=")[^"]*(")',
                  rf'\1https://polyglyphanalytica.github.io/pangea/{atlas}/og-image.png\2', html, count=1)
    html = re.sub(r'(og:site_name"[^>]*content=")[^"]*(")',
                  rf'\g<1>{name}\2', html, count=1)

    # Twitter tags
    html = re.sub(r'(twitter:title"[^>]*content=")[^"]*(")',
                  rf'\g<1>{name} — {subtitle}\2', html, count=1)
    html = re.sub(r'(twitter:description"[^>]*content=")[^"]*(")',
                  rf'\g<1>{og_desc}\2', html, count=1)
    html = re.sub(r'(twitter:image"[^>]*content=")[^"]*(")',
                  rf'\1https://polyglyphanalytica.github.io/pangea/{atlas}/og-image.png\2', html, count=1)

    # JSON-LD
    html = re.sub(r'("name":\s*")[^"]*— The Human Atlas(")',
                  rf'\g<1>{name} — {subtitle}\2', html, count=1)
    json_ld_desc = config.get('jsonld_description', meta_desc)
    html = re.sub(r'("description":\s*"An interactive)[^"]*(")',
                  rf'\g<1>{json_ld_desc}\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'("url":\s*")[^"]*civilitas[^"]*(")',
                  rf'\1https://polyglyphanalytica.github.io/pangea/{atlas}/\2', html, count=1)

    # Favicon
    html = re.sub(r"(<text y='.9em' font-size='90'>)[^<]+(</text>)",
                  rf'\g<1>{icon}\2', html, count=1)

    # ── Replace UI strings ──
    # Logo
    html = re.sub(r'(<span class="logo-t">)[^<]+(</span>)',
                  rf'\g<1>{name_upper}\2', html, count=1)
    html = re.sub(r'(<span class="logo-s">)[^<]+(</span>)',
                  rf'\g<1>{subtitle}\2', html, count=1)

    # Skip link
    skip_label = config.get('skip_label', f'Skip to {name.lower()} panel')
    html = re.sub(r'(class="skip-link"[^>]*>)[^<]+(</button>)',
                  rf'\g<1>{skip_label}\2', html, count=1)

    # Map aria
    map_aria = config.get('map_aria', f'World map with {name.lower()} markers')
    html = re.sub(r'(id="wsvg"[^>]*aria-label=")[^"]+(")',
                  rf'\g<1>{map_aria}\2', html, count=1)

    # Map hint
    hint = config.get('hint_text', 'TAP AN ITEM  ·  PINCH TO ZOOM  ·  DRAG TO PAN')
    html = re.sub(r'(id="map-hint-text">)[^<]+(</span>)',
                  rf'\g<1>{hint}\2', html, count=1)

    # Density bar aria
    html = re.sub(r'(id="density-bar"[^>]*aria-label=")[^"]+(")',
                  rf'\1{name} density over time\2', html, count=1)

    # Info panel aria
    info_aria = config.get('info_aria', f'{name} details')
    html = re.sub(r'(info-panel"[^>]*aria-label=")[^"]+(")',
                  rf'\g<1>{info_aria}\2', html, count=1)

    # Thread panel
    thread_label = config.get('thread_label', 'Concept Threads')
    html = re.sub(r'(thread-panel"[^>]*aria-label=")[^"]+(")',
                  rf'\g<1>{thread_label}\2', html, count=1)
    html = re.sub(r'(id="thread-panel-title">)[^<]+(</span>)',
                  rf'\g<1>{thread_label}\2', html, count=1)

    # Burger menu labels
    html = re.sub(r'(id="btn-threads"[^>]*>\s*<span>[^<]*</span><span>)[^<]+(</span>)',
                  rf'\g<1>{thread_label}\2', html, count=1)
    heritage_label = config.get('heritage_label', 'Heritage')
    html = re.sub(r'(id="btn-heritage"[^>]*>\s*<span>[^<]*</span><span>)[^<]+(</span>)',
                  rf'\g<1>{heritage_label}\2', html, count=1)

    # Cluster picker
    cluster_label = config.get('cluster_label', f'Select {name.lower()} item')
    html = re.sub(r'(id="cluster-picker"[^>]*aria-label=")[^"]+(")',
                  rf'\g<1>{cluster_label}\2', html, count=1)
    html = re.sub(r'(id="cluster-picker-hdr">\s*<span>)[^<]+(</span>)',
                  rf'\g<1>{cluster_label}\2', html, count=1)

    # Count label
    count_label = config.get('count_label', 'items active')
    html = re.sub(r'(id="cnt-n">[^<]*</span>\s*)\S[^<]*(</div>)',
                  rf'\g<1>{count_label}\2', html, count=1)

    # Share title
    html = re.sub(r"(const shareTitle=')[^']+(')",
                  rf"\g<1>{name} — {subtitle}\2", html, count=1)

    # Arc label in drawer
    arc_label = config.get('arc_label', f'{name} Arc')
    html = re.sub(r"(return'|return ')Civilization Arc(')",
                  rf"\g<1>{arc_label}\2", html, count=1)
    # Also in the lens row
    html = html.replace('Civilization Arc', arc_label)

    # About modal
    html = re.sub(r'(aria-label="About )[^"]+(")', rf'\g<1>{name}\2', html, count=1)
    html = re.sub(
        r"(font-family:'Cinzel Decorative'[^>]*>)CIVILITAS(</div>)",
        rf'\g<1>{name_upper}\2', html, count=1
    )
    html = re.sub(
        r"(font-family:'Cinzel'[^;]*letter-spacing[^>]*>)The Human Atlas(</div>)",
        rf'\g<1>{subtitle}\2', html, count=1
    )

    # ── Replace data blocks ──
    # Extract data sections from data.js (everything after ATLAS_CONFIG)
    data_sections = data_js[config_m.end():] if config_m else data_js

    # Replace LENSES
    lens_m = re.search(r'const LENSES\s*=\s*\[[\s\S]*?\];', data_sections)
    if lens_m:
        html = re.sub(r'const LENSES\s*=\s*\[[\s\S]*?\];', lens_m.group(0), html, count=1)

    # Replace ERAS
    eras_m = re.search(r'const ERAS\s*=\s*\[[\s\S]*?\];', data_sections)
    if eras_m:
        html = re.sub(r'const ERAS\s*=\s*\[[\s\S]*?\];', eras_m.group(0), html, count=1)

    # Replace ITEMS (use the full block between const ITEMS= and const TRANSMISSIONS=)
    items_m = re.search(r'(const ITEMS\s*=\s*\[[\s\S]*?)(?=const TRANSMISSIONS)', data_sections)
    items_orig = re.search(r'(const ITEMS\s*=\s*\[[\s\S]*?)(?=const TRANSMISSIONS)', html)
    if items_m and items_orig:
        html = html[:items_orig.start()] + items_m.group(0) + html[items_orig.end():]

    # Replace TRANSMISSIONS
    tx_m = re.search(r'const TRANSMISSIONS\s*=\s*\[[\s\S]*?\];', data_sections)
    if tx_m:
        html = re.sub(r'const TRANSMISSIONS\s*=\s*\[[\s\S]*?\];', tx_m.group(0), html, count=1)

    # Replace WOMEN
    women_m = re.search(r'const WOMEN\s*=\s*\{[\s\S]*?\};', data_sections)
    if women_m:
        html = re.sub(r'const WOMEN\s*=\s*\{[\s\S]*?\};', women_m.group(0), html, count=1)

    # Replace FP_LABELS and FP_KEYS
    fp_m = re.search(r"const FP_LABELS\s*=\s*\[[^\]]+\];\s*\nconst FP_KEYS\s*=\s*\[[^\]]+\];", data_sections)
    if fp_m:
        html = re.sub(r"const FP_LABELS\s*=\s*\[[^\]]+\];\s*\nconst FP_KEYS\s*=\s*\[[^\]]+\];",
                      fp_m.group(0), html, count=1)

    # Replace HERITAGE_REGIONS and HERITAGE_REASONS
    hr_m = re.search(r'const HERITAGE_REGIONS\s*=\s*\{[\s\S]*?\};\s*\n+const HERITAGE_REASONS\s*=\s*\{[\s\S]*?\};', data_sections)
    if hr_m:
        html = re.sub(r'const HERITAGE_REGIONS\s*=\s*\{[\s\S]*?\};\s*\n+const HERITAGE_REASONS\s*=\s*\{[\s\S]*?\};',
                      hr_m.group(0), html, count=1)

    # Replace year init and slider functions
    year_init_m = re.search(r'let year\s*=\s*(-?\d+)', data_sections)
    if year_init_m:
        html = re.sub(r'let year\s*=\s*-?\d+', f'let year={year_init_m.group(1)}', html, count=1)

    slider_m = re.search(r'function sliderToYear\(v\)\{[\s\S]*?\}\s*\nfunction yearToSlider\(yr\)\{[\s\S]*?\}', data_sections)
    if slider_m:
        html = re.sub(r'(// .*?slider.*?\n)?function sliderToYear\(v\)\{[\s\S]*?\}\s*\nfunction yearToSlider\(yr\)\{[\s\S]*?\}',
                      slider_m.group(0), html, count=1)

    # Timeline labels
    tl_m = re.search(r'const TL_LABELS\s*=\s*\[([^\]]+)\]', data_sections)
    if tl_m:
        labels = re.findall(r"'([^']+)'", tl_m.group(1))
        tl_html = '\n    '.join(f'<span class="tl-lbl">{l}</span>' for l in labels)
        html = re.sub(
            r'(<div class="tl-lbls">)\s*((?:<span class="tl-lbl">[^<]+</span>\s*)+)',
            rf'\g<1>\n    {tl_html}\n    ',
            html, count=1
        )

    # ── Fix any remaining civilitas references ──
    if atlas != 'civilitas':
        html = html.replace('navigateToCiv', 'navigateToItem')
        html = html.replace('civClick', 'itemClick')
        # Fix share text fallbacks that reference civilitas
        html = re.sub(
            r"Explore \$\{civName\} on Civilitas[^'`]*",
            f"Explore ${{civName}} on {name}",
            html
        )
        html = re.sub(
            r"'Civilitas [^']*'",
            f"'{name} — {subtitle}'",
            html
        )
        # Fix comments referencing civilitas
        html = html.replace('Civilitas share', f'{name} share')
        html = html.replace('and Civilitas', f'and {name}')
        # Civilization Arc → atlas arc label
        html = html.replace('Civilization Arc', arc_label)
        # Generic civilizat* in UI strings (skip data content)
        html = html.replace('civilizations active', count_label)
        html = html.replace('Select civilization', cluster_label)
        html = html.replace('Civilization details', info_aria)
        html = html.replace('Civilization density', f'{name} density')

    # Fix item count in title
    item_count = len(re.findall(r"^\{id:'", html, re.MULTILINE))
    html = html.replace('{items}', str(item_count))

    # Update meta description item count
    html = re.sub(r'(content="Explore )\d+', rf'\g<1>{item_count}', html, count=1)

    # ── Write output ──
    out_path = Path(f"{atlas}/index.html")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"  Built {atlas}/index.html ({len(html):,} chars, {item_count} items)")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        engine = Path("civilitas/index.html").read_text(encoding="utf-8")
        built = 0
        for d in sorted(Path(".").iterdir()):
            if d.is_dir() and (d / "data.js").exists() and d.name != "civilitas":
                if build_atlas(d.name, engine):
                    built += 1
        print(f"\nBuilt {built} atlases.")
    elif sys.argv[1] == "--verify":
        atlas = sys.argv[2] if len(sys.argv) > 2 else None
        if atlas:
            build_atlas(atlas)
            subprocess.run([sys.executable, "pangea_validate.py", atlas, "--force"])
    else:
        build_atlas(sys.argv[1])
