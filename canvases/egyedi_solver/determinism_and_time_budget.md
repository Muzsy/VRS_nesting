# Determinizmus + idokeret enforcement

## 🎯 Funkcio
Ez a P1 task a determinisztikus futas es idokeret-kikenszerites megerositesenek scaffoldja: a hash-stabilitas smoke mar letezik, de formalizalt idokeret-eset es regresszio coverage tovabb kell. P1, mert P0-ban a minimum gate megvan, de SLA-szintu stabilitasra tovabbi ellenorzes kell.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - Seed/time_limit policy es elvart viselkedes formalizalasa.
  - output hash stabilitas + timeout ag regresszio-terv.
  - Runner meta kotelezo mezok ellenorzesi listaja.
- Nincs benne:
  - Solver heurisztika tuning.
  - Uj CI workflow bevezetes.

### Erintett modulok/fajlok
- `vrs_nesting/runner/vrs_solver_runner.py`
- `rust/vrs_solver/src/main.rs`
- `scripts/check.sh`
- `.github/workflows/nesttool-smoketest.yml`
- `codex/reports/egyedi_solver/determinism_and_time_budget.md`
- `codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md`

### DoD
- [ ] A canvas egyertelmuen rogzitett seed/time_limit es hash-stabilitas celokat tartalmaz.
- [ ] A report vaz tartalmaz timeout viselkedes es determinism regresszio teszttervet.
- [ ] A checklist tartalmazza a P0 hash-smoke kompatibilitas ellenorzeset.
- [ ] A scaffold report/checklist kitoltve.

### Kockazat + mitigacio + rollback
- Kockazat: idozitesfuggo drift nem-determinisztikus outputot okozhat.
- Mitigacio: fix seed/time_limit, stable sort/tie-break policy, hash compare smoke.
- Rollback: uj ellenorzesek feature-flaggel vagy izolalt script szakasszal kivehetok.

### Regresszio-orseg (P0 nem romolhat)
- Kotelezo ellenorzes: `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_and_time_budget.md`.
- P0 referencia: `canvases/egyedi_solver/determinism_hash_stability_smoke.md`, `scripts/check.sh`.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_and_time_budget.md`
- Relevans letezo szkriptek:
  - `./scripts/check.sh`
  - `python3 -m vrs_nesting.runner.vrs_solver_runner --help`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `canvases/egyedi_solver/determinism_hash_stability_smoke.md`
- `canvases/egyedi_solver/table_solver_mvp_multisheet.md`
