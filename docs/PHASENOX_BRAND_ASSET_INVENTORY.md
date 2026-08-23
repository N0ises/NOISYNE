# PHASENOX Brand Asset Inventory

## Scope and preservation

R8 inventoried the approved source tree at `assets/brand/` before integration:

- Files: 45
- Total bytes: 335,876
- Aggregate source SHA-256:
  `F48D82ECFF7B59ACED5D7F01658DF0390173D143528ACEDA99FCAB09C1177972`

The aggregate is calculated from sorted repository-relative filenames and each
file's SHA-256. R8 does not alter or regenerate these originals. Packaged files
are byte-for-byte copies with source provenance recorded by the branding API.

## Inventory and classification

| Source group | Count | Format and dimensions | Classification and intended use | Runtime package |
| --- | ---: | --- | --- | --- |
| `architecture/Architecture Diagram*.svg` | 2 | SVG, 1600×900 | Duplicate architecture/reference diagrams | Source-only |
| `concepts/Master-logo.svg` | 1 | SVG, 1500×300 | Live/accent lockup concept | Source-only |
| `concepts/phasenox-font-study.svg` | 1 | SVG, 1500×300 | Typography/lockup study | Source-only |
| `concepts/phasenox-eye-study.svg` | 1 | SVG, 1600×900 | Ø/eye construction study | Source-only |
| `concepts/technical-phasenox-logo.svg` | 1 | SVG, 1600×900 | Duplicate technical eye study | Source-only |
| `exports/phasenox-logo-{16,32,64,128,256,512,1024}x*.png` | 7 | PNG, square at named sizes | Production-ready app/window icon set | Packaged |
| `favicon/*.png` | 4 | PNG, 16×16 | Favicon experiments/duplicates | Source-only |
| `favicon/*.svg` | 3 | SVG, declared 256×256; viewBox 1024×1024 | Scalable favicon experiments/duplicates | Source-only |
| `hero/phasenox-hero-banner.svg` | 1 | SVG, 1920×720 | Dark cinematic splash/hero candidate | Packaged |
| `master/phasenox-master.svg` | 1 | SVG, 1500×300 | Primary dark lockup with tagline | Packaged |
| `master/phasenox-master-dark.svg` | 1 | SVG, 1500×300 | Byte-identical named dark lockup duplicate | Source-only |
| `master/phasenox-master-light.svg` | 1 | SVG, 1500×300 | Primary light lockup with tagline | Packaged |
| `master/phasenox-master-live.svg` | 1 | SVG, 1500×300 | Dark live/signal-accent lockup | Source-only |
| `master/phasenox-master-light-live.svg` | 1 | SVG, 1500×300 | Light live/signal-accent lockup | Source-only |
| `master/phasenox-symbol.svg` | 1 | SVG, 1024×1024 | Monochrome Ø/eye app mark | Packaged |
| `master/phasenox-symbol-dark.svg` | 1 | SVG, 1024×1024 | Ø/eye mark with restrained signal accent | Packaged |
| `master/phasenox-wordmark.svg` | 1 | SVG, 1500×260 | Primary dark wordmark | Packaged |
| `master/phasenox-wordmark-dark.svg` | 1 | SVG, 1500×260 | Byte-identical named dark wordmark duplicate | Source-only |
| `master/phasenox-wordmark-light.svg` | 1 | SVG, 1500×260 | Primary light wordmark | Packaged |
| `master/phasenox-wordmark-live.svg` | 1 | SVG, 1500×260 | Dark live/signal-accent wordmark | Source-only |
| `master/phasenox-wordmark-light-live.svg` | 1 | SVG, 1500×260 | Light live/signal-accent wordmark | Source-only |
| `previews/phasenox-hero-banner.png` | 1 | PNG, 1920×720 | Raster hero preview | Source-only |
| `previews/phasenox-master*.png` | 2 | PNG, 1500×300 | Master lockup previews | Source-only |
| `previews/phasenox-social-preview*.png` | 2 | PNG, 1200×630 | Social composition previews | Source-only |
| `social/phasenox-social-preview*.svg` | 2 | SVG, 1200×630 | Social sharing artwork | Source-only |
| Root README, validation, and change manifest | 3 | Markdown | Source provenance and validation evidence | Source-only |
| `guidelines/PHASENOX-Brand-Guidelines.md` | 1 | Markdown | Locked visual usage guidance | Source-only |
| `guidelines/phasenox-design-tokens.json` | 1 | JSON | Design-system reference tokens | Source-only |
| **Total** | **45** |  |  | **14 packaged assets** |

## Packaged runtime boundary

Production consumers use `phasenox.resources.branding`, not repository-root
paths. The Qt-independent API provides canonical display metadata, logical asset
names, package-safe byte access, and temporary/path materialization through
`importlib.resources`. It works from a source checkout and an installed wheel
without depending on the current working directory.

Source artwork remains under `assets/brand/`. Concept studies, design guidance,
previews, social assets, diagrams, duplicate variants, and favicon experiments
are intentionally excluded from wheel and sdist runtime resources.
