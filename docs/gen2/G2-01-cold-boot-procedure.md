# G2-01 Gen-1 Cold-Boot Proof Procedure

Status: **FROZEN PROCEDURE**

Authority: TF-00 + G2-00 §§3, 3.1, 3.2 + G2-01.

The migration reference is `486b75d6e050cec6f143d77460e4f2a748858f94`.

A valid periodic cold boot must start from a clean checkout/worktree of that exact SHA, use Python 3.11 with the exact dependency lock recorded in `g2-01-gen1-reference-bundle.json`, install pinned Sergeant `4a277cc5950aa08a98157b950c96fb88f2178c79`, compile `src`, and run the repository-only qualification with both `TENFOLD_REPOSITORY_ONLY_PROOF=1` and `TENFOLD_CANDIDATE_SHA` bound to the migration SHA.

The run is invalid if the checkout is dirty, a moving ref is used, the dependency lock differs, the Sergeant authority version differs, repository-only proof is disabled, or any required test is skipped/fails.

The initial G2-01 evidence run used Python `3.11.16`, pip `26.2.1`, and completed `158 passed` with no skip in the repository-only lane.
