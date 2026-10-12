# Trust Fabric Threat Model (§110) + Attack Surface (§111)

## Actors

malicious/compromised user, malicious webpage/email/repo/MCP
server/A2A agent/extension, compromised model, prompt injection,
memory poisoning, identity/credential theft, policy/audit tampering,
supply-chain, rogue agent/swarm, physical attacker, network
attacker, insider.

## Representative threats -> mitigations (residuals stated)

- Privilege escalation / confused deputy: caller-identity + capability
  + resource checks at tool boundary; audience-bound tokens.
  Residual: tool bugs outside the boundary.
- Delegation/token laundering, replay, amplification: subset rule,
  depth caps, nonce/expiry/audience/max-use, privilege-graph
  analysis. Residual: stolen keys within TTL (short TTLs mitigate).
- Identity spoofing / A2A impersonation: Ed25519 identities,
  explicit delegation required, no inheritance. Residual: CA-less
  self-issued identities need out-of-band trust bootstrap.
- Policy bypass/downgrade: versioned+hashed policies, DENY-wins
  precedence, canary + regression gates. Residual: admin-key
  compromise (out of scope: HSM).
- Audit tampering: hash chaining + signed checkpoints detect
  modification; deletion by storage admin detectable only via
  external checkpoints (stated limit, §52).
- Secret exfiltration: tier separation (USE executes server-side,
  values never disclosed), DLP flows, egress budgets.
- Prompt injection: untrusted-data doctrine; no content path to
  policy/identity/approval stores (tested).
- Memory poisoning: provenance-required writes; external content
  never auto-trusted.
- Swarm collusion / A2A compromise: per-member authority, no
  headcount amplification, remote default-deny.
- SSRF/rebinding/redirect: literal-IP, private-range, metadata,
  hex/decimal-trick rejection + redirect-chain validation.
- Robot safety bypass: independent veto layer + e-stop + M50 global
  stop; kill latency measured.
- Kill-switch bypass: kills live below the model loop (listeners +
  plane scopes); external non-cancellable ops surface
  CANCEL_REQUESTED honestly.

## Attack surface (§111)

MODEL, AGENT, TOOL, MCP, A2A, BROWSER, COMPUTER, FILESYSTEM,
NETWORK, MEMORY, AUTOMATION, EXTENSIONS, SECRETS, ROBOTICS,
PHYSICAL DEVICES, UI, IPC, CLI, API, UPDATE SYSTEM — each mapped to
the enforcing module in ARCHITECTURE.md; gaps tracked in the
migration report.
