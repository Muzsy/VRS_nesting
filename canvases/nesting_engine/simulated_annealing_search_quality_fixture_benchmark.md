# simulated_annealing_search_quality_fixture_benchmark

## 🎯 Funkció

**Cél:** Bizonyítani (teszttel + reporttal), hogy az F2-4 SA keresés **ténylegesen javíthat** a baseline greedy eredményen legalább egy fix, repo-ban tárolt fixture esetén.

Konkrét elvárás:
- baseline (`--search none` vagy flag nélkül) → `sheets_used = 2`
- SA (`--search sa` fix seed-del) → `sheets_used = 1`
- mindez determinisztikusan reprodukálható és gate-ből bizonyított

**Nem cél:**
- SA paramétertuning “általános” optimalizációra
- caching/incremental eval
- több fixture nagy mintával (most elég 1 kis, stabil)

## 🧠 Fejlesztési részletek

### Új fixture (CLI-hez, evidenciához)
Hozz létre egy új v2 input fixture-t:

- `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`

Tartalom elv (téglalapok poligonként):
- Sheet: 100×100 mm, kerf=0, margin=0, spacing=0
- Part A: 90×40 mm, allowed_rotations_deg = [0, 90]
- Part B: 40×90 mm, allowed_rotations_deg = [0]
- A és B outer polygon: `[[0,0],[w,0],[w,h],[0,h]]`, holes üres.
- A baseline (ByArea + rot lista sorrend) az A-t 90×40-ként teszi le → B nem fér a maradék magasságba → új sheet.
- SA képes a rotáció-prioritást megfordítani (A: [90,0]) → A 40×90-ként kerül le → B elfér ugyanarra a sheetre → sheets_used=1.

### Bizonyító Rust unit teszt (gate-be kötve via `sa_`)
Adj hozzá egy új `sa_` prefixű tesztet a `rust/nesting_engine/src/search/sa.rs` `#[cfg(test)]` moduljába:

- `sa_quality_fixture_improves_sheets_used`

A teszt:
1) baseline futtatás `greedy_multi_sheet(..., PartOrderPolicy::ByArea)` → assert `sheets_used == 2`
2) SA futtatás `run_sa_search_over_specs(...)` fix configgal → assert `sheets_used == 1` (vagy `< baseline`)
3) állítsd `NESTING_ENGINE_STOP_MODE=work_budget`, hogy timeout-bound drift ne jöjjön be

### Report evidence (kötelező “SA javít” claimhez)
A reportban legyen két CLI futás (kisméretű, gyors):
- baseline:
  - `nest < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` (vagy `--search none`)
- SA:
  - `nest --search sa --sa-seed 2026 --sa-iters 128 --sa-eval-budget-sec 2 < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`

A reportban rögzítsd:
- baseline `sheets_used`
- SA `sheets_used`
- mindkét output `meta.determinism_hash` (csak reprodukálhatósági kontroll)

## 🧪 Tesztállapot

### DoD
- [ ] Új fixture file: `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`
- [ ] Új Rust unit teszt: `sa_quality_fixture_improves_sheets_used` (sa_ prefix) PASS
- [ ] `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_` PASS (verify logban is látszik)
- [ ] Report Standard v2 + AUTO_VERIFY + `.verify.log` mentve
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_quality_fixture_benchmark.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- F2-4 canvas: `canvases/nesting_engine/simulated_annealing_search.md`
- SA integráció: `canvases/nesting_engine/simulated_annealing_search_cli_and_evaluator_integration.md`
- Kód: `rust/nesting_engine/src/search/sa.rs`
- Gate: `scripts/check.sh` (már futtat `sa_` teszteket)
