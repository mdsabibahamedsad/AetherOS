# AETHEROS_SCIENTIFIC_SAFETY — Safety Policy + Threat Model (§238)

## Classification

COMPUTATIONAL (sandboxed code/data/stats/benchmarks) → LOW_RISK →
REVIEW_REQUIRED (physical lab, controlled automation, external) →
HIGH_RISK → PROHIBITED (bio/chem/cyber-offensive patterns in protocol
or domain). Physical lab additionally requires validated protocol,
authorization, bounds, operator/device identity, audit, e-stop.

## Threat model (§238)

| Threat | Mitigation | Residual |
|---|---|---|
| Scientific hallucination | Status labels, gate, numeric verification | Reviewer complacency — human gates kept |
| Fake evidence/citations | No resolver invents sources; verification fails closed | External resolver quality (when wired) |
| Citation injection | Sources are DATA; quarantine on injection patterns | Paraphrased injections — review |
| Dataset poisoning | Hash pinning, lineage, leakage checks | Sophisticated poisoning — red-team |
| Model poisoning | Version pinning, provenance | Upstream compromise — attestations |
| Experiment/result manipulation | Manifests, fingerprints, immutable raws | Admin tampering — audit log |
| Artifact tampering | Hash verification before reuse | Same as above |
| Remote agent compromise | Trust/provenance/verification required | Colluding agents — independence analysis |
| Prompt injection | Doc scanning, DATA-not-AUTHORITY | See residual above |
| Data exfiltration | Secret scanning, confidentiality modes | Filesystem-read residual (documented) |
| Unsafe physical execution | LAB_UNAVAILABLE default; approval gates | Misconfigured connector — bounds enforced |
| Autonomous runaway | Budgets, stop conditions, STOP ALL SCIENCE | — |

## Confidentiality modes

PUBLIC / PRIVATE / CONFIDENTIAL / AIR_GAPPED / LOCAL_ONLY /
TEMPORARY. Default LOCAL_ONLY: landscape builder has no network
search unless explicitly injected (`network_status` reports
UNAVAILABLE otherwise).
