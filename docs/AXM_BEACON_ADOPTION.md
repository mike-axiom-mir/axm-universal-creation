# Universal Creation Organ Beacon

Universal Creation adopts `axm-beacon/0.1` as local collaboration and proposal
transport around the machine. The implementation is adapted from AXM Discovery
Buddy `main@0ef4e93f30e6aeba7ab1bdc524d82bde6460177b`, inspected on 2026-09-09.
Each repository carries its own executable copy; Universal Creation imports no
peer repository at runtime.

## Local commands

```bash
python .axm/beacon/beacon.py publish --base HEAD^ --head HEAD --output-dir /tmp/creation-feed
python .axm/beacon/beacon.py scan --feed-dir tests/fixtures/axm_beacon_reference_index.json
python .axm/beacon/beacon.py fetch --repo owner/repo --capsule-id <sha256>
python .axm/beacon/beacon.py verify .axm/beacon/inbox/<sha256>/capsule.json
```

Publication binds an exact Git range to deterministic capsule and patch
identities. Scanning ranks evidence against creation-domain interests. Fetching
writes only to `.axm/beacon/inbox/<capsule-id>/` and records that nothing was
applied.

## Export boundary

The publisher uses an allowlist for source, tests, capability/organ contracts,
recipes, schemas, bounded request examples, and documentation. Created outputs,
daily snapshots, reference bodies, build output, private/quarantined paths,
environment files, credentials, keys, and local Beacon transport state are
excluded. The allowlist is a transport boundary, not a license decision;
repository provenance and source-identity contracts remain authoritative.

The checked-in fixture preserves the exact Discovery Buddy reference-capsule
summary requested by issue #26. It is deterministic scan input, not copied
runtime code, correctness evidence, or CANON.

## Authority boundary

Beacon is outside Universal Creation's cognition and canonical growth model.
Attention and relevance are triage only. A received proposal cannot update
`main`, `machine.contract.json`, capability state, creation state, snapshots, or
outputs. Adoption requires explicit inspection and the machine's own tests,
four-root fit, source/provenance checks, and human merge authority.
