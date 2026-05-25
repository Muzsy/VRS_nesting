# Runner — SGH-Q07 RotationPolicy + continuous rotation foundation

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q07 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md
```

Első sor: `PASS`.

A reportban legyen:

```text
SGH-Q07_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md
docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md
docs/egyedi_solver/sgh_q06_loss_model_contract.md
canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07_rotation_policy_continuous_foundation.yaml
```

## Kötelező source audit

Ne korábbi összefoglalóból dolgozz. Használd a valós source-t.

```bash
./scripts/ensure_sparrow.sh
```

Majd fájlkereséssel azonosítsd és auditáld:

```text
jagua-rs RotationRange / allowed_rotation modell
Sparrow uniform rotation sampling
Sparrow search_position/search_placement
Sparrow coordinate descent / rotation wiggle
```

A reportban szerepeljen a tényleges path + struct/function név. Ha ez hiányzik, report: `REVISE` vagy `BLOCKED`.

## Implementációs cél

Vezess be moduláris rotation policy réteget:

```text
locked/no_rotation
half_turn
orthogonal
forty_five
explicit discrete
continuous
```

Kötelező:

```text
- legacy allowed_rotations_deg továbbra is működik
- global SolverInput rotation policy opcionális
- part-level rotation policy opcionális és erősebb, mint a global
- 45° és arbitrary discrete szögek működnek rectangular bbox proxyval
- continuous policy seedelt, determinisztikus, és tényleg ad non-orthogonal angle candidate-eket
- 0/90/180/270 legacy eredmények nem romlanak
```

Ha a `Placement.rotation_deg` i64 miatt nem lehet valódi continuous rotationt tárolni, migráld f64-re kontrolláltan. Ne hagyj fake continuous policyt, amely végül csak integer/orthogonal szöget tud commitolni.

## Nem cél

Ne csináld meg Q07-ben:

```text
jagua-rs CDE backend
exact irregular polygon rotation/collision
hole/cavity kezelés
DXF/preflight refaktor
külső benchmark backend
új optimizer stratégia
```

## Kötelező tesztek

Minimum:

```text
rotation_policy_locked_generates_only_zero
rotation_policy_half_turn_generates_0_180
rotation_policy_orthogonal_matches_legacy_0_90_180_270
rotation_policy_forty_five_generates_8_angles
legacy_allowed_rotations_deg_still_supported
part_policy_overrides_global_policy
global_policy_used_when_part_has_no_explicit_policy
arbitrary_45_degree_bbox_math_is_correct
continuous_policy_generates_non_orthogonal_angles
continuous_policy_same_seed_is_deterministic
continuous_rotation_can_fit_rectangle_that_orthogonal_cannot
separator_uses_rotation_policy_not_hardcoded_orthogonal
compression_uses_rotation_policy_not_hardcoded_orthogonal
```

Használható fit fixture:

```text
part: 100 x 20
sheet: 90 x 90
orthogonal: fail
45° / continuous candidate: pass
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml item
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
```

## Report és marker

Hozd létre/frissítsd:

```text
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
codex/codex_checklist/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.verify.log
```

A report első sora csak teljes zöld verify esetén lehet `PASS`.

PASS esetén a report végén legyen:

```text
SGH-Q08_STATUS: READY
```
