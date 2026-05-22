# Checklist — JG-03 jagua_optimizer_t03_outer_only_contract_and_hole_gate

## Feladat

Phase 1 outer-only contract és hole gate megvalósítása a JG-02 utáni `vrs_solver` modulstruktúrában.

## Dependency

- [x] JG-02 report első sora `PASS`.
- [x] JG-02 report tartalmazza: `JG-03_STATUS = READY`.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Contract / policy

- [x] Phase 1 capability policy dokumentálva: rectangular multi-sheet, item holes nélkül.
- [x] `docs/solver_io_contract.md` frissítve a JG-03 policyval.
- [x] `solver_profile` vagy ezzel egyenértékű profile boundary dokumentálva.
- [x] `capabilities` és/vagy `unsupported_reason` kezelés dokumentálva.
- [x] Végleges unsupported policy kiválasztva: output-alapú unsupported vagy controlled non-zero error.
- [x] Stabil unsupported reason string dokumentálva.

## Rust gate

- [x] Part hole mezők (`holes_points`, `prepared_holes_points`) explicit észlelve a Rust boundaryn.
- [x] `outer_points` / `prepared_outer_points` kezelés nem okoz silent geometry losst.
- [x] Hole-os part Phase 1 profil alatt deterministic unsupported/error státuszt ad.
- [x] Gate placement előtt fut.
- [x] Rectangle-only inputokon a JG-02 baseline behavior nem változik.
- [x] Stock hole/remnant capability nincs véletlenül Phase 1 jagua profilban engedélyezve.
- [x] Default legacy `scripts/check.sh` smoke nem törik.

## Python runner / validator

- [x] `vrs_nesting/runner/vrs_solver_runner.py` státuszkezelése ellenőrizve/frissítve.
- [x] `vrs_nesting/nesting/instances.py` layout-only exact validation szabálya nem lazult el.
- [x] Unsupported non-layout állapot nem megy át valid layout PASS-ként.
- [x] Runner meta vagy log tartalmazza az unsupported okot.

## Smoke / tests

- [x] `scripts/smoke_jagua_optimizer_outer_only_contract.py` létrejött.
- [x] Positive outer-only fixture fut és exact validation PASS.
- [x] Negative hole-os part fixture deterministic unsupported/error.
- [x] Negative fixture reason string ellenőrizve.
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `python3 scripts/smoke_jagua_optimizer_outer_only_contract.py` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` PASS.
- [x] Verify log mentve.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz contract döntést.
- [x] Report tartalmaz Rust/Python változás összefoglalót.
- [x] Report tartalmaz positive/negative smoke evidence-t.
- [x] Report tartalmaz exact validation evidence-t.
- [x] Report tartalmaz legacy regression evidence-t.
- [x] Globális progress checklist JG-03 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-04_STATUS: READY` vagy `NOT_READY`.
