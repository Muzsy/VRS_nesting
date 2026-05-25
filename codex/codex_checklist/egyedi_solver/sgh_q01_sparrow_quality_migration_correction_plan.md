# Checklist — SGH-Q01 `sgh_q01_sparrow_quality_migration_correction_plan`

## Dependency

- [x] SGH-Q00 report létezik.
- [x] SGH-Q00 report első sora PASS vagy PASS_WITH_NOTES.
- [x] SGH-Q00 report tartalmazza: SGH-Q01_STATUS: READY.

## Inputs

- [x] SGH-Q00 audit elolvasva.
- [x] SGH-Q00 gap matrix elolvasva.
- [x] SGH-Q00 modular principles elolvasva.
- [x] SGH-01..SGH-05 contractok elolvasva.
- [x] Releváns Rust anchorok auditálva.

## Outputs

- [x] `docs/egyedi_solver/sgh_q01_sparrow_quality_migration_correction_plan.md` elkészült.
- [x] `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md` elkészült.
- [x] `docs/egyedi_solver/sgh_q01_no_downgrade_acceptance_gates.md` elkészült.

## Content

- [x] SGH-06 paused döntés szerepel.
- [x] SGH-01..SGH-05 keep/stop/replace táblázat szerepel.
- [x] Minden MISSING/PROXY/PARTIAL feature migration decisiont kapott.
- [x] RotationPolicy track szerepel.
- [x] CollisionBackend/CDE track szerepel.
- [x] LossModel/collision severity track szerepel.
- [x] GLS/separator parity track szerepel.
- [x] multi-worker / move_items_multi track szerepel.
- [x] exploration/compression track szerepel.
- [x] infeasible pool/disruption track szerepel.
- [x] benchmark/acceptance parity gate-ek szerepelnek.
- [x] no-downgrade gate-ek konkrétak.

## Scope

- [x] Nem történt production kódmódosítás (csak komment-szintű annotáció).
- [x] Nincs vendor/submodule.
- [x] Nincs külső backend.
- [x] Nincs benchmark kampány.

## Verify

- [x] Report első sora PASS/PASS_WITH_NOTES/FAIL/BLOCKED.
- [x] DoD -> Evidence Matrix szerepel.
- [x] verify.sh lefutott.
- [x] Zöld esetben: SGH-Q02_STATUS: READY.
