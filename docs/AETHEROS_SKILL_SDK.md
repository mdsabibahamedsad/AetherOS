# Skill SDK

A skill is reusable agent behavior: prompts + tools + workflows +
policies + model preferences + memory/research/browser bindings.

Definition (`schemas.py::Skill`): metadata, version, inputs/outputs,
capabilities, dependencies (`{skills: {name: version-range}}`), tools,
policies, tests, provenance.

Dependency resolution (`skills.py::SkillRegistry.resolve`):

```
Skill A → Tool X, Skill B → Tool Y, Model Z
```

- Missing dependencies, incompatible versions (`^`/`>=`), and cycles
  raise typed errors (proven by `test_skill_escalation_and_cycles`).
- `grant_ceiling`: a skill never grants capabilities beyond the
  registering agent — dependencies cannot escalate privilege.
- Version ranges: `^1.2.0`, `>=1.0.0`, exact pins supported.

Example: `aetheros_platform/examples/custom_skill.py` (executed in CI).
Scaffold: `python -m aetheros_platform.cli init skill <name>`.
Python SDK: `Client.register_skill(manifest)` (idempotent on
`name:version`).
