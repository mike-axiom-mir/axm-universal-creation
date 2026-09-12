# Standalone media workbench

Three more donor capabilities are callable through the UC CLI and Python API.
They require Python's standard library only. Each CLI command builds a new local
project through the existing mixed-media writer, with a preview page and
`media.json` describing its files and hashes. Existing projects are refused.

```bash
# Seven painted-metal maps, with a stable seed and adjustable wear.
PYTHONPATH=src python -m axm_uc metal creations/painted-metal --size 128 --seed 7 --wear 0.5 --scratches 24

# All material parameters can be supplied as a JSON PaintedMetalSpec.
PYTHONPATH=src python -m axm_uc metal creations/red-metal --spec examples/media/red-metal.json

# Transparent native bitmap text for interface assets.
PYTHONPATH=src python -m axm_uc bitmap-label creations/core-label --text 'CORE ONLINE' --scale 4

# Bring integer PCM WAV into a predictable stereo delivery format.
PYTHONPATH=src python -m axm_uc normalize-wav input.wav creations/audio --rate 48000 --channels 2
```

## What is available

| Function | Input | Output | Practical boundary |
|---|---|---|---|
| `metal_request` / `metal_fields` | Size, seed, `PaintedMetalSpec` | Base color, roughness, metallic, height, normal, AO, ORM | Authored PBR-style maps, not measured material or verified engine shading. No seamless tiling claim. |
| `label_request` | Text, integer scale, RGB color, padding | RGBA PNG plus glyph report | Uppercase 5×7 font. Unsupported glyphs appear as boxes. No installed font, Pillow, or Unicode shaping dependency. |
| `wav_request` / `normalize_wav` | PCM WAV bytes, rate, channel count | 16-bit PCM WAV and conversion facts | Nearest-sample resampling, not high-quality filtering. Mono averages all input channels; stereo selects the first two or duplicates mono. No MP3/AAC/float-WAV decoder. |

Python imports live in `axm_uc.media_workbench`. `*_request` returns a request
for `UniversalCreationMachine.create`; it does not itself write files.
`metal_fields` returns raw channels and bytes. `normalize_wav` returns WAV bytes
and conversion metadata. These are composable functions, not automatic actions
performed for every creation.

`PaintedMetalSpec` exposes paint/metal RGB, paint/metal roughness, wear, scratches,
grain scale, height grain/broad amplitudes, scratch/pit depths, pit wear strength,
base/roughness grain variation, and normal strength. `--spec` replaces the CLI
wear/scratches settings; unspecified JSON fields use donor defaults. ORM channels
are AO / roughness / metallic. Normal Y follows the donor's image coordinates;
a target engine may require a green-channel flip, which is not applied here.

Current bounded adapters accept metal sizes 16..512, 0..128 scratches, seeds
0..2147483647, labels up to 1024 input characters and 1,048,576 pixels, and WAV
input up to 16 MiB / eight channels / 1,048,576 frames. WAV output is bounded to
1,048,576 frames, one or two channels, 8..96 kHz. These are allocation controls
for these implementations; they are not limits on UC's architecture.

## Sources and checks

`third_party/absorption-v3.json` records pinned donor commits, complete source
hashes, exact extracted definitions, and local destinations. Game Assets and
FrameState Apache-2.0 licenses are already retained under `third_party/`.
Metal field math and bitmap functions are exact source slices with local imports;
native WAV decoding is copied byte for byte. Validation, previews and transactional
writer adapters are UC code. Existing donor modules and previous capabilities
remain in place.

Tests compare seven metal-channel hashes against the original donor at size 32,
seed 7; verify ORM channel packing and a neutral normal field; decode actual PNG
rows to check glyph shape and transparency; exercise signed and unsigned PCM
widths, stereo/mono conversion and exact nearest-sample duplication; reject
invalid/oversized/truncated inputs; and generate all three project types through
the machine, verifying written hashes and no-overwrite behavior.
These checks establish local byte and integration behavior. They do not claim
engine rendering, listening quality, physical material fidelity, or browser QA.
