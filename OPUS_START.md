# Tenfold Gen-2 — Opus execution handoff

## Mission
Continue the canonical Tenfold Gen-2 implementation from the actual repository and live GitHub state. Do not search for another handoff. This file is the handoff.

Do not ask the Owner for routine permission between engineering steps. Continue through the safe approved frontier. Stop/escalate only when frozen authority requires an Owner decision, a genuinely unavailable physical/human proof is mandatory, or new evidence demonstrates a constitutional conflict.

## Authority recovery — mandatory before mutation
Recover from current canonical `main`, not chat memory. Read the full recovery order in `AGENTS.md`, including at minimum:

1. `README.md`
2. `docs/00-founding-authority.md`
3. `docs/01-roadmap.md`
4. `docs/07-gen2-evolution-authority.md`
5. `docs/08-gen2-roadmap.md`
6. `docs/09-gen2-review-record.md`
7. `docs/10-chat-workspace-execution.md`
8. `docs/11-generational-evolution-map.md`
9. `docs/12-master-build-horizon.md`
10. `docs/02-assurance-matrix.md`
11. `docs/03-sergeant-donor-map.md`
12. `docs/04-tf00-review-record.md`
13. `docs/05-operating-methods.md`
14. `docs/06-project-method-profiles.md`
15. `PICKUP.md`
16. live GitHub state: current `main`, open PRs, exact candidate heads, review threads, checks and evidence.

Repository law overrides this snapshot if newer.

## Workspace law
Use `D:\THETECHGUY\engineering\tenfold-gen2` as the private construction plane and use the **actual qualified Tenfold Gen-1 runtime** materialised from the canonical Tenfold repository. Do not replace it with an ad-hoc shadow Tenfold, chat-only orchestration, or one-off scripts pretending to be Tenfold. Qualified Gen 1 remains the construction authority until the canonical G2-27 crossover gate.

Canonical project repository: `jaydumisuni/tenfold`.

Before work, verify every checkout/worktree identity and cleanliness. If a required worktree is missing or stale, recreate it deterministically from Git rather than guessing. Do not mutate canonical `main` directly.

## Last-known live anchors — REVERIFY BEFORE ACTING
As recovered immediately before this handoff:

- canonical `main`: `05aa384a34a650e677970904079a985ec8b26d90`;
- PR #36: **OPEN**, `Gen2 G2-01 — exact canonical Gen1 reference v5`;
- PR #36 head: `62496433bb179192b34064f190444acd43ed2c72`;
- PR #36 state in its own description: **FROZEN / PROVING**, not PROVEN;
- Tenfold CI at that head: success;
- `G2-01 exact Gen1 reference proof` workflow at that head: success;
- these green runs do NOT close G2-01 because review findings remain part of the proof surface.

## Current blocking review findings on PR #36
Treat these as real P1 proof-integrity findings until independently shown false or corrected:

1. **Handle PASS bundles in the periodic proof lane.** The proof workflow currently asserts `cold_boot_status == PENDING`; finalisation requires a PASS lifecycle and bound proof artifact, so the periodic/re-proof lane must correctly accept and validate the final PASS state rather than becoming invalid after promotion.

2. **Isolate candidate code from the frozen-reference proof.** The PR-controlled candidate import in the proof lane can execute before the frozen Gen-1 proof and can potentially mutate proof inputs/runtime. Candidate validation must be isolated/trusted appropriately and the frozen reference must be reverified immediately around the authoritative suite so PR-controlled code cannot forge the proof substrate.

Do not dismiss either finding merely because CI is green.

## Immediate execution objective
Finish **G2-01 — Gen-1 Reference and Inheritance Freeze** legitimately.

Use the THETECHGUY cycle:

`Understand -> Build -> Review -> Freeze -> Prove -> Ship`

Expected work pattern:

1. Recover the exact frozen G2-01 obligations and falsification baseline from authority/roadmap.
2. Recover PR #36 completely, including all review threads and current workflows.
3. Use qualified Gen 1 in this workspace to construct the smallest authority-correct repair for the two P1 findings.
4. Review the candidate against TF-00, G2-00, G2-01, Assurance Matrix, Trust/independence requirements and the existing negative fixtures.
5. Freeze only after the implementation is coherent and review findings are addressed rather than papered over.
6. Prove on the exact candidate head. Require all mandatory repository proof, negative fixtures, independent review/Council reconciliation and no disallowed skip or proof-substrate ambiguity.
7. Re-read every current PR review thread after the final candidate is pushed. Resolve/address findings on the actual final head and obtain fresh review where required.
8. Only when repository evidence supports **PROVEN** may G2-01 be promoted/merged.
9. After merge, recover canonical `main` from scratch and continue to the next approved Gen-2.0 milestone according to `docs/08-gen2-roadmap.md`. Do not begin a dependent milestone early. Occupy any independently safe dependency frontier Tenfold proves is available.
10. At every milestone, push only coherent reviewed/frozen milestone output to the canonical repo; keep scratch/construction machinery in the private workspace.

## Continuous execution rule
After a milestone is legitimately proven and shipped, continue automatically to the next approved milestone. Do not stop just to ask whether to continue. Do not jump to G2-30 by hand-scaffolding future milestones. The roadmap is a dependency graph executed by actual Tenfold, not a checklist for speculative file creation.

No Gen2 authority migration or self-construction may be activated before its exact frozen gate. Shadow Gen2 is observation/comparison only until authority migration permits otherwise.

## Completion claims
Never infer completion from successful commands alone. Before claiming any milestone complete, recover and cite:

- exact current `main`;
- exact candidate head/tree;
- current PR/review state;
- mandatory checks and proof artifacts;
- Council/external assurance required by the Matrix;
- negative fixtures/falsification evidence;
- authority ownership and migration state;
- repository-only sufficiency where the milestone requires it.

If evidence conflicts, the stricter unresolved state wins.
