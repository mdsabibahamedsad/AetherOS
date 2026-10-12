# AETHEROS_HYPOTHESIS_ENGINE — Generation to Validation

## Generation (13 strategies)

EXPLANATORY, MECHANISTIC, CAUSAL, ALTERNATIVE, CONTRARIAN,
BOUNDARY_CONDITION, ANALOGICAL, CROSS_DOMAIN, FIRST_PRINCIPLES,
DATA_DRIVEN, SIMULATION_DERIVED, LITERATURE_DERIVED, ANOMALY_DRIVEN.
Templates force explicit mechanism + predictions + variables. Analogy
and simulation outputs are labeled in the statement text itself.

## Diversity & exploration

`HypothesisDiversifier` groups families by independent variable and
measures strategy coverage (warns < 0.3). `ExplorationController`
pushes contrarian/cross-domain/first-principles modes when missing and
prioritizes high-information uncertain hypotheses over the most
likely one.

## Novelty (corpus-relative, never absolute)

Jaccard similarity over stemmed token sets against a *provided*
corpus → NOVEL / POTENTIALLY_NOVEL / KNOWN_VARIANT / KNOWN /
DUPLICATE / UNCERTAIN. Empty corpus → UNCERTAIN (never "novel by
default"). NOVEL renders as "No matching prior work was found in the
searched corpus." — never "new scientific discovery".

## Critique, falsification, causal discipline

Structured `HypothesisReview` (arguments, confounders, alternatives,
kill-test, reproducibility/safety concerns). `FalsificationEngine`
emits weaken/falsify/support/inconclusive criteria per hypothesis and
judges outcomes into PROPOSED/SUPPORTED/WEAKENED/FALSIFIED/
INCONCLUSIVE. Causal claims require intervention evidence —
observation-only evidence can raise confidence but never VALIDATE
(a test pins this: status stays HYPOTHESIS-equivalent).
