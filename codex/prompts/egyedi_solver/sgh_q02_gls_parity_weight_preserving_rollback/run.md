# Runner prompt — SGH-Q02 `sgh_q02_gls_parity_weight_preserving_rollback`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-Q02 taskot:

```text
SGH-Q02 — GLS parity + weight-preserving rollback
```

Ez implementációs task, de szűk scope-pal. A cél a meglévő `VrsSeparator` GLS/rollback alapjának javítása Sparrow-parity irányba.

**Production scope:** alapértelmezetten csak:

```text
rust/vrs_solver/src/optimizer/separator.rs
```

Dokumentáció/report/checklist scope:

```text
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

---

## Dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

Feltételek:

```text
első sor: PASS vagy PASS_WITH_NOTES
tartalmazza: SGH-Q02_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency részét frissítsd.

---

## Kötelező olvasmányok

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_sparrow_jagua_quality_feature_parity_audit.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q00_modular_architecture_principles.md
docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md
codex/reports/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md
```

Auditáld a valós kódot:

```text
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
```

---

## Implementációs követelmény

### 1. Multiplicative GLS

A jelenlegi additive formula nem maradhat végleges Q02 után:

```rust
*w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max)
```

Helyette Sparrow Algorithm 8 jellegű formula kell:

```text
max_loss = maximum active pair/boundary loss
loss == 0:
    multiplier = decay
loss > 0:
    multiplier = min_inc_ratio + (max_inc_ratio - min_inc_ratio) * (loss / max_loss)
new_weight = clamp(old_weight * multiplier, 1.0, weight_max)
```

Elvárások:

```text
- max_loss normalizáció ténylegesen legyen benne;
- pair és boundary collision is ugyanazon elv szerint frissüljön;
- non-colliding, de korábban súlyozott pair decay-eljen vissza 1.0 felé;
- ne hozz létre minden nulla-loss pairhez feleslegesen weight entry-t;
- ne törj el meglévő publikus config mezőket;
- minden új mező defaultot kapjon;
- frissítsd a QUALITY_RISK annotációt: AdditiveGlsProxy többé nem lehet aktuális állítás.
```

### 2. `restore_but_keep_weights`

Adj `VrsCollisionTracker` loss-state snapshotot.

A snapshot tartalmazza:

```text
bboxes
boundary_valid
minden olyan tracker mező, amelyből loss számolódik
```

A restore **nem** állíthatja vissza:

```text
pair_weights
boundary_weights
```

A rollback pontokon a helper-t használd úgy, hogy failed tentative move után:

```text
current layout visszaáll;
tracker loss-state visszaáll;
GLS weights megmaradnak;
update_weights a megmaradt súlyokon fut tovább.
```

### 3. Ne nyisd meg a következő scope-okat

Tilos ebben a taskban:

```text
multi-worker / rayon
random shuffle / stochastic ordering
exploration/compression phase orchestration
infeasible solution pool
large-item disruption
continuous rotation
CollisionBackend / CDE backend
smooth LossModel / pole penetration
IO contract módosítás
Python runner módosítás
külső Sparrow backend/vendor/submodule
```

---

## Kötelező tesztek

Adj/frissíts teszteket legalább ezekre:

```text
1. Multiplicative GLS: nagyobb loss nagyobb vagy egyenlő weight növekedést kap.
2. Max-loss normalizáció: max loss entry normalizált ratio-ja 1.0.
3. No-collision decay: meglévő weight 1.0 felé csökken, de nem 1.0 alá.
4. Boundary collision weight ugyanazzal az elvvel frissül.
5. restore_but_keep_weights: loss-state visszaáll, pair_weights és boundary_weights megmarad.
6. Egyszerű overlap separator fixture továbbra is best_loss == 0.0.
7. Determinism: azonos input + azonos config → bit-identical output/diagnostics.
```

---

## Contract dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md
```

Kötelező szekciók:

```text
# SGH-Q02 GLS parity + weight-preserving rollback contract
## Decision
## Source Sparrow feature mapping
## VRS implementation summary
## GLS formula
## Config semantics
## Collision/boundary weight handling
## restore_but_keep_weights contract
## Rollback invariants
## Tests and acceptance gates
## Remaining quality gaps after SGH-Q02
## Next task: SGH-Q03
```

---

## Report és checklist

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

A report tartalmazzon:

```text
Dependency evidence
Source evidence
Current-state audit
Change summary
Config semantics
F07/F08 parity status update
No-downgrade gates G01-G08
Tests run + exact command output summary
Scope safety
DoD -> Evidence Matrix
```

Ha minden zöld, a report végén legyen:

```text
SGH-Q03_STATUS: READY
```

---

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md
```

Ha bármelyik fail, a report első sora nem lehet PASS.
