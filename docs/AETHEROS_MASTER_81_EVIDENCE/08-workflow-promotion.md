# Workflow promotion (§31)

Finding: Master 79.2/80 placed `windows-desktop-certification.yml` under
`aetheros/.github/workflows/` — GitHub Actions only executes the repository root
`.github/workflows/`, so the certification workflow was INERT (could never run).
Live root workflows: desktop-build/nightly/release/security/test + ios-build.

Action: promoted to `.github/workflows/windows-desktop-certification.yml` with
root-relative path fixes (aetheros/ prefix, `node-version-file: aetheros/.nvmrc`,
npm-ci working-directory, evidence paths); nested copy removed (was untracked).
No redundant workflow created (§28): root desktop-release.yml builds+publishes,
this one certifies. PyYAML validation: 7 jobs, DAG
preflight→test→build→{validate,runtime,roundtrip}→evidence. CI execution itself: NOT_RUN.
