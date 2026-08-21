# G2-01 — Gen-1 Reference and Inheritance Freeze — Review / Proof Record

**Status:** PROVEN  
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01  
**Canonical Gen-1 migration reference:** `486b75d6e050cec6f143d77460e4f2a748858f94`

## Construction authority

Qualified Tenfold Gen 1 executed the G2-01 campaign in the private workspace. The independently assured campaign bound:

- blueprint digest `9a1053b920046a6c65929a59b1d66cbf72831c18d3cdbbb13218eb1c819be0a5`;
- campaign digest `16790615f29fab3a299fa8ef5238901d38f2e7935b89b5303f98a73fe064e528`;
- independent derivation proof `458c76282892151d9b062c07f4f339c68bf8a90f767ce8a253395cb6f1306cf1`;
- frozen source reference `486b75d6e050cec6f143d77460e4f2a748858f94`.

The exact reference environment was independently cold-booted on Python 3.11.16 with pinned dependencies and Sergeant `4a277cc5950aa08a98157b950c96fb88f2178c79`; repository-only proof returned **158 passed**.

## Accepted G2-01 artifacts

- `g2-01-gen1-reference-bundle.json` — exact SHA, runtime/dependency lock, environment digest/lineage, dispositions, divergence register, reference coverage and interim Root binding.
- `g2-01-reference-corpus.sha256` — 65-file Git-tracked source/fixture/document corpus manifest recovered from the exact reference; generated caches/install products are excluded by construction.
- `g2-01-pip-freeze.txt` — normalized dependency lock.
- `g2-01-cold-boot-proof.txt` — exact reference proof result.
- `G2-01-cold-boot-procedure.md` — permanent periodic cold-boot procedure.
- `src/tenfold/gen2/reference.py` — frozen-reference model and permanent differential harness.
- `tests/gen2/test_g2_01_reference.py` — G2-01 fail-closed fixtures.

## Review / assurance

Artifact evidence digests:

- `019533f380c6ff050fd9e1cb19e3b724d19740d5e3de050f6045ed82f7915378`
- `becd207efd951a52b4296903ce1734ae5b27077afd862e6be6321eaa632c3089`
- `b7429831dd95868a2fd733ccfcb1c5bf810dcfb5e7c5293e853a34367862a75c`
- `f02804cb94b00a6d0bd746bb388155011dc463af7f50a9fdfb6267945c3968d6`
- `5e2ee438b6921852fb364f0877144dcb8b7cfa4e24a510395046599f4f4951fd`
- `28d5addf9439ff645d6c7cf918091739fd1b01790d0ffe72aac3c17f1c470065`
- `5f59a7c09322594ef035f881d431d1cd9d160090b778cfcb50beedcf4837d5b4`

Independent authority-review request: `65b2d48d66206d8f6190ad2b479203e22e5cb44631bf75b9bf4344fd2a7f2d07`  
Independent authority-review response: `6815a41513f12a95e0b0de017d981cfa3b123c446353315f3c39c99c2351c93d`  
Assurance satisfaction record: `f3aa53937491146727e9174f55ffa25d88f75f816ccf9e1a00eb2dd897b65dfd`  
Milestone Council: `bc932e4373454e6c216469e0aa2d04df29977f627648c25eac115c859e301ae5`

The independent reviewer was deliberately separate from the Gen-2 reference producer: stdlib-only, raw frozen-authority checks, no import of `tenfold.gen2.reference`.

## Acceptance reconciliation

- exact reference environment cold-boots: **PASS**;
- semantic/fixture corpora reproduce accepted Gen1 results: **PASS**;
- every inherited component has exactly one disposition: **PASS**;
- no unregistered initial divergence: **PASS** (`Intentional Divergence Register = []`);
- interim Root provenance/exclusions exact: **PASS**;
- Gen2 execution authority enabled: **NO**;
- self-construction enabled: **NO**.

## Next frontier

After G2-01 reached `PROVEN`, the Gen-1 Foreman exposed only:

```text
READY: G2-02 — Constitutional Schema and Policy Foundation
```

G2-03…G2-30 remain blocked by the frozen roadmap dependency chain.
