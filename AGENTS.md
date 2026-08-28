# AXM Universal Creation — Agent Lanes

This repository uses one clean work lane per AI instance.

## Main instance

The main instance works on the authoritative `main` tree and preserves the standalone Universal Creation direction.

## Additional instances

Each additional AI instance gets exactly **one PR lane** for its work.

Logical order:

- main instance → `main`
- next AI instance → PR lane 1
- next AI instance → PR lane 2
- next AI instance → PR lane 3
- continue sequentially

One instance does not scatter its work across multiple PRs, cleanup branches, merge-back branches, or parallel copies of the machine.

An instance stays responsible for its one PR until that work is finished, abandoned, or explicitly handed over.

If several tasks belong to the same instance and active direction, keep them in that instance's existing PR rather than opening another PR.

## Integration

The active machine remains singular. PRs are proposal lanes into that one machine, not alternate machines.

Do not merge a PR unless the user explicitly directs the merge.

After integration, normal build hygiene still applies:

`build -> verify -> remove build debris -> confirm clean -> done`

## GitHub numbering note

GitHub issues and pull requests share one numeric sequence. Therefore the human-facing lane number above is the stable AXM instance lane even when GitHub's displayed PR number is higher because issue numbers already exist.
