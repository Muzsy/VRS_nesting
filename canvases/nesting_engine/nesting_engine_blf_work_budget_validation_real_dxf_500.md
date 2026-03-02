# canvases/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500.md

## 🎯 Funkció

Validálni, hogy a frissen bevezetett `work_budget` stop mód megszünteti a BLF time-limit határ közeli
nondeterminizmust a valós DXF-ből származtatott 500-as fixture-en:

- input: `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`
- összevetés:
  - BLF (wall_clock default)
  - BLF (work_budget mód)

Ezt mérhetően, reportban dokumentálva kell lezárni.

## 🧠 Fejlesztési részletek

### 1) Benchmark script kiegészítés (CLI -> env)
Érintett fájl:
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`

Adj hozzá opcionális CLI argumentumokat (backward compatible):
- `--stop-mode wall_clock|work_budget` (default: nincs beállítás, tehát a binary defaultja)
- `--work-units-per-sec <u64>` (csak work_budget esetén)
- `--hard-timeout-grace-sec <u64>` (csak work_budget esetén)

A script futtatáskor állítsa be a subprocess env-be (ha meg vannak adva):
- `NESTING_ENGINE_STOP_MODE`
- `NESTING_ENGINE_WORK_UNITS_PER_SEC`
- `NESTING_ENGINE_HARD_TIMEOUT_GRACE_SEC`

A bench output “meta” részébe írd bele, hogy milyen stop-mode env-ekkel futott (ha futott).

### 2) Mérés (csak BLF, 500-as valós DXF fixture)
Release build után futtasd:

1) Wall-clock baseline (nincs stop-mode args):
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer blf --runs 5 --input poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`

2) Work-budget:
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer blf --runs 5 --stop-mode work_budget --work-units-per-sec 50000 --hard-timeout-grace-sec 60 --input poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`

Elvárás:
- work_budget esetén `determinism_stable=true`
- és a placed/sheets eredmény runok között azonos.

### 3) Report + checklist
Új reportot csinálunk (ne keverjük a korábbi real_dxf quality reportba):
- `codex/reports/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500.md`

Tartalom:
- parancsok (pontos)
- 2 soros táblázat: BLF wall_clock vs BLF work_budget (median runtime, placed_count, sheets_used, determinism_stable, timeout_bound_present)
- rövid konklúzió: “a drift oka wall-clock cutoff volt; work_budget módban determinisztikus”.

## 🧪 Tesztállapot

### DoD
- [x] `bench_nesting_engine_f2_3_large_fixture.py` támogatja a stop-mode argsokat és az env-eket átadja a binnek
- [x] 500/BLF work_budget módban 5 run: determinism_stable = true
- [x] Report elkészült, AUTO_VERIFY PASS:
  - `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_blf_work_budget_validation_real_dxf_500.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `rust/nesting_engine/src/multi_bin/greedy.rs` (StopPolicy::from_env + env varok)
- `rust/nesting_engine/src/placement/blf.rs` (stop.consume kapuk)
- `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`

## Felderítési snapshot (2026-03-02)

- A `greedy.rs` jelenleg az alábbi env-eket olvassa a stop policy-hoz:
  - `NESTING_ENGINE_STOP_MODE`
  - `NESTING_ENGINE_WORK_UNITS_PER_SEC`
  - `NESTING_ENGINE_HARD_TIMEOUT_GRACE_SEC`
- A benchmark script eddig nem tudta ezeket CLI-ről vezérelni; csak az NFP stats env-et állította.
- Hozzáadandó CLI opciók:
  - `--stop-mode wall_clock|work_budget`
  - `--work-units-per-sec <u64>`
  - `--hard-timeout-grace-sec <u64>`
- Env továbbítási terv:
  - ha `--stop-mode` nincs: nem állítunk stop-mode env-et (binary default marad),
  - ha `--stop-mode wall_clock`: csak `NESTING_ENGINE_STOP_MODE=wall_clock`,
  - ha `--stop-mode work_budget`: mindhárom env beállítva, hiányzó számmezők script-defaultdal.
