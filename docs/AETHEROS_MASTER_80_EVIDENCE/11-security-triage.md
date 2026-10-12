# §42 triage — actual scanner output, classified (2026-09-15, no redesign, no suppression)

## Secrets scanner (`check-secrets.mjs`, exit 1)

| Finding | Location | Verdict | Rationale |
|---|---|---|---|
| `api_key: 'sk-secret'` | `src/store/onboarding.test.ts:357,365,374` | TEST_FIXTURE | synthetic value asserting local-endpoint key storage; `example.com` URL; never a real credential |
| `auth' : 'apikey'` (type union `'apikey' \| 'oauth'`) | `src/store/onboarding.ts:24,379,381` | FALSE_POSITIVE | string-literal enum member, not a credential |
| `token: 't'` | `src/store/updates.test.ts:105` | TEST_FIXTURE | single-char stub in update-state test |

No live credential leak observed. Owner: desktop maintainer. Action: none required for
build integrity; scanner stays ungated (informational) until allowlisting lands.

## Dependencies (`audit-dependencies.mjs`, exit 2 — 32 vulns: 21 high, 1 critical; 49 outdated)

| Class | Members | Verdict |
|---|---|---|
| Build-only (never shipped) | app-builder-lib, dmg-builder, builder-util, builder-util-runtime, electron-builder-squirrel-windows, electron-publish, concurrently, vitest, @vitest/mocker, vite, esbuild, mermaid, postcss, baseline-browser-mapping, browserslist, @babel/core | KNOWN_ACCEPTED_RISK (build-time; fix via routine dep updates, NOT a release gate) |
| Transitive via toolchain | brace-expansion, tar (critical), shell-quote, form-data, js-yaml, nanoid, colord, joi, baseline-browser-mapping | KNOWN_ACCEPTED_RISK (transitive; track upstream fixes) |
| Runtime-reaching, review owned by desktop maintainer | axios, undici, dompurify, react-router, react-router-dom, nanoid, electron (high), electron-builder (high), @xmldom/xmldom | ACTION_REQUIRED (triage+scheduling, not a Master-80 gate; do NOT inflate into a production blocker here) |

`security:audit` score 50/100 (12/24) recorded as INFORMATIONAL. Live runtime security
remains VM-gated (W79-035). Remediation is routine maintenance, explicitly out of Master-80 scope.
