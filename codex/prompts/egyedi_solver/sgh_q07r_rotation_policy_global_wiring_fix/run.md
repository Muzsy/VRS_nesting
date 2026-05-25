# Runner — SGH-Q07R RotationPolicy global wiring + seed propagation fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q07R javító taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
```

Első sor: `PASS`.

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r_rotation_policy_global_wiring_fix.yaml
```

## Javítandó hiba

Az SGH-Q07 nem elég, mert a globális `SolverInput.rotation_policy` jelenleg a valós solve pathban nem biztos, hogy hat.

Ellenőrizd ezekkel:

```bash
rg "rotation_policy" rust/vrs_solver/src
rg "resolve_part_rotation_angles\([^\n]*None, 0, 8" rust/vrs_solver/src
rg "expand_instances\(&input.parts\)" rust/vrs_solver/src
rg "can_fit_any_stock\(" rust/vrs_solver/src
```

A reportban rögzítsd a pre-fix találatokat, majd a javítás után az összes megmaradó előforduláshoz adj indoklást.

## Implementációs cél

Javítsd úgy a Q07-et, hogy igaz legyen a teljes solve pathra:

```text
Part.rotation_policy > legacy Part.allowed_rotations_deg > SolverInput.rotation_policy > Orthogonal fallback
```

Kötelező:

```text
- adapter::solve átadja input.rotation_policy-t és input.seedet az instance expansion/pre-filter útvonalra
- global forty_five policy ténylegesen tudjon placementet eredményezni valós solve-on
- continuous policy ne hardcoded seed 0-val dolgozzon
- legacy allowed_rotations_deg precedence ne romoljon
- part-level policy precedence ne romoljon
- same input + same seed determinisztikus marad
```

## Nem cél

Ne implementáld Q08-at:

```text
jagua-rs CDE backend
exact irregular polygon collision
hole/cavity semantics
DXF/preflight refaktor
új optimizer stratégia
```

## Kötelező regression fixture

Készíts valós adapter/solve tesztet:

```text
stock: 90 x 90, quantity 1
part: 100 x 20, quantity 1, allowed_rotations_deg üres, part.rotation_policy None
case A: global rotation_policy absent vagy orthogonal => unplaced / not ok
case B: global rotation_policy forty_five => placed / ok
```

Ez bizonyítja, hogy a globális policy nem csak helper unit tesztben működik.

## Kötelező tesztek

Minimum:

```text
global_forty_five_policy_affects_expand_instances_when_part_has_no_legacy_rots
global_continuous_policy_affects_expand_instances_when_part_has_no_legacy_rots
adapter_solve_global_forty_five_places_100x20_on_90x90_sheet
adapter_solve_legacy_allowed_rotations_overrides_global_policy
part_policy_overrides_global_policy_in_real_solve_path
continuous_policy_same_seed_deterministic_through_solve
continuous_policy_different_seed_changes_resolved_candidate_angles
no_remaining_production_none_zero_eight_policy_resolution_without_justification
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml item
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q08_STATUS: READY`.

## Report

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.verify.log
```

PASS esetén a report végén legyen:

```text
SGH-Q08_STATUS: READY
```
