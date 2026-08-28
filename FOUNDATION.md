# Foundation

## What this machine is

AXM Universal Creation is intended to be a persistent, inspectable creation substrate rather than a collection of opaque generators.

Its internal pieces may be modular, deeply connected, and machine-scale. A human does not need to manually read every module before using it. The requirement is that the machine can expose what it is made from when inspected.

## Starting structural layers

### Atom
The smallest reusable creation primitive that is still meaningful to the machine.

### Component
A reusable composition of atoms with a defined role.

### Organ
A reusable functional assembly that performs a bounded creation capability.

### Capability
A callable creation ability made from one or more organs, components, learned systems, or explicit external boundaries.

### Creation
A produced artifact, system, medium, or other result.

These categories are **initial scaffolding, not canon**. The running system may refine its own representation when experience justifies it and the change fits the four roots.

## Capability topology

The system should know more than a flat list of tools. It should be able to represent:

- what capabilities exist;
- what smaller pieces compose them;
- how pieces relate;
- what assumptions and dependencies they require;
- what domains or representations they can translate between;
- what they cannot currently do;
- and the smallest explicit missing capability exposed by real use.

The valuable failure object is not merely:

> output was bad

but, when justified:

> capability X is absent or insufficient; existing machinery covers A and B; missing primitive or relation C is the smallest gap currently preventing the requested creation.

## Reuse before rediscovery

The machine should be able to reuse known capability instead of reconstructing the same route from scratch every time.

A newly solved capability gap should be able to become a reusable part of the continuing machine.

## Transparency boundary

Internal capability must be inspectable.

External capability may be used only when its boundary is explicit. The machine must distinguish at least:

- native inspectable deterministic capability;
- learned internal capability whose current usable state is inspectable;
- external black-box capability;
- human-supplied capability;
- unknown or unresolved capability.

Calling an external model, service, binary, device, or API does not make that external system part of the transparent machine.
