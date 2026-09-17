"use strict";

const assert = require("assert");
const Rig = require("../rigged-gltf-codec");

function unpack(bytes) {
  bytes = new Uint8Array(bytes);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  assert.strictEqual(view.getUint32(0, true), 0x46546c67);
  assert.strictEqual(view.getUint32(4, true), 2);
  const jsonLength = view.getUint32(12, true);
  const json = JSON.parse(
    new TextDecoder().decode(bytes.subarray(20, 20 + jsonLength)).trim(),
  );
  const binHeader = 20 + jsonLength;
  const binLength = view.getUint32(binHeader, true);
  const binary = bytes.slice(binHeader + 8, binHeader + 8 + binLength);
  return { json, binary };
}

function repack(json, binary) {
  const jsonRaw = new TextEncoder().encode(JSON.stringify(json));
  const jsonLength = Math.ceil(jsonRaw.length / 4) * 4;
  const binLength = Math.ceil(binary.length / 4) * 4;
  const out = new Uint8Array(12 + 8 + jsonLength + 8 + binLength);
  const view = new DataView(out.buffer);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, out.length, true);
  view.setUint32(12, jsonLength, true);
  view.setUint32(16, 0x4e4f534a, true);
  out.fill(32, 20, 20 + jsonLength);
  out.set(jsonRaw, 20);
  const binHeader = 20 + jsonLength;
  view.setUint32(binHeader, binLength, true);
  view.setUint32(binHeader + 4, 0x004e4942, true);
  out.set(binary, binHeader + 8);
  return out;
}

function variant(sourceBytes, componentType, normalized) {
  const parsed = unpack(sourceBytes);
  const json = JSON.parse(JSON.stringify(parsed.json));
  const binary = parsed.binary.slice();
  const primitive = json.meshes[0].primitives[0];
  const accessor = json.accessors[primitive.attributes.WEIGHTS_0];
  const bufferView = json.bufferViews[accessor.bufferView];
  const count = accessor.count;
  const offset = (bufferView.byteOffset || 0) + (accessor.byteOffset || 0);
  const data = new DataView(binary.buffer, binary.byteOffset, binary.byteLength);
  const maximum = componentType === 5121 ? 255 : componentType === 5123 ? 65535 : 1;
  const size = componentType === 5121 ? 1 : componentType === 5123 ? 2 : 4;

  accessor.componentType = componentType;
  if (normalized === undefined) delete accessor.normalized;
  else accessor.normalized = normalized;
  delete bufferView.byteStride;

  for (let vertex = 0; vertex < count; vertex += 1) {
    const row = vertex < Math.floor(count / 2) ? [1, 0, 0, 0] : [0, 1, 0, 0];
    for (let component = 0; component < 4; component += 1) {
      const at = offset + (vertex * 4 + component) * size;
      if (componentType === 5121) data.setUint8(at, row[component] * maximum);
      else if (componentType === 5123)
        data.setUint16(at, row[component] * maximum, true);
      else data.setFloat32(at, row[component], true);
    }
  }
  return repack(json, binary);
}

const packed = Rig.pack(
  Rig.makeClip({ fps: 8, duration: 1, id: "normalized-weight-receiver-fixture" }),
);
const floatControl = variant(packed.bytes, 5126, undefined);
const normalizedU8 = variant(packed.bytes, 5121, true);
const normalizedU16 = variant(packed.bytes, 5123, true);
const controlInspection = Rig.inspect(floatControl);
assert.strictEqual(controlInspection.pass, true, controlInspection.errors.join("; "));

for (const [name, bytes] of [
  ["normalized-u8", normalizedU8],
  ["normalized-u16", normalizedU16],
]) {
  const inspection = Rig.inspect(bytes);
  assert.strictEqual(inspection.pass, true, `${name}: ${inspection.errors.join("; ")}`);
  assert.strictEqual(inspection.weightSumsPass, true);
  assert.strictEqual(inspection.jointIndicesPass, true);
  assert.strictEqual(inspection.deformation.pass, true);
  assert.strictEqual(inspection.deformation.changed, true);
  assert.deepStrictEqual(inspection.deformation.samples, controlInspection.deformation.samples);
}

for (const [name, bytes] of [
  ["u8-without-normalized", variant(packed.bytes, 5121, false)],
  ["u16-without-normalized", variant(packed.bytes, 5123, undefined)],
  ["u16-null-normalized", variant(packed.bytes, 5123, null)],
  ["normalized-float", variant(packed.bytes, 5126, true)],
]) {
  const inspection = Rig.inspect(bytes);
  assert.strictEqual(inspection.pass, false, `${name} unexpectedly passed`);
  assert(
    inspection.errors.includes("WEIGHTS_0 accessor invalid"),
    `${name}: ${inspection.errors.join("; ")}`,
  );
}

console.log("PASS_NORMALIZED_SKIN_WEIGHT_RECEIVER_PARITY");
