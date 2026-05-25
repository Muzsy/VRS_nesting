# Runner — SGH-Q06 LossModel + smooth collision severity

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q06 taskot.

## Kötelező bemenetek

Olvasd el és tartsd be:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
canvases/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q06_loss_model_smooth_collision_severity.yaml
```

## Dependency gate

Normál gate:

```text
codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
```

első sora legyen `PASS`, és legyen érvényes `SGH-Q06_STATUS: READY` marker a Q05/Q05R vonalon.

Projektgazdai override: az SGH-Q05R2 dokumentációs cleanup elfogadottnak tekintendő, még ha az aktuális checkoutban nincs is benne. Ha a Q05 contractban még szerepel a régi `PhaseResult.best_score = min(...)` állítás, azt ismert Q05R2 dokumentációs késésként kezeld. Ez önmagában nem blokkolhatja Q06-ot.

Ne módosíts Q05/Q05R/Q05R2 fájlokat ebben a taskban.

## Kötelező Sparrow source audit

Ne README vagy korábbi összefoglaló alapján dolgozz. Használd a repo meglévő Sparrow source resolve mechanizmusát, például:

```bash
./scripts/ensure_sparrow.sh
```

majd auditáld az aktuális Sparrow source releváns fájljait, különösen:

```text
.cache/sparrow/src/quantify/overlap_proxy.rs
.cache/sparrow/src/quantify/tracker.rs
```

Ha az útvonal eltér, keresd meg valós fájlkereséssel. A reportban rögzítsd a ténylegesen olvasott pathokat és funkciókat.

Ha a source nem érhető el vagy a formula nem tisztázható, a report első sora `BLOCKED` vagy `REVISE`, és ne legyen `SGH-Q07_STATUS: READY` marker.

## Implementációs cél

Vezess be moduláris `LossModel` réteget:

```text
rust/vrs_solver/src/optimizer/loss_model.rs
```

Két modell kell:

```text
BboxAreaLoss
  - default
  - backward-compatible
  - pair_loss = legacy bbox dx*dy
  - boundary_loss = legacy 0/1 proxy

PolePenetrationSmoothLoss
  - Sparrow Algorithm 3 irányából
  - VRS rectangle/bbox surrogate adaptáció
  - smooth collision severity foundation
  - explicit korlát: nem CDE és nem irregular exact parity
```

Kösd be a separatorba:

```text
VrsSeparatorConfig.loss_model
VrsCollisionTracker.pair_loss / boundary_loss
VrsCollisionTracker::build
VrsCollisionTracker::update_placement
VrsCollisionTracker::snapshot_loss
VrsCollisionTracker::restore_but_keep_weights
```

A default config semmilyen meglévő viselkedést nem ronthat.

## Szigorú nem-célok

Ne nyisd meg:

```text
RotationPolicy / continuous rotation
CollisionBackend / jagua-rs CDE backend
exact irregular polygon collision
DXF/preflight
IO contract
Python runner
frontend/API
SheetElimination/BPP refaktor
PhaseOptimizer refaktor
Q05/Q05R/Q05R2 cleanup
```

## Kötelező tesztek

Minimum viselkedések:

```text
bbox_area_loss_matches_legacy_overlap_area
bbox_area_loss_preserves_binary_boundary_proxy
smooth_penetration_decay_is_continuous_at_epsilon
smooth_pair_loss_increases_with_overlap_depth
smooth_pair_loss_is_shape_scaled
smooth_boundary_loss_increases_with_violation_depth
separator_default_loss_model_preserves_existing_behavior
separator_can_use_smooth_loss_model
restore_but_keep_weights_preserves_weights_with_loss_model
same_seed_same_loss_model_determinism
```

A pontos tesztnevek igazodhatnak a repo stílusához, de ezek a viselkedések legyenek bizonyítva.

## Dokumentáció és report

Hozd létre/frissítsd:

```text
docs/egyedi_solver/sgh_q06_loss_model_contract.md
codex/codex_checklist/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.verify.log
```

A report első sora csak akkor lehet `PASS`, ha minden DoD és verify zöld. PASS esetén a report végén legyen:

```text
SGH-Q07_STATUS: READY
```

Ha bármelyik teszt vagy verify fail, a report első sora `REVISE` vagy `BLOCKED`, és ne legyen SGH-Q07 marker.

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::loss_model
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
```
