# Measurement-result evidence

Universal Creation distinguishes a sourced definition/convention from a result obtained by measurement.

The `axm.measurement-result/v1` contract follows the metrology principle that a measurement result is not just a number: it is a measured quantity value together with relevant information, normally including measurement uncertainty. Terminology is aligned with the JCGM VIM/GUM family and NIST TN 1297 rather than an AXM-specific confidence score.

Reference guidance:

- JCGM VIM measurement result: https://jcgm.bipm.org/vim/en/2.9.html
- JCGM VIM measurement uncertainty: https://jcgm.bipm.org/vim/en/2.26.html
- BIPM JCGM Guides in Metrology: https://www.bipm.org/en/publications/guides
- NIST TN 1297 uncertainty classification: https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-2-classification-components-uncertainty
- NIST TN 1297 uncertainty reporting: https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-7-reporting-uncertainty

## Contract

A record carries:

- a measurand and measured quantity value/unit;
- uncertainty kind: `standard`, `combined_standard`, or `expanded`;
- uncertainty evaluation: `type_a`, `type_b`, `mixed`, or `not_stated`;
- a coverage factor for expanded uncertainty, with optional coverage probability;
- degrees of freedom when known;
- method description, statistic and optional sample count/instrument/procedure;
- explicit scope and conditions;
- published, dataset, or local-record provenance using HTTPS and/or SHA-256;
- optional observation date and bounded notes.

Type A means evaluation by statistical analysis of a series of observations. Type B means evaluation by other information. The labels are not aliases for random and systematic error.

For an expanded uncertainty `U` with reported coverage factor `k`, the math evidence bridge retains a standard-equivalent input uncertainty as `U / k`. This is only a representation change of the supplied uncertainty record; it is not general uncertainty propagation.

## Creation use

`axm.math-create/v1` accepts inline `measurement_overrides` keyed by declared math-family parameters. The measured value is converted through the same dimension registry as other math evidence. Incompatible units fail closed. Numeric overrides, installed known-measure IDs, and measurement-result records cannot compete for the same parameter.

The parameter is marked `selected_by: measurement_result`, its truth becomes `measured`, and the full measurement record travels with the resolved math evidence. Exact mathematical relations derived from measured inputs remain measured.

## Truth boundary

The contract validates evidence shape, units and declared uncertainty semantics. It does not certify an instrument, prove calibration, establish metrological traceability, verify the truth of a supplied source, or propagate arbitrary correlated/nonlinear uncertainties through derived equations. Those require additional evidence and dedicated propagation machinery.
