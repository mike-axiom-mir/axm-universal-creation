# Size-aware creation templates

List the built-in formats and layouts:

```
PYTHONPATH=src python -m axm_uc formats
```

Create an editable card scaffold through the existing machine template capability:

```
PYTHONPATH=src python -m axm_uc formats --format poker-card --layout collectible-card --title "Relay Engineer" --bleed 3 --safe 3 --path creations/relay-card
PYTHONPATH=src python -m axm_uc formats --format full-hd --layout game-hud --safe 48 --path creations/hud-layout
```

The output includes a local HTML preview, an editable SVG and a JSON manifest.
Named regions (artwork, abilities, stats, minimap, playfield, etc.) can feed later
creation passes without guessing positions. These are layout scaffolds, not
finished art or functional game interfaces. SVG guide rectangles are included and
must be removed before final art export.

Print presets: poker/collectible card 63.5 × 88.9 mm; A4 210 × 297 mm; A5 148 ×
210 mm; A6 105 × 148 mm; US Letter 215.9 × 279.4 mm. Screen canvases: HD, Full HD,
QHD, UHD, portrait HD, 1024 square and 256 icon. Pixel presets are design choices,
not guarantees of device fit or responsive behavior. Layout choices: collectible
card, card back, game HUD, inventory, main menu and poster.

Physical sizes stay in millimetres. DPI only calculates suggested raster export
pixel dimensions, rounded upward; it does not rasterize the SVG. Bleed expands
outside trim; safe inset shrinks inside trim. Both default to zero and must be
chosen for the printer. The example's 3 mm is an explicit example choice, not a
universal printing requirement. No CMYK, PDF/X, duplex registration, imposition,
printer certification or automatic artwork generation is claimed.

Dimensional references checked 2026-09-12:
- https://www.thegamecrafter.com/ (poker size 2.5 × 3.5 inches)
- https://www.neenahpaper.com/ (A-series paper dimensions)

Verification covers dimensions, print/pixel separation, invalid bounds, XML
parsing, escaping and all 72 format/layout combinations within canvas bounds.
