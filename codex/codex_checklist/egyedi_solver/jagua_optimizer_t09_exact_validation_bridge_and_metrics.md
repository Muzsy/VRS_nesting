# Checklist — JG-09 jagua_optimizer_t09_exact_validation_bridge_and_metrics

## Feladat

Rust solver output és Python exact validator/report metrikák zárása. Invalid layout nem lehet successful; valid layout csak exact validator PASS után fogadható el.

## Dependency

- [x] JG-08 report létezik.
- [x] JG-08 report első sora `PASS`.
- [x] JG-08 report tartalmazza: `JG-09_STATUS: READY`.
- [x] JG-08 construction placer artifactok léteznek: `optimizer/candidates.rs`, `optimizer/initializer.rs`, `scripts/smoke_jagua_initial_construction.py`.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Exact validation bridge

- [x] Runner audit dokumentálva: hol fut `validate_multi_sheet_output()`.
- [x] Valid `ok`/`partial` output exact validator PASS után sikeres.
- [x] Invalid `ok`/`partial` output exact validator FAIL esetén runner szinten hibás.
- [x] Overlap invalid output elutasítva.
- [x] Out-of-sheet vagy invalid sheet-index output elutasítva.
- [x] Duplicate/coverage mismatch továbbra is elutasított.
- [x] Unsupported Phase 1 hole-os input nem valid success, explicit unsupported/skip branch.
- [x] Invalid layout soha nem kap successful JG-09 státuszt.

## Metrics / report

- [x] `runner_meta.json` vagy report tartalmaz validation status mezőt.
- [x] Invalid esetben validation error mentődik vagy logolódik.
- [x] Report/metrikák tartalmazzák: runtime/duration.
- [x] Report/metrikák tartalmazzák: placed_count.
- [x] Report/metrikák tartalmazzák: unplaced_count.
- [x] Report/metrikák tartalmazzák: used_sheets vagy sheet_count_used.
- [x] Report/metrikák tartalmazzák: utilization.
- [x] Utilization definíció dokumentálva.
- [x] Partial success fogalma elkülönül a valid successtől.

## Rust / runner contract

- [x] `contract_version`, `status`, `placements`, `unplaced`, `metrics` v1 mezők nem sérültek.
- [x] Rust Metrics bővítés csak backward-compatible módon történt, ha történt.
- [x] Ha validation status csak Python runner meta szinten van, ez dokumentálva van.
- [x] jagua-rs típus nem szivárog publikus VRS output/runner contractba.
- [x] Silent geometry loss nincs: identity, quantity, transform, validation adat megmarad.

## Smoke / tests

- [x] `scripts/smoke_jagua_exact_validation_bridge.py` létrejött.
- [x] Valid fixture runneren keresztül PASS.
- [x] Overlap invalid fixture FAIL.
- [x] Out-of-sheet vagy invalid sheet-index fixture FAIL.
- [x] Unsupported fixture explicit unsupported/skip.
- [x] `python3 scripts/smoke_jagua_initial_construction.py` regression PASS.
- [x] `python3 scripts/smoke_jagua_exact_validation_bridge.py` PASS.
- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz valós kód auditot.
- [x] Report tartalmaz validation bridge design döntést.
- [x] Report tartalmaz metrics example-t.
- [x] Report tartalmaz valid és invalid fixture kimenet-részleteket.
- [x] Globális progress checklist JG-09 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-10_STATUS: READY` vagy `NOT_READY`.
