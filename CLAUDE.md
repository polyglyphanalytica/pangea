# Pangea Atlas Project Rules

## Gold Standard
**civilitas/index.html is the gold standard for EVERYTHING.** All other atlases (bellum, numen, pecunia, flora, lex) must follow civilitas as the reference implementation for:
- Structure and data format
- UX and interactivity
- Content quality and depth
- Lenses and their implementation
- Layout and visual design
- Menu structure and navigation
- All features and functionality

## Atlas Specifications
- **civilitas**: 100 civilizations, 30 lenses — the reference atlas
- **bellum, numen, pecunia, flora, lex**: 50 items each, 20 lenses each (per meta descriptions)

## Content Quality
- Each item must have substantive, historically/thematically accurate content for every lens
- Content should be 2-4 sentences per lens field, written as single-line strings with escaped single quotes
- Follow the exact data structure patterns established in civilitas

## Development
- Always check the meta description tags in each atlas to verify the target item count
- Never assume a lower count is "complete" — verify against the stated targets
