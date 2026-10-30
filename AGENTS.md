# Instructions for all saymer-alt projects

## Mandatory: detailed agent tasks and intent preservation (owner decision, 30.10.2026)

**Before drafting or executing agent assignments, read [AGENT-TASK-CONTRACT.md](AGENT-TASK-CONTRACT.md).** Complex tasks must be described in **full technical detail**: the real user goal, checked source refs/SHA, already completed work, scope/non-goals, protected behavior and data, dependencies, permission/owner-GO boundaries, negative scenarios, verification and a testable Definition of Done. **Never shorten an important assignment just to save tokens or make it easier to paste.** A technically literal result that harms the real user goal is **FAIL** («эффект обезьяньей лапки»). For small obvious fixes, use proportionate detail. This rule extends to every saymer-alt repository, including forks, alongside stricter local safety instructions.


**Proof Before Build (owner decision, 26.10.2026).** Before starting a new feature, major integration, or architectural expansion, follow the [cross-project Proof Before Build policy](PROOF-BEFORE-BUILD.md). Prove a real problem, compare alternatives (including no change, platform-native and waiting for upstream), assess engineering/economic benefit, total maintenance cost, risks, measurable experiment and a STOP criterion. Use a concise existing-Issue note, not a bureaucracy-heavy report. If value is unproven, defer or skip. Small bugfixes/documentation changes require proportionate evidence only. Never waive project safety or permissions.

This policy is intended to be referenced from `AGENTS.md` in individual repositories. Per-repository safety/integration instructions continue to apply.
