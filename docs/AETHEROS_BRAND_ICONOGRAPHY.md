# AetherOS Brand Iconography Rules

Two libraries exist and both stay (no rewrite this phase): **Codicons**
(`components/ui/codicon.tsx`, chrome/status/dense UI) and **Tabler**
(`lib/icons.ts`, feature/product icons). Rules that bind them:

- One family per surface; never mix both in the same row/control.
- 16px base grid (12/16/20/24/32 steps); 2px optical padding at 16px;
  stroke weight inherits family default — never restyle one icon.
- Corners: rounded joins (match radius Small); optical alignment by eye
  at 16px, not math centering.
- Meaning is fixed per glyph (shield = trust/security, ● = live,
  ✓ = done, ○ = pending, ✕ = failed); ambiguous icons get tooltips +
  accessible labels.
- Status is never color-alone; never emoji as status.
- New product icons must read in the wolf's angular/minimal DNA.
- Follow-up (not this phase): codify one family per directory and codemod
  mixed surfaces; add an icon lint allowlist.
