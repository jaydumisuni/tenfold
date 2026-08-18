# Tenfold Assurance Matrix

Status: **FOUNDING AUTHORITY / GENERATION 1**

This document defines mandatory external assurance classes for Tenfold campaigns. The Foreman applies this matrix deterministically and cannot waive a required assurance.

Campaigns must bind the exact Matrix generation and digest used for their decisions. Requirements compose: if a milestone matches multiple rows, all applicable mandatory assurances apply.

## Generation 1 rules

| Milestone / authority characteristic | Mandatory assurance |
| --- | --- |
| Ordinary bounded implementation with no other flagged boundary | Tenfold Milestone Council |
| Security, authentication, credential, secret, trust-boundary, permission, or privilege work | Tenfold Council + Sec-Ops |
| Change to Tenfold authority, rank, evidence admission, coupling policy, Assurance Matrix, or founding invariant | Tenfold Council + independent authority review; Owner approval where authority policy changes |
| Prime OS authority boundary, machine capability ownership, boot/update/driver/resource-enforcement integration | Tenfold Council + Prime authority review |
| Ptah Workspace authority/contracts, Node/Provider/Facility semantics, Workspace execution boundary | Tenfold Council + Ptah authority review |
| Cross-repository integration where independent repositories must agree on an interface/state transition | Tenfold Council + independent integration assurance |
| Physical device mutation, firmware/device state transition, or single physical-resource ownership | Tenfold Council + relevant physical/specialist proof authority |
| Destructive or irreversible operation | Tenfold Council + explicit governing authority gate; automatic retry forbidden unless idempotency is proven |
| Public/external release, deployment, publication, or activation of a new authority class | Tenfold Council + release/activation assurance required by the governing project |
| High-risk concurrent mutable work in any flagged category above | Independent pre-dispatch Coupling Assurance in addition to all other applicable assurance |
| Consultant proposes a blueprint/authority change | Advice remains non-authoritative; blueprint/authority amendment path required |

## Deterministic application

The Foreman does not decide whether review "feels necessary."

It evaluates milestone attributes against this matrix and emits the complete required assurance set.

Officers, Council, Owner, or consultants may request **additional** assurance. They may not remove mandatory assurance produced by the matrix.

## High-risk coupling rule

For any Matrix-flagged high-risk mutable milestone:

> **Unknown independence is not safe.**

Before concurrent mutable lanes are dispatched, independent Coupling Assurance must produce an exact-generation Coupling Assurance Record and affirm `parallelism_authorized` for the relevant units.

If independence is unresolved, mutation is serialized or placed under one coupled integration owner.

## Amendment authority

The Assurance Matrix is authority policy, not ordinary configuration.

Changing it requires:

1. proposed old -> new matrix diff;
2. exact old generation/digest;
3. exact proposed new generation/digest;
4. independent policy review through a sufficiently separate path;
5. impact analysis across active and future campaign classes;
6. explicit classification of assurance added, removed, weakened, or strengthened;
7. Owner approval for authority-policy change;
8. publication as a new immutable Matrix generation.

A new generation never silently rewrites an active campaign's binding.

### Weakening

An active campaign remains bound to its existing Matrix generation until an explicitly authorized rebind. A weaker new generation cannot retroactively bypass existing gates.

### Strengthening

When a new generation strengthens assurance requirements, impact analysis identifies affected active milestones.

Affected milestones enter `ASSURANCE_REBIND_REQUIRED` before:

- new high-risk mutation is dispatched under insufficient assurance;
- Freeze;
- Prove;
- Ship.

Already-running bounded work is handled under its exact active execution authority. Its evidence may be retained, but stronger assurance must be reconciled before the milestone advances.

## Amendment independence

The matrix amendment validator/reviewer must not merely execute the same policy implementation that produced the amendment.

Independent review must compare:

- old matrix;
- proposed matrix;
- authority rationale;
- affected milestone classes;
- active campaign impact;
- any formerly mandatory review that would become optional or disappear.

## Founding invariant

No implementation, performance optimisation, consultant recommendation, or Foreman state transition may weaken this matrix by implication.

If runtime behaviour allows a mandatory assurance to be bypassed without a valid new Matrix generation and governing authority, TF-00 has been violated and must reopen.
