# Combined animated game-asset showcase

`game-showcase-verify` is the fail-closed integration gate for a finished game-asset proof. It does not create art or award quality from polygon count. It requires one evidence source to bind all of these layers:

- unchanged canonical identity and a selectable realistic style;
- at least one selected game style and three realized material families;
- a named rig with at least two clips and measured loop seams;
- at least two explicit secondary-motion classes with measured export error;
- both ground-contact and gameplay-socket bones;
- a descending LOD ladder that retains declared identity features;
- fixed-view pixel comparisons for the selected cheaper LOD; and
- digests for both an actual GLB and editable Blender source.

The command writes `showcase-source.json` and `showcase-receipt.json` into a new directory and refuses to overwrite an existing path:

```sh
axm-assets game-showcase-verify measured-showcase.json checked-showcase
```

A structurally valid source can return `HOLD` when any measured gate fails. Malformed or incomplete evidence is rejected. The receipt preserves the exact validated source and its canonical digest.

## Parcel Imp proof

`tools/blender/game_showcase_parcel_imp.py` builds one original salvage courier bot rather than another isolated mechanism swatch. It has a mischievous screen face, one oversized armored wheel, crooked caster, parcel catapult, navigator duck, spring alarm, endless receipt and swinging excuse satchel.

The proof exports LOD0 and LOD1 GLBs with the same 16-bone rig and three named actions: `Idle_Parcel_Panic`, `Delivery_Dash`, and `Package_Launch`. The spring, antenna, receipt chain and satchel use the repository's deterministic secondary-motion solver. Worn yellow painted metal, patched fabric and rubber are realized from repository material bundles; the realistic finish remains independently selectable.

The priority-10 repair adds functional motion without replacing those authored
layers: dash root travel now drives radius-correct wheel and caster rotation,
and the parcel follows a constant-gravity release/apex/impact track between
explicit endpoints. Fresh-import comparisons bind those tracks to the GLBs.
The calculated wheel residual is an authored distance/rotation consistency
check, not terrain-contact physics.

Fresh Blender 4.3 imports measure animation tracks, loop closure, ground contacts, sockets, triangle counts and two transparent fixed-view LOD comparisons. Representative stills support only static visual review. Continuous target-engine playback, collision behavior and frame-time performance remain explicitly unproven.
