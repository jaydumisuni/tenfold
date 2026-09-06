# PM-ECO-PROGRESS-001 — Eco-progress Execution Profile

Status: **PROVISIONAL**  
Revision: **0.1.0**  
Project: **eco-progress**  
Applicable global methods: **OM-001**

## Purpose

Describe the current evidence-backed way to use Tenfold on Eco-progress without changing Eco-progress architecture, roadmap authority, release authority, or Tenfold founding authority.

## Project authority / recovery sources

Recover these sources before substantial work:

- `jaydumisuni/Eco-progress` canonical repository;
- `ROADMAP.md`;
- `docs/superpowers/specs/2026-09-05-eco-progress-github-native-design.md`;
- `docs/superpowers/plans/2026-09-05-ep15-full-ecosystem-import-governance-implementation.md` for the active EP15 campaign;
- the accepted predecessor commit named by the active plan; for EP15 this is `cc28f9f819a5209b5ac6094a3f30cfe5b8835a7b`;
- current Project Zero evidence and progress policy;
- current GitHub review/workflow evidence;
- Tenfold `docs/00-founding-authority.md`, `docs/02-assurance-matrix.md`, and OM-001.

## Current execution topology

Eco-progress uses a private implementation branch/workspace as the construction and proof plane and `main` as the canonical promotion surface.

For EP15:

```text
EP14 main @ cc28f9f819a5209b5ac6094a3f30cfe5b8835a7b
        |
        v
implementation/ep15-full-ecosystem-import-governance
        |
        +-- recovered ecosystem authority
        +-- TDD RED -> GREEN
        +-- focused EP15 proof
        +-- adversarial Review
        +-- full regression/schema proof
        +-- exact candidate-byte freeze
        +-- Tenfold Council / required assurance
        |
        v
single coherent EP15 product commit
sole parent = frozen EP14 commit
        |
        v
main fast-forward + exact-head confirmation
```

Temporary CI, campaign drivers, proof transport, and workspace-only Tenfold machinery are non-product and must not leak into the final canonical product tree unless project authority explicitly promotes them.

## Project-specific method rules

### Rule 1 — Registration is authority-gated, never observation-derived

- **Rule:** Account ownership, repository visibility, name similarity, fork/mirror presence, or donor/reference use cannot self-register a project.
- **Why:** EP15 separates observable repository inventory from admitted ecosystem membership.
- **Evidence:** EP15 classification/relationship tests and Task 8 adversarial review.
- **Status:** Mandatory for EP15.

### Rule 2 — Preserve frozen predecessor authority exactly

- **Rule:** Existing frozen Eco-progress and Hunter registry identities/authority from EP14 remain unchanged unless higher project authority explicitly changes them.
- **Why:** EP15 Review already exposed an attempted predecessor-authority drift during import work.
- **Evidence:** `tests/ep15-review.test.ts` and the frozen EP14 predecessor.
- **Status:** Mandatory.

### Rule 3 — Dependency closure contains registered identities only

- **Rule:** Unregistered targets stay explicit unresolved/external records and must not become graph nodes by inference.
- **Why:** The Eco-progress dependency model treats registry membership as the canonical graph boundary.
- **Evidence:** EP15 dependency-closure tests.
- **Status:** Mandatory.

### Rule 4 — UNSCORED is not zero

- **Rule:** Missing target authority or inadequate proof remains explicitly UNSCORED/UNAVAILABLE/RECONCILIATION_REQUIRED as applicable; no percentage is fabricated.
- **Why:** Zero is a scored result and would misrepresent missing authority/evidence.
- **Evidence:** eligibility and EP15 integration tests.
- **Status:** Mandatory.

### Rule 5 — Public repository observability does not expose private project relationships

- **Rule:** Coverage/public projections are compiled only from permitted visibility and cannot infer private membership from a public repository.
- **Why:** Repository visibility and project relationship visibility are different authorities.
- **Evidence:** EP15 coverage and Task 8 review tests.
- **Status:** Mandatory.

### Rule 6 — Final EP15 history is synthesized from reviewed product bytes

- **Rule:** The final EP15 product commit must have the frozen EP14 commit as its sole parent and contain reviewed product bytes only.
- **Why:** The active plan explicitly requires temporary CI/workspace/Tenfold material to remain outside canonical history and requires a coherent milestone commit.
- **Evidence:** EP15 Task 9 plan plus OM-001.
- **Status:** Mandatory for this campaign.

## Dependency-frontier strategy

