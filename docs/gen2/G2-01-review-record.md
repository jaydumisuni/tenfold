# G2-01 — Gen-1 Reference and Inheritance Freeze — Review / Proof Record

**Status:** FROZEN / PROVING
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01
**Frozen Gen-1 migration reference:** `05aa384a34a650e677970904079a985ec8b26d90`
**Frozen Gen-1 migration tree:** `c7c130b573180e74438d70b6e11c17dd9bade648`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the corrected G2-01 construction
campaign in the private chat workspace after recovering current canonical
`main` from scratch.

The campaign binds:

- blueprint digest `6317043410e6e499a94e37e1ba5f94cb558a11aa65d9c3519b748cd1a941428a`;
- campaign digest `7a45f39517a0625e9beb3f44b20a3ba690e0cb95ad7c33073df38ffe621eeca4`;
- exact canonical reference commit/tree above;
- mandatory assurance `independent_authority_review` + `tenfold_council`.

Independent Gen-1 campaign derivation returned PASS with no findings. The
initial safe frontier contained the reference binding, validator hardening,
divergence hardening and environment hardening lanes; canonical recovery-state
reconciliation remained preparation-safe until reference binding, and final
milestone review remained blocked behind all construction/proof predecessors.

## Corrected G2-01 candidate

This candidate supersedes earlier G2-01 attempts that bound older canonical
recovery states. It addresses the live review findings by:

1. freezing the current canonical pre-G2 `main` commit and exact Git tree;
2. binding the cold-boot userspace to a content-addressed OCI image and exact
   Python `3.11.16` runtime rather than a mutable hosted-runner label;
3. recomputing and verifying the dependency-lock, environment and all bound
   corpus/proof artifact digests;
4. verifying every path/digest in the frozen reference manifests against an
   exact clean reference checkout;
5. binding intentional-divergence waivers to exact reference output digest,
   exact candidate output digest and exact divergence-register generation;
6. keeping Gen-2 execution authority and self-construction disabled.

## Frozen artifacts

- `g2-01-gen1-reference-bundle.json` — schema `tenfold.gen1_reference.v2`;
- `g2-01-reference-corpus.sha256` — complete pre-G2 `src + tests + docs` corpus;
- `g2-01-semantic-corpus.sha256` — pre-G2 `src` corpus;
- `g2-01-qualification-fixture-corpus.sha256` — pre-G2 `tests` corpus;
- `g2-01-pip-freeze.txt` — exact dependency lock;
- `G2-01-cold-boot-procedure.md` — exact periodic proof procedure;
- `src/tenfold/gen2/reference.py` — fail-closed frozen-reference and differential harness;
- `tests/gen2/test_g2_01_reference.py` — permanent G2-01 negative fixtures;
- `.github/workflows/g2-01-reference-proof.yml` — content-addressed exact-reference proof lane.

## Current proof boundary

The bundle is intentionally `cold_boot_status = PENDING` in this frozen
candidate. A private/local run cannot substitute for the required exact Python
3.11.16 content-addressed repository proof.

Canonical recovery surfaces therefore still identify G2-01 as current until the
repository proof succeeds. They must advance **atomically** with the final G2-01
proof record; they are not changed early merely to make this candidate look
complete.

## Does not enable

- Gen-2 authoritative execution;
- authority migration;
- Gen-2 self-construction;
- G2-02 execution before this milestone reaches canonical `PROVEN`.
