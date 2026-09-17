from pathlib import Path

path = Path('capabilities/platform-hands/shared/asset-hands/rigged-gltf-codec.js')
text = path.read_text()

old_decode = '''        else
          v = new DataView(
            parsed.bytes.buffer,
            parsed.bytes.byteOffset + at,
            4,
          ).getFloat32(0, true);
        values.push(v);'''
new_decode = '''        else
          v = new DataView(
            parsed.bytes.buffer,
            parsed.bytes.byteOffset + at,
            4,
          ).getFloat32(0, true);
        if (
          accessor.normalized === true &&
          (accessor.componentType === 5121 || accessor.componentType === 5123)
        )
          v /= accessor.componentType === 5121 ? 255 : 65535;
        values.push(v);'''
if text.count(old_decode) != 1:
    raise SystemExit('exact accessor decode site drifted; refusing edit')
text = text.replace(old_decode, new_decode, 1)

old_weight = '''      if (
        !weightAccessor ||
        weightAccessor.type !== "VEC4" ||
        weightAccessor.componentType !== 5126
      )
        errors.push("WEIGHTS_0 accessor invalid");'''
new_weight = '''      var weightComponent =
          weightAccessor && weightAccessor.componentType,
        weightNormalized =
          weightAccessor && weightAccessor.normalized === true,
        weightNormalizedFieldValid =
          !!weightAccessor &&
          (weightAccessor.normalized == null ||
            typeof weightAccessor.normalized === "boolean"),
        weightFormatValid =
          !!weightAccessor &&
          weightAccessor.type === "VEC4" &&
          weightNormalizedFieldValid &&
          ((weightComponent === 5126 && !weightNormalized) ||
            ([5121, 5123].indexOf(weightComponent) >= 0 &&
              weightNormalized));
      if (!weightFormatValid) errors.push("WEIGHTS_0 accessor invalid");'''
if text.count(old_weight) != 1:
    raise SystemExit('exact WEIGHTS_0 validator drifted; refusing edit')
text = text.replace(old_weight, new_weight, 1)
path.write_text(text)
