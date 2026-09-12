# Universal Creation Asset Composer

From the repository root run `python -m http.server 8000`, then open
`http://localhost:8000/tools/asset-composer/` in your browser.
No npm installation, API key, donor checkout, or network service is required.

24 uploaded PNG originals are bundled, with their original bytes and SHA-256
in `manifest.json`. All are 1536 × 1536 RGB, with **no alpha channel**.
Black backgrounds are preserved. Screen blending can help light effects but
is not a substitute for a true transparency mask. This is a separate pack
from the donor's locked v0.11 ZIP; its archive identity is not reused.

Choose a base and seed; add, reorder, hide, transform, or blend ingredients.
Export PNG or export/import recipe JSON. Browse source sheets below the editor.
Recipes are local until downloaded; reload does not preserve unsaved work.
The default starts with one energy globe. Extra layers are opt-in.
Regular grid windows and non-grid crops are approximate sampling regions,
not clean semantic cutouts. Random compositions are proposals, not guaranteed
finished art. Generated captions in the source artwork do not indicate game state.

The editor adapts `premade-composer.js` and its stylesheet from
mike-axiom-mir/axm-material-surface-fabric at
c5ed5b09be88e13031b89977d392b3088d659e4a, using the already-vendored
composer core. The donor snapshot has no LICENSE file; reuse follows the
user's authorization for their repositories, with no new upstream license claim.
Local changes: independent uploaded pack, gallery, opaque-source labels,
latest-render-wins canvas updates, escaped imported layer names, import
size/layer bounds, reset grid coordinates on atlas change, and no partial PNG
export when assets fail to load. The original donor core remains unchanged.

Validation: all 24 original hashes verified; JavaScript syntax checked;
seeded plans checked against every bundled resource and source dimensions.
Live browser QA was attempted but the supervised preview could not start;
visual quality and download behavior have not been verified in that browser.
