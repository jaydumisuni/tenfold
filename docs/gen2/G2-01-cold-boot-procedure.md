# G2-01 Gen-1 Cold-Boot Proof Procedure

**Status:** FROZEN PROCEDURE CANDIDATE
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01

The Gen-1 migration reference is the exact canonical pre-G2 state:

- commit `05aa384a34a650e677970904079a985ec8b26d90`;
- Git tree `c7c130b573180e74438d70b6e11c17dd9bade648`.

A valid G2-01 cold boot must use the exact environment identity recorded in
`g2-01-gen1-reference-bundle.json`:

- platform `linux/amd64`;
- OCI image `mcr.microsoft.com/playwright/python:v1.57.0-amd64@sha256:8331696befd3ee8b5baefca428446345f548e415a2408fe1d3d1224e9d919682`;
- `actions/checkout@11d5960a326750d5838078e36cf38b85af677262`;
- `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`;
- Python exactly `3.11.16`;
- pip exactly `26.2.1`;
- the complete dependency lock in `g2-01-pip-freeze.txt`;
- Sergeant exactly `4a277cc5950aa08a98157b950c96fb88f2178c79`.

Because Gen 1 deliberately sanitizes worker subprocess environments and does not
forward `LD_LIBRARY_PATH`, the exact setup-python runtime's
`libpython3.11.so.1.0` must be copied into `/usr/local/lib` and registered with
`ldconfig` before qualification. The procedure must verify that the copied
library is byte-identical to the setup-python source library and that Python
3.11.16 launches successfully under an environment containing only the same
ordinary variables Gen-1 workers preserve. The final cold-boot proof records the
SHA-256 of that shared library and its loader path. This is proof-substrate
materialization only; it does not modify Gen-1 source or authority.

The hosted `runs-on` label is transport, not the reproducibility identity. The
content-addressed OCI image plus platform and pinned setup actions are the bound
execution substrate.

The content-addressed Playwright image also supplies the Chromium binary and its
system libraries required by the accepted Gen-1 browser fixture. The procedure
must discover exactly one executable `chrome` inside `/ms-playwright`, expose it
as `/usr/local/bin/chromium`, and record its resolved path, version and SHA-256.
A missing or ambiguous browser binding is a proof failure; the browser fixture may
not be converted into a skip merely because the proof substrate omitted Chromium.


The proof procedure must independently verify the frozen commit/tree, validate
all three corpus manifests against a clean checkout of that exact reference,
compile `src`, and execute the repository-only Gen-1 qualification suite with
`TENFOLD_REPOSITORY_ONLY_PROOF=1` and `TENFOLD_CANDIDATE_SHA` bound to the
migration reference.

A run is invalid if any bound identity moves, any corpus file differs, the
reference checkout is dirty, a required test skips/fails, or the proof artifact
cannot be bound by SHA-256 into the final G2-01 reference bundle.

The executable procedure is `.github/workflows/g2-01-reference-proof.yml`.
