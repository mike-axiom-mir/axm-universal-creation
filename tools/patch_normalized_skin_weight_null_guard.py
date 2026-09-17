from pathlib import Path

path = Path('capabilities/platform-hands/shared/asset-hands/rigged-gltf-codec.js')
text = path.read_text()
old = '''        weightNormalizedFieldValid =
          !!weightAccessor &&
          (weightAccessor.normalized == null ||
            typeof weightAccessor.normalized === "boolean"),'''
new = '''        weightNormalizedFieldValid =
          !!weightAccessor &&
          (weightAccessor.normalized === undefined ||
            typeof weightAccessor.normalized === "boolean"),'''
if text.count(old) != 1:
    raise SystemExit('normalized-field guard source drifted; refusing edit')
path.write_text(text.replace(old, new, 1))
