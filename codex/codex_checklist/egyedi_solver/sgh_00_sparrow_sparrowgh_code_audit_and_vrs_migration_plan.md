# Checklist — SGH-00 `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`

## Dependency gate

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` létezik.
- [x] JG-20 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] JG-20 report tartalmazza: `PHASE2_GATE_DECISION: PASS`.
- [x] Nincs JG-20 által jelölt unresolved `STOP`, `NO-GO`, boundary vagy exact validation blocker.
- [x] Dependency evidence dokumentálva a SGH-00 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] Jagua optimizer master plan / task index / progress checklist elolvasva.
- [x] Jelenlegi `rust/vrs_solver/src/optimizer/*.rs` modulok auditálva.
- [x] Runner/exact validator útvonal auditálva.

## External source audit

- [x] `JeroenGar/sparrow` elérhetősége, ref/commit és license dokumentálva.
- [x] `coroush/sparrow` vagy releváns SparrowGH/coroush source elérhetősége, ref/commit és license dokumentálva.
- [x] `coroush/sparrow-grasshopper` elérhetősége vagy hiánya dokumentálva.
- [x] Eredeti Sparrow releváns optimizer/search/tracker fájljai auditálva vagy `NOT_FOUND` jelölve.
- [x] SparrowGH/coroush BPP `bp_optimizer` fájljai auditálva vagy `NOT_FOUND` jelölve.
- [x] File-by-file audit tartalmazza: repo, ref, path, relevant functions/types, VRS relevance, porting risk.

## Migration plan

- [x] Elkészült `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md`.
- [x] Elkészült `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md`.
- [x] A terv kimondja: nincs külső SparrowGH benchmark backend.
- [x] A terv saját VRS optimizerbe portolt/újraimplementált algoritmusokra épül.
- [x] VRS module mapping elkészült.
- [x] State model / infeasible working layout kérdés kezelve.
- [x] Per-sheet separator terv kezelve.
- [x] LBF + separator fallback construction terv kezelve.
- [x] Sheet elimination / bin reduction terv kezelve.
- [x] Transfer/swap/reinsert move operator terv kezelve.
- [x] Solution pool / perturbation / stagnation handling terv kezelve.
- [x] Scoring és exact validation integráció kezelve.
- [x] Irregular/remnant és allowed rotations policy kezelve.
- [x] Rollback és risk terv szerepel.

## Follow-up tasks

- [x] SGH-01…SGH-N tasklánc megadva.
- [x] Minden következő taskhoz cél, dependency, javasolt output és acceptance gate szerepel.
- [x] `SGH-01_STATUS: READY` csak akkor szerepel, ha az audit és migrációs terv tényleg kész.

## Scope safety

- [x] Nem történt production Rust optimizer kódmódosítás.
- [x] Nem történt Python runner / exact validator módosítás.
- [x] Nem történt solver IO contract módosítás.
- [x] Nem történt külső source vendorolás.
- [x] Nem készült külső benchmark backend adapter.

## Verification and report

- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md` lefutott vagy környezeti blocker dokumentálva.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Eltérések, hiányzó external source-ok és blocker-ek explicit módon dokumentálva vannak.
