# Checklist — JG-04 jagua_optimizer_t04_jagua_adapter_contract_poc

## Feladat

Vékony JaguaAdapter contract és proof-of-contact létrehozása a JG-02/JG-03 utáni `vrs_solver` modulstruktúrában.

## Dependency

- [x] JG-02 report első sora `PASS`.
- [x] JG-03 report első sora `PASS`.
- [x] JG-03 report tartalmazza: `JG-04_STATUS: READY`.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.
- [x] `DISCOVERED_MISMATCH` kezelve: régi JG-04 rectangular optimizer név vs aktuális backend adapter task.

## Adapter contract

- [x] Adapter trait/contract leírva saját publikus VRS modellben.
- [x] Jagua-specifikus típusok nem szivárognak át az optimizer publikus modelljébe.
- [x] Adapter hibakezelés explicit: `unsupported`, `conversion_error`, `backend_error`.
- [x] A meglévő `solve(input)` orchestration és JG-03 hole gate nem sérült.
- [x] A POC nem köt be még teljes optimizer-loopot.

## Geometry conversion / jagua PoC

- [x] VRS polygon/rect → jagua geometry konverzió első verziója elkészült vagy spike-olva.
- [x] f64 → f32 konverziós pont dokumentált.
- [x] Unit/coordinate kockázat dokumentált.
- [x] Egyszerű item-item collision smoke valid/nem átfedő esetet felismer.
- [x] Egyszerű item-item collision smoke invalid/overlap esetet felismer.
- [x] Item-sheet / boundary jellegű smoke lefut, ha a jagua API támogatja.
- [x] Ha valamelyik API-rész nem támogatott, explicit `unsupported` / `REQUIRES_DECISION` bizonyíték van.

## Smoke / tests

- [x] `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs` létrejött.
- [x] `scripts/smoke_jagua_adapter_contract.py` létrejött.
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `python3 scripts/smoke_jagua_adapter_contract.py` PASS.
- [x] `python3 scripts/smoke_jagua_optimizer_outer_only_contract.py` PASS, vagy explicit indokkal dokumentált.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` PASS.
- [x] Verify log mentve.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz code-boundary auditot.
- [x] Report tartalmaz adapter API-megfigyeléseket és ismert korlátokat.
- [x] Report tartalmaz smoke evidence-t.
- [x] Report tartalmaz f32/f64 konverziós kockázatot.
- [x] Globális progress checklist JG-04 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-05_STATUS: READY` vagy `NOT_READY`.
