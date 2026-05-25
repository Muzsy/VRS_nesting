# Checklist — SGH-Q07R2 `sgh_q07r2_phase_rotation_context_wiring_fix`

## Dependency gate

- [x] SGH-Q07R report létezik: `codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md`
- [x] SGH-Q07R report első sora: PASS
- [x] Q07R fájlok nem módosítva ebben a taskban

## Preflight reads

- [x] AGENTS.md átolvasva
- [x] docs/codex/overview.md átolvasva
- [x] docs/codex/yaml_schema.md átolvasva
- [x] docs/codex/report_standard.md átolvasva
- [x] docs/qa/testing_guidelines.md átolvasva
- [x] canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md átolvasva
- [x] canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md átolvasva
- [x] docs/egyedi_solver/sgh_q07_rotation_policy_contract.md átolvasva
- [x] canvases/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md átolvasva
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r2_phase_rotation_context_wiring_fix.yaml átolvasva

## Pre-fix kódaudit

- [x] `explore.rs:183` — `MoveExecutor::new(parts, sheets)` (legacy default) a production pathban
- [x] `compress.rs:40` — `MoveExecutor::new(parts, sheets)` (legacy default) a production pathban
- [x] `compress.rs:41` — `RotationResolveContext::legacy_default()` lokálisan létrehozva
- [x] `explore.rs:259` — `VrsSeparatorConfig { seed, worker_count, ..Default::default() }` — rotation_context hiányzott

## Implementáció

- [x] `rust/vrs_solver/src/optimizer/explore.rs` javítva
  - `LargeItemSwapDisruption` struktúrába `rotation_context: RotationResolveContext` mező hozzáadva
  - `LargeItemSwapDisruption::new_with_rotation_context(...)` konstruktor bevezetve
  - `LargeItemSwapDisruption::new(...)` → `new_with_rotation_context(..., legacy_default())` wrapper (teszt backward compat)
  - `try_disrupt()` → `MoveExecutor::new_with_rotation_context(..., self.rotation_context.clone())`
  - `ExplorationPhase::new()` → `LargeItemSwapDisruption::new_with_rotation_context(..., config.rotation_context.clone())`
  - `ExplorationPhase::run()` separator config → `rotation_context: self.config.rotation_context.clone()` hozzáadva
- [x] `rust/vrs_solver/src/optimizer/compress.rs` javítva
  - `RotationResolveContext::legacy_default()` lokális eltávolítva
  - `MoveExecutor::new(parts, sheets)` → `MoveExecutor::new_with_rotation_context(parts, sheets, rotation_context.clone())`
  - `rotation_context = &self.config.rotation_context` (nem lokális, hanem a PhaseConfig-ból)
  - `RotationResolveContext` import eltávolítva (már nem szükséges közvetlenül)

## Post-fix kódaudit

- [x] `explore.rs` production pathban nincs `MoveExecutor::new` legacy defaulttal → PASS
- [x] `compress.rs` production pathban nincs `MoveExecutor::new` legacy defaulttal → PASS
- [x] `compress.rs` production pathban nincs `RotationResolveContext::legacy_default()` → PASS
- [x] `explore.rs` VrsSeparatorConfig tartalmazza `rotation_context: self.config.rotation_context.clone()` → PASS

## Tesztek

### explore.rs tesztek (3 új, SGH-Q07R2)

- [x] `exploration_separator_uses_phase_rotation_context`
- [x] `exploration_disruption_uses_phase_rotation_context_for_move_executor`
- [x] `no_production_legacy_context_in_explore_or_compress_phase_paths`

### compress.rs tesztek (2 új, SGH-Q07R2)

- [x] `compression_uses_phase_rotation_context_for_candidate_rotations`
- [x] `compression_move_executor_uses_phase_rotation_context`

## Verification

- [x] `cargo test optimizer::explore` → 9/9 PASS (6 meglévő + 3 új)
- [x] `cargo test optimizer::compress` → 6/6 PASS (4 meglévő + 2 új)
- [x] `cargo test --lib` → 224/224 PASS (211 meglévő + 13 új)
- [x] `./scripts/verify.sh --report ...` → lásd report AUTO_VERIFY szekció

## Default no-downgrade gate

- [x] `LargeItemSwapDisruption::new(...)` backward compat (teszt-only legacy wrapper) → PASS
- [x] Minden pre-Q07R2 teszt zöld (211 → 224, 13 új)

## Documentation

- [x] `docs/egyedi_solver/sgh_q07_rotation_policy_contract.md` Q07R2 addendummal frissítve (linter által)
- [x] `codex/codex_checklist/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md` elkészült
- [x] `codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md` elkészült

## No-scope-violation gate

- [x] jagua-rs CDE backend: NEM módosítva
- [x] LossModel refaktor: NEM módosítva
- [x] BPP refaktor: NEM módosítva
- [x] DXF/preflight: NEM módosítva
- [x] Q07R fájlok: NEM módosítva
- [x] Q08 implementáció: NEM megkezdve
