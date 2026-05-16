# LV8 Density T01 — Phase 0 fixture inventory és LV8 179 rendezés

## 🎯 Funkció

A feladat célja a Phase 0 shadow runhoz szükséges fixture-készlet valós repo-alapú feltérképezése és dokumentálása. A végleges LV8 packing density terv szerint a Phase 0 shadow run három fixture-családon fut:

1. LV8 család:
   - LV8 276 full 2-sheet benchmark.
   - LV8 179 single-sheet subset.
2. web_platform / contract_freeze család.
3. kis-synthetic / SA guard család.

A T01 nem algoritmikus fejlesztés. Ez egy mérési előfeltétel: a későbbi T02–T06 Phase 0 feladatok csak akkor delegálhatók biztonságosan, ha minden szükséges fixture státusza dokumentált: `PRESENT`, `MISSING`, `RESTORED`, `REGENERATABLE`, vagy `STOP`.

## Forrás és döntések

A T01 a végleges `codex/reports/nesting_engine/development_plan_packing_density_20260515.md` v2.2 tervre és a T00 által létrehozott `canvases/nesting_engine/lv8_density_task_index.md` indexre épül. A terv tartalmát nem szabad módosítani.

A T01-be beépített végleges döntések:

- A Phase 0 shadow run kötelezően 3 fixture-családot vizsgál.
- A kis-synthetic / SA guard elsődleges fixture-je: `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`.
- A LV8 276 fixture elsődleges útvonala: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`.
- A LV8 179 fixture tervezett útvonala: `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`, de a friss snapshotban ez nem garantáltan létezik. T01 feladata ezt ellenőrizni és nem kitalálni.
- A web_platform / contract_freeze fixture-listát nem szabad kézzel feltételezni; a repo aktuális canvas/report/fixture állapotából kell feltárni.

## Valós repo-kiindulópontok a friss snapshot alapján

A T01 előtt a T00 már létrehozta:

- `canvases/nesting_engine/lv8_density_task_index.md`
- `codex/prompts/nesting_engine/lv8_density_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

A T01-ben kötelezően ellenőrizendő fájlok:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
- `canvases/nesting_engine/lv8_density_task_index.md`
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`
- `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`
- `codex/reports/nesting_engine/lv8_singlesheet_etalon_179_20260514.md`
- `canvases/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `canvases/web_platform_phase0_contract_freeze.md`
- `codex/reports/web_platform_phase0_contract_freeze.md`

## T01 scope

### T01 feladata

1. Fixture inventory készítése a három Phase 0 fixture-családra.
2. LV8 276 fixture meglétének és minimális JSON-olvasási állapotának ellenőrzése.
3. LV8 179 fixture státuszának tisztázása:
   - ha létezik: `PRESENT`;
   - ha nem létezik, de a repo alapján reprodukálható: `REGENERATABLE`, pontos parancs / input / output útvonallal;
   - ha nem reprodukálható: `MISSING`, T02–T06 számára STOP/blocked jelzéssel.
4. Kis-synthetic / SA guard fixture meglétének és minimális JSON-olvasási állapotának ellenőrzése.
5. web_platform / contract_freeze családhoz konkrét fixture-jelöltek listázása a repo aktuális fájljaiból.
6. `tmp/lv8_density_fixture_inventory.md` és `tmp/lv8_density_fixture_inventory.json` létrehozása.
7. T01 checklist és report létrehozása.

### T01 nem célja

- Nem módosít Rust engine kódot.
- Nem módosít Python production kódot.
- Nem módosít quality profile-t.
- Nem futtat hosszú nesting benchmarkot.
- Nem implementál Phase 0 shadow run logikát.
- Nem ír polygon-aware validátort.
- Nem hoz létre placeholder fixture-t.
- Nem talál ki nem létező contract_freeze fixture útvonalat.

## Létrehozandó / módosítható fájlok

A T01 futása legfeljebb ezeket a fájlokat hozhatja létre vagy módosíthatja:

- `tmp/lv8_density_fixture_inventory.md`
- `tmp/lv8_density_fixture_inventory.json`
- `codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`

Opcionális, csak akkor, ha a repo alapján bizonyíthatóan reprodukálható és a reportban indokolt:

- `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`
- `tmp/lv8_density_fixture_restore_notes.md`

Tilos más production vagy config fájl módosítása. Ha bármilyen további output szükségesnek tűnik, a taskot `FAIL`/`STOP` státusszal kell zárni, és külön T01b canvas szükséges.

## Kötelező inventory státuszok

Minden fixture-jelölthöz pontos státuszt kell írni:

