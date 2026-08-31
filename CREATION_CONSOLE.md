# AXM Universal Creation Console

The [AXM Universal Creation Console](https://axm-universal-creation-console.miketobi90.chatgpt.site) is a phone-ready browser surface for making small standalone artifacts without an AI call, account requirement, or cloud runtime dependency.

## What it can emit

| Selection | Standalone output |
| --- | --- |
| Website | Responsive dependency-free HTML |
| Game | Touch-ready offline Canvas arena in HTML |
| Local tool | Device-local notes app using browser storage |
| 3D asset | glTF 2.0 binary GLB command-tower model |
| Media cue | Mono PCM16 WAV signal |

Each build produces real files, an `axm.phone-creation-receipt/v0.1` receipt, and a downloadable ZIP. The browser computes a SHA-256 digest for every emitted body file. The downloaded package works without returning to the console.

## Browser and full-machine boundaries

The console is a deliberately small independent creation runtime. It does not upload the request to the Python machine and it does not require the repository to be running on the phone.

Its receipt therefore states:

- exact browser-emitted bytes were hashed;
- the full Python machine did not execute;
- runtime, visual, and quality behavior was not proven;
- no organ candidate was installed.

For stronger structural validation, use the repository routes. In particular, `procedural-glb-asset` reparses the complete GLB structure after publication, while the console's browser GLB generator is optimized for portable phone-side creation.

## Organ growth remains separate

The console displays the current 415-record organ census and the 412 implementation gaps, but it cannot install an organ. The repository's `creation-organ-growth` route can test one explicitly supplied organ against one missing creation interface in detached and ephemeral spaces. Adoption remains a separate explicit decision.
