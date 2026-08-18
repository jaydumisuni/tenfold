# TF-00 Hostile Review Record

Status: **FINAL HOSTILE PASS — PASS**

Purpose: preserve why TF-00 was considered freeze-ready and which attacks materially changed the founding authority.

## Review posture

The review was explicitly adversarial: attack authority, coupling, derivation, consultant trust, assurance selection, stale state, and amendment paths rather than validating that the design sounded good.

## Material findings and dispositions

### 1. Blueprint -> campaign misinterpretation

Attack: a deterministic Foreman may consistently misparse a blueprint. Determinism prevents drift but does not guarantee correctness.

Disposition: **CLOSED**.

TF-00 now requires independent Campaign Derivation Assurance with requirement coverage, no-invention proof, semantic dependency/coupling review, exact blueprint/compiler/campaign digests, and a sufficiently independent review path. Architectural ambiguity escalates instead of being guessed.

### 2. Missed semantic coupling

Attack: two workers may each remain inside individually valid, non-overlapping write surfaces while still interacting through undeclared shared semantic state such as external APIs, rate limits, shared services, credentials, schemas, or physical resources.

Disposition: **CLOSED**.

TF-00 now requires:

- planned coupling/conflict groups;
- runtime facility-observed touched-state enforcement;
- immediate fencing on observed escape;
- periodic Officer semantic coupling audits;
- independent pre-dispatch Coupling Assurance for Assurance-Matrix-flagged high-risk mutable milestones;
- affirmative evidence of independence; unresolved high-risk coupling serializes;
- exact-generation Coupling Assurance Records invalidated by re-derivation/material binding changes.

### 3. Foreman discretion over external review

Attack: a deterministic Foreman cannot also exercise open-ended judgment about when Sec-Ops/Sergeant/other assurance is required.

Disposition: **CLOSED**.

TF-00 uses an immutable deterministic composable Assurance Matrix. Foreman cannot waive mandatory review. Additional review may be added but required review cannot be removed.

### 4. Consultant poisoning

Attack: a wrong consultant recommendation could become campaign truth through a semi-privileged Council.

Disposition: **CLOSED**.

Consultants return advisory Advice Packets only. Factual claims require evidence validation; hypotheses remain hypotheses; implementation proposals remain bounded by existing authority; blueprint-changing proposals enter the blueprint-amendment path; confidence is not authority.

### 5. Assurance Matrix amendment integrity

Attack: if the Matrix controls mandatory independent review, a weak amendment path could silently narrow review coverage over time.

Disposition: **CLOSED**.

Matrix generations are immutable/versioned/digested. Amendment requires independent policy review, impact analysis, explicit classification of weakened/strengthened assurance, Owner approval for authority-policy change, and publication as a new generation. Active campaigns bind exact generations and cannot silently inherit weaker policy.

### 6. Matrix strengthening during in-flight work

Attack: a stronger Matrix may land while a high-risk milestone is already executing.

Disposition: **COVERED / REQUIRED PROOF CASE**.

Affected milestones enter `ASSURANCE_REBIND_REQUIRED`. No new high-risk mutation may dispatch under insufficient assurance; Freeze/Prove/Ship remain blocked until reconciliation. Already-running bounded work is handled under its exact active authority and its evidence may be retained subject to Council/review.

### 7. Stale Coupling Assurance Record

Attack: campaign re-derivation could leave a previously valid independence record attached to structurally different work.

Disposition: **CLOSED**.

Founding Condition 16 binds Coupling Assurance Records to exact Blueprint generation, Campaign generation, derived campaign digest, and Assurance Matrix generation. Re-derivation/material changes invalidate the record before high-risk parallel mutation may resume.

## Accepted strengths

The hostile review explicitly accepted:

- the model-free Foreman decision;
- Sergeant as donor for hierarchy/training/council discipline;
- Council/rebrief as protection against treating completion as correctness;
- deterministic Assurance Matrix selection;
- consultant advisory-only boundary;
- high-risk `unknown != safe` coupling rule;
- independent implementation paths for derivation/coupling/matrix assurance;
- worker capability minimums;
- prompt-injected content as job material rather than command authority.

## Final result

The final hostile pass reported **PASS**, with one non-blocking refinement: explicitly invalidate Coupling Assurance Records when the campaign is re-derived. That refinement was accepted as Founding Condition 16.

No structural objection remains recorded against TF-00.

## Reopen rule

TF-00 must reopen if implementation or new evidence reveals an actual path that violates a founding invariant.

Ordinary new features, additional adapters, performance improvements, or implementation details belong in TF-01+ and do not reopen TF-00 unless they weaken the founding authority.