- `PRESENT` — létezik, olvasható, minimális JSON / fájl check zöld.
- `MISSING` — a terv vagy korábbi report hivatkozik rá, de ebben a snapshotban nincs meg.
- `RESTORED` — a task létrehozta reprodukálható forrásból, reportált parancs alapján.
- `REGENERATABLE` — nincs létrehozva, de pontos generálási út ismert és dokumentált.
- `BLOCKED` — nem lehet jogszerűen helyreállítani meglévő repo-forrásból.
- `NOT_APPLICABLE` — adott családnál nincs JSON fixture, csak dokumentált candidate path / canvas kapcsolat.

## Kötelező inventory mezők JSON-ban

A `tmp/lv8_density_fixture_inventory.json` legalább ezt a struktúrát tartalmazza:

```json
{
  "task_slug": "lv8_density_t01_phase0_fixture_inventory",
  "generated_at": "YYYY-MM-DD",
  "source_plan": "codex/reports/nesting_engine/development_plan_packing_density_20260515.md",
  "families": [
    {
      "family_id": "lv8",
      "fixtures": [
        {
          "id": "lv8_276_full",
          "path": "tests/fixtures/nesting_engine/ne2_input_lv8jav.json",
          "status": "PRESENT",
          "file_type": "json",
          "exists": true,
          "json_parse_ok": true,
          "notes": "..."
        }
      ]
    }
  ],
  "blocking_issues": [],
  "recommended_next_step": "..."
}
```

A `tmp/lv8_density_fixture_inventory.md` emberileg olvasható összefoglaló legyen, azonos adatokkal.

## Minimális ellenőrzések

A T01 nem futtat hosszú benchmarkot. Kötelező minimális ellenőrzések:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in [
    'tests/fixtures/nesting_engine/ne2_input_lv8jav.json',
    'poc/nesting_engine/f2_4_sa_quality_fixture_v2.json',
]:
    path = Path(p)
    print(p, 'exists=', path.exists())
    if path.exists():
        json.loads(path.read_text())
        print(p, 'json_parse_ok=True')
PY
```

Fixture keresésekhez legalább:

```bash
find . -path '*lv8_sheet1_179.json' -o -path '*lv8_singlesheet*'
find . \( -iname '*contract*freeze*' -o -path '*contract_freeze*' -o -iname '*freeze*' \)
find tests poc samples tmp -maxdepth 5 -type f \( -name '*.json' -o -name '*.dxf' \) 2>/dev/null
```

## Rollback terv

A T01 csak dokumentációt és `tmp/` inventory artefaktumokat hoz létre. Rollback:

```bash
rm -f tmp/lv8_density_fixture_inventory.md
rm -f tmp/lv8_density_fixture_inventory.json
rm -f tmp/lv8_density_fixture_restore_notes.md
rm -f codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
rm -f codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
rm -f codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log
```

Ha `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` létrejött, csak akkor törölhető, ha a report szerint `RESTORED` státuszú és nem volt korábban létező fájl.

## Definition of Done

- [ ] Repo szabályfájlok és T00 index/master runner elolvasva.
- [ ] `tmp/lv8_density_fixture_inventory.md` létrejött.
- [ ] `tmp/lv8_density_fixture_inventory.json` létrejött és valid JSON.
- [ ] LV8 276 fixture státusza dokumentált.
- [ ] LV8 179 fixture státusza dokumentált, nem feltételezett.
- [ ] Kis-synthetic / SA guard fixture státusza dokumentált.
- [ ] web_platform / contract_freeze fixture-jelöltek konkrét fájlokra bontva vagy BLOCKED indokkal jelölve.
- [ ] Nincs placeholder fixture.
- [ ] Nincs Rust / Python / TypeScript production kódmódosítás.
- [ ] T01 checklist létrejött és ki van töltve.
- [ ] T01 report a Report Standard v2 szerint elkészült, DoD → Evidence Matrix-szal.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md` lefutott, vagy ha környezeti okból nem futott, a report FAIL/PASS_WITH_NOTES módon dokumentálja.

## Stop feltételek

A taskot `FAIL` vagy `BLOCKED` státusszal kell zárni, ha:

- A LV8 276 fixture nem létezik vagy nem olvasható JSON-ként.
- A kis-synthetic SA guard fixture nem létezik vagy nem olvasható JSON-ként.
- A contract_freeze családhoz semmilyen repo-beli anchor nem található.
- A LV8 179 fixture hiányzik, és semmilyen reprodukálási út nem dokumentálható. Ez nem teljes T01 failure, de T02–T06 számára blocking issue.
- A feladat csak placeholder fixture létrehozásával lenne lezárható.
