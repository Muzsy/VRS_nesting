# T01 Checklist — lv8_density_t01_phase0_fixture_inventory

Pipálható DoD lista a canvas
[lv8_density_t01_phase0_fixture_inventory.md](../../../canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](../../reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md)).

## Repo szabályok és T00 outputok

- [x] `AGENTS.md` beolvasva.
- [x] `docs/codex/overview.md` beolvasva.
- [x] `docs/codex/yaml_schema.md` beolvasva (root `steps`, `name`/`description`/`outputs`,
      opcionális `inputs`).
- [x] `docs/codex/report_standard.md` beolvasva (Report Standard v2).
- [x] `docs/qa/testing_guidelines.md` beolvasva.
- [x] `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
      beolvasva (v2.2 plan).
- [x] T00 outputok jelen és kompatibilisek:
      [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md),
      [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md).
- [x] T01 canvas és YAML beolvasva.

## Inventory artefaktok

- [x] [tmp/lv8_density_fixture_inventory.md](../../../tmp/lv8_density_fixture_inventory.md) létrejött.
- [x] [tmp/lv8_density_fixture_inventory.json](../../../tmp/lv8_density_fixture_inventory.json)
      létrejött és valid JSON.
- [x] Az inventory JSON tartalmazza a három családot:
      `lv8`, `web_platform_contract_freeze`, `small_synthetic_sa_guard`.
- [x] Tartalmazza a kötelező fixture id-ket: `lv8_276_full`,
      `lv8_179_single_sheet`, `f2_4_sa_quality_fixture_v2`.
- [x] Minden fixture státusza az engedélyezett halmazból
      (`PRESENT`/`MISSING`/`RESTORED`/`REGENERATABLE`/`BLOCKED`/`NOT_APPLICABLE`).

## Fixture státusz dokumentálása

- [x] LV8 276 fixture státusza dokumentált: PRESENT, 122855 byte,
      JSON parse OK; útvonal `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`.
- [x] LV8 179 fixture státusza dokumentált, nem feltételezett: PRESENT,
      122854 byte, JSON parse OK; útvonal
      `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`;
      forrás-riport: `codex/reports/nesting_engine/lv8_singlesheet_etalon_179_20260514.md`.
- [x] Kis-synthetic / SA guard fixture státusza dokumentált: PRESENT,
      583 byte, JSON parse OK; útvonal
      `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`.
- [x] web_platform / contract_freeze fixture-jelöltek konkrét fájlokra
      bontva: `samples/dxf_demo/stock_rect_1000x2000.dxf` +
      `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` +
      driver `scripts/smoke_svg_export.py`. Nincs `BLOCKED`-jelölés.

## LV8 179 helyreállítási döntés

- [x] LV8 179 jelenleg PRESENT, ezért **nem** hoztunk létre új fixture
      fájlt (`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`
      érintetlen, csak audit).
- [x] Determinisztikus helyreállítási recept dokumentálva:
      [tmp/lv8_density_fixture_restore_notes.md](../../../tmp/lv8_density_fixture_restore_notes.md).

## Tilalmak betartása

- [x] Nincs Rust engine kódmódosítás (production diff guard üres halmaz a
      `*.rs/*.py/*.ts/*.tsx` szűrőre).
- [x] Nincs Python production kódmódosítás.
- [x] Nincs TypeScript / frontend kódmódosítás.
- [x] Nincs quality profile módosítás (`nesting_quality_profiles.py` érintetlen).
- [x] Nincs hosszú benchmark futtatva.
- [x] Nincs polygon-aware validátor implementálva.
- [x] Nincs placeholder LV8 179 fixture (a meglévő fixture érintetlen,
      a recept külön notes-ban).
- [x] Nincs kitalált contract_freeze fixture útvonal; minden anchor
      `ls`-szel és `find`-dal igazolva.

## Verifikáció

- [x] T01 sanity check zöld (Python assertion blokk a runnerből):
      `T01 inventory sanity PASS`.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
      lefutott. Eredmény: **PASS** (`check.sh` exit 0, 175s). 302 pytest pass,
      mypy clean, Sparrow + DXF + multisheet + `vrs_solver` determinisztika +
      timeout/perf guard zöld. Log:
      `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`.
- [x] Report DoD → Evidence Matrix kitöltve (lásd a report 5) szekcióját);
      mind a 12 DoD pont PASS.
