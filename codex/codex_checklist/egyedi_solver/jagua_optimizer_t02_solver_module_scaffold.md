# JG-02 Checklist — jagua_optimizer_t02_solver_module_scaffold

Pipálható DoD lista a canvas alapján:

- `canvases/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`

Bizonyítékforrás:

- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.verify.log`
- `docs/egyedi_solver/jagua_optimizer_source_audit.md`

## Szabályfájlok és tervforrások

- [x] `AGENTS.md` beolvasva.
- [x] `docs/codex/overview.md` beolvasva.
- [x] `docs/codex/yaml_schema.md` beolvasva.
- [x] `docs/codex/report_standard.md` beolvasva.
- [x] `docs/qa/testing_guidelines.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md` beolvasva.
- [x] `canvases/egyedi_solver/jagua_optimizer_task_index.md` beolvasva.
- [x] `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md` beolvasva.
- [x] `docs/egyedi_solver/jagua_optimizer_source_audit.md` beolvasva.

## Task azonosítás

- [x] JG-02 pontosan megtalálva a task bontásban.
- [x] JG-02 pontosan megtalálva a progress checklistben.
- [x] JG-01 dependency státusza ellenőrizve: PASS.
- [x] `docs/egyedi_solver/jagua_optimizer_source_audit.md` tartalmazza: `JG-02_STATUS: READY`.
- [x] Goal YAML parse OK és `steps` root séma érvényes (7 step, `YAML_OK`).
- [x] Nincs sandbox-specifikus abszolút path a goal YAML-ben.

## Baseline refaktor előtt

- [x] A jelenlegi `rust/vrs_solver/src/main.rs` viselkedése baseline-ként dokumentálva.
- [x] Baseline tartalmazza a DTO-kat és IO contract mezőket (report 4.1 szekció, type table).
- [x] Baseline tartalmazza a sheet expand sorrendet és `sheet_index` szemantikát.
- [x] Baseline tartalmazza az instance expand és rendezési szabályt (`instance_id.cmp`).
- [x] Baseline tartalmazza az allowed rotations policyt (csak 0/90/180/270).
- [x] Baseline tartalmazza a row/cursor placement mechanikát (`SheetCursor`, `try_place_on_sheet`).
- [x] Baseline tartalmazza a hole-aware sheet boundary checket (`rect_inside_sheet_shape`).
- [x] Refaktor előtti `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS (2.49s).
- [x] Refaktor előtti smoke/run output dokumentálva (baseline JSON a reportban).

## Moduláris refaktor

- [x] `rust/vrs_solver/src/io.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/geometry.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/sheet.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/item.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/adapter.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` létrejött/frissült.
- [x] `rust/vrs_solver/src/main.rs` CLI/orchestration szerepre szűkült (49 sor).
- [x] Refaktor csak a JG-02 YAML outputs listában engedélyezett implementációs fájlokat érintette.
- [x] Nem történt dependency módosítás (`Cargo.toml` érintetlen).
- [x] Nem lett új optimizer algoritmus implementálva.
- [x] Nem lett JG-03 hole gate implementálva.
- [x] Nem lett JG-04 magasabb szintű JaguaAdapter implementálva.

## Viselkedésmegőrzés

- [x] Az input contract nem változott kompatibilitást törően.
- [x] Az output contract nem változott kompatibilitást törően.
- [x] Smoke inputokon a normalizált JSON output szemantikailag változatlan (BYTE_IDENTICAL).
- [x] `placements` egyeznek (BYTE_IDENTICAL diff bizonyítja).
- [x] `unplaced` egyeznek (BYTE_IDENTICAL diff bizonyítja).
- [x] `metrics` kulcsmezők egyeznek (BYTE_IDENTICAL diff bizonyítja).
- [x] `sheet_index` szemantika változatlan.
- [x] Instance-id képzés és rendezés stabil.
- [x] Hole-aware sheet boundary check nem gyengült (`rect_inside_sheet_shape` 1:1 mozgatva).
- [x] Minden viselkedésváltozás explicit NO/YES táblában dokumentált (report 6. szekció).

## Build, test, verify

- [x] Refaktor utáni `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS (12.91s).
- [x] Refaktor utáni `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS (2/2 ok, item::tests).
- [x] `python3 scripts/validate_nesting_solution.py --run-dir <run_dir>` PASS.
- [x] Determinism hash smoke PASS (`./scripts/verify.sh` determinism szekció: 10/10).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` lefutott.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.verify.log`.

## Report és progress checklist

- [x] Report tartalmaz baseline összefoglalót (4. szekció).
- [x] Report tartalmaz module split összefoglalót (5. szekció).
- [x] Report tartalmaz diff összefoglalót (AUTO_VERIFY git diff --stat).
- [x] Report tartalmaz output-equivalence bizonyítékot (7.3 szekció, BYTE_IDENTICAL).
- [x] Report tartalmaz build/test/verify bizonyítékot (7. szekció).
- [x] Report tartalmaz explicit blocker/deviation szakaszt (DISCOVERED_MISMATCH, validation.rs).
- [x] Globális progress checklist JG-02 szakasza frissült bizonyíték alapján.
- [x] Gate 0 / JG-03 readiness döntés dokumentálva (JG-03_STATUS: READY a reportban).

## Záró mezők

- [x] Reportban szerepel a végső státusz: PASS.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van (DISCOVERED_MISMATCH, validation.rs).
- [x] Következő task indíthatósága egyértelműen jelölve van: **JG-03 READY**.

## Package generation note

- [x] Véglegesítve: 2026-05-23, lokális repo-ban futtatva.