- Derive work from registered project identity and explicit dependency relationships only.
- Treat unresolved/unregistered repositories as classification work, not implicit graph nodes.
- Continue independent review, evidence recovery, and candidate preparation when a later promotion gate is pending.
- Serialize writes to coupled authority surfaces such as `config/ecosystem.json`, Project Zero evidence, and final publication refs.
- Re-run closure/cycle proof after dependency edits. A reverse Hunter/Pete edge discovered during EP15 Review demonstrated that apparently plausible edges can create invalid cycles.

## Workspace / isolation strategy

- Bind the campaign to the exact accepted predecessor before mutation.
- Use the dedicated implementation branch for EP15 construction.
- Keep temporary branch-only CI/proof harnesses disposable.
- Keep one write owner for registry, Project Zero evidence, and final candidate synthesis.
- Before promotion, re-read `main` and require it still equals the frozen predecessor.
- Any candidate-byte movement invalidates the previous freeze/proof binding.

## Test / proof escalation

Preferred EP15 escalation:

```text
small RED discriminator
  -> GREEN implementation
  -> focused EP15 integration corpus
  -> Project Zero reproduction
  -> frozen Hunter reproduction
  -> adversarial review corpus
  -> full npm test regression
  -> schema validation
  -> exact-candidate proof
  -> Tenfold Council + required independent assurance
  -> exact-head post-promotion confirmation
```

Tests confirm recovered engineering contracts; they do not substitute for authority recovery.

## Canonical publication strategy

- `main` receives one coherent EP15 product commit when all gates pass.
- That commit has the frozen EP14 commit as sole parent.
- Temporary `.github` development CI added only for private proof must not enter the final product tree unless it was already canonical or separately approved.
- Temporary Tenfold checkout/runtime material, campaign drivers, logs, and proof transport remain disposable.
- EP15's own final SHA is recorded only by a subsequent evidence update if the active project plan requires that sequencing.

## Physical / external gate strategy

EP15 has no physical-device mutation requirement in the recovered plan. External gates are repository state, GitHub proof environment, Tenfold assurance, and final canonical ref promotion. If a hosted runner cannot execute a required proof accurately, hold that proof gate or change the proof environment; do not weaken product truth.

## Reusable construction assets

- `tests/fixtures/ep15/recovered.ts` — recovered approved registry/repository observations;
- `tests/ep15-ecosystem.test.ts` — EP15 integrated exit-gate corpus;
- `tests/ep15-review.test.ts` — imported-registry adversarial review;
- existing discovery/classification/relationship/coverage review suites;
- `tests/self.test.ts` — Project Zero transition reproduction;
- `tests/hunter.test.ts` — frozen Hunter model reproduction;
- branch-only EP15 development workflow for remote proof while construction is active.

## Current measurements / observations

Evidence recovered during the active EP15 campaign:

- Task 8 integrated/review state reached 254/254 passing tests with schema validation PASS before Task 9 self-transition work.
- Task 9 RED correctly produced three intended Project Zero failures before EP14 evidence admission.
- After EP14 evidence admission, a broader regression exposed one stale Project Zero expectation inside the Hunter reproduction suite; this was classified as a test expectation coupled to the old EP13->EP14 frontier, not a product-model defect.
- Review caught two material campaign defects before canonical publication: predecessor authority drift and a reverse dependency that would have introduced a cycle.
- No canonical EP15 promotion has occurred at this profile revision.

## Known project-specific failure modes

- treating account/repository observation as project registration;
- admitting forks, mirrors, donors, or references as ecosystem members;
- allowing public repository visibility to disclose private project relationships;
- allowing stale/lower-authority evidence to override accepted target authority;
- collapsing UNSCORED into `0%`;
- auto-creating dependency nodes for unregistered targets;
- creating duplicate project identity during rename/support/legacy resolution;
- mutating frozen EP14 registry authority during import;
- introducing a reverse dependency that creates a cycle;
- updating the primary Project Zero test while leaving a secondary reproduction suite bound to the old frontier;
- leaking temporary CI/Tenfold proof machinery into canonical product history;
- proving one branch head and promoting different bytes.

## Method discovery targets

- reduce repeated Project Zero frontier expectations duplicated across suites;
- make exact-candidate proof binding and product-tree exclusion checks more automated;
- improve automated detection of temporary proof artifacts before candidate synthesis;
- measure whether dedicated adversarial review grouping lowers later full-regression rework.

## Candidate lessons for global promotion

- When a project has multiple independent reproductions of the same derived frontier, transition work should enumerate and rebind all reproductions before GREEN is claimed. Keep project-specific until repeated elsewhere.
- Product-tree synthesis from an exact predecessor is useful where private branch history intentionally contains disposable proof machinery; cross-project evidence is required before promoting this beyond OM-001 guidance.

## Revision history

### 0.1.0 — 2026-09-06

Initial provisional Eco-progress profile recovered during EP15 Task 9 before broad Tenfold campaign execution.
