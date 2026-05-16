# LV8 Density T01 — Phase 0 fixture inventory és LV8 179 rendezés
TASK_SLUG: lv8_density_t01_phase0_fixture_inventory

## Szerep

Senior repo-audit és benchmark-preflight agent vagy. A feladatod nem algoritmusfejlesztés, hanem a Phase 0 shadow run fixture-alapjának bizonyítása a valós repó alapján.

## Cél

Hozd létre:

1. `tmp/lv8_density_fixture_inventory.md`
2. `tmp/lv8_density_fixture_inventory.json`
3. `codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
4. `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`

Opcionális, csak bizonyított szükség esetén:

- `tmp/lv8_density_fixture_restore_notes.md`
- `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`

Ne implementálj engine funkciót. Ne módosíts quality profile-t. Ne hozz létre placeholder fixture-t.

## Kötelező olvasnivaló prioritási sorrendben

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
7. `canvases/nesting_engine/lv8_density_task_index.md`
8. `codex/prompts/nesting_engine/lv8_density_master_runner.md`
9. `canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
10. `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml`

Ha bármelyik kötelező szabályfájl hiányzik, állj meg, és a reportban FAIL-ként rögzítsd.

## Engedélyezett módosítások

Csak ezek a fájlok hozhatók létre vagy módosíthatók:

- `tmp/lv8_density_fixture_inventory.md`
- `tmp/lv8_density_fixture_inventory.json`
- `tmp/lv8_density_fixture_restore_notes.md`
- `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`
- `codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`

## Szigorú tiltások

- Tilos Rust engine kódot módosítani.
- Tilos Python production kódot módosítani.
- Tilos TypeScript / frontend kódot módosítani.
- Tilos quality profile-t módosítani.
- Tilos hosszú benchmarkot futtatni.
- Tilos polygon-aware validátort implementálni.
- Tilos placeholder LV8 179 fixture-t létrehozni.
- Tilos nem létező contract_freeze fixture útvonalat tényként kezelni.
- Tilos a végleges fejlesztési terv döntéseit megváltoztatni.

## Előfeltétel ellenőrzés

```bash
ls AGENTS.md || echo "STOP: AGENTS.md missing"
ls docs/codex/yaml_schema.md || echo "STOP: yaml schema missing"
ls docs/codex/report_standard.md || echo "STOP: report standard missing"
ls canvases/nesting_engine/lv8_density_task_index.md || echo "STOP: T00 task index missing"
ls codex/prompts/nesting_engine/lv8_density_master_runner.md || echo "STOP: master runner missing"
ls canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md || echo "STOP: T01 canvas missing"
ls codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml || echo "STOP: T01 YAML missing"
```

## Fixture keresési parancsok

### LV8 276 és kis-synthetic sanity

```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in [
    'tests/fixtures/nesting_engine/ne2_input_lv8jav.json',
    'poc/nesting_engine/f2_4_sa_quality_fixture_v2.json',
]:
    path = Path(p)
    print(f'{p}: exists={path.exists()}')
    if path.exists():
        json.loads(path.read_text())
        print(f'{p}: json_parse_ok=True size={path.stat().st_size}')
PY
```

### LV8 179 keresés

```bash
find . -path '*lv8_sheet1_179.json' -o -path '*lv8_singlesheet*' | sort
```

Ellenőrizd külön:

```bash
test -e tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json \
  && echo 'PRESENT tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json' \
  || echo 'MISSING tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json'
```

### contract_freeze anchorok

```bash
find . \( -iname '*contract*freeze*' -o -path '*contract_freeze*' -o -iname '*freeze*' \) | sort
```

Olvasd el legalább ezeket, ha léteznek:

```bash
sed -n '1,220p' canvases/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md 2>/dev/null || true
sed -n '1,220p' codex/reports/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md 2>/dev/null || true
sed -n '1,220p' canvases/web_platform_phase0_contract_freeze.md 2>/dev/null || true
sed -n '1,220p' codex/reports/web_platform_phase0_contract_freeze.md 2>/dev/null || true
```

### Fixture-készlet áttekintése

```bash
find tests poc samples tmp -maxdepth 5 -type f \( -name '*.json' -o -name '*.dxf' \) 2>/dev/null | sort > /tmp/lv8_density_fixture_findings.txt
sed -n '1,220p' /tmp/lv8_density_fixture_findings.txt
```

## Inventory JSON elkészítése

A `tmp/lv8_density_fixture_inventory.json` legalább ezt tartalmazza:

```json
{
  "task_slug": "lv8_density_t01_phase0_fixture_inventory",
  "generated_at": "YYYY-MM-DD",
  "source_plan": "codex/reports/nesting_engine/development_plan_packing_density_20260515.md",
  "families": [
    {
      "family_id": "lv8",
      "fixtures": []
    },
    {
      "family_id": "web_platform_contract_freeze",
      "fixtures": []
    },
    {
      "family_id": "small_synthetic_sa_guard",
      "fixtures": []
    }
  ],
  "blocking_issues": [],
  "recommended_next_step": "..."
}
```

Kötelező fixture id-k:

- `lv8_276_full`
- `lv8_179_single_sheet`
- `f2_4_sa_quality_fixture_v2`

Státuszok kizárólag:

- `PRESENT`
- `MISSING`
- `RESTORED`
- `REGENERATABLE`
- `BLOCKED`
- `NOT_APPLICABLE`

## Sanity check

A végén futtasd:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('tmp/lv8_density_fixture_inventory.json')
assert p.exists(), 'inventory json missing'
data = json.loads(p.read_text())
families = {f['family_id'] for f in data.get('families', [])}
for required in ['lv8', 'web_platform_contract_freeze', 'small_synthetic_sa_guard']:
    assert required in families, f'missing family: {required}'
ids = {fx.get('id') for fam in data['families'] for fx in fam.get('fixtures', [])}
for required in ['lv8_276_full', 'lv8_179_single_sheet', 'f2_4_sa_quality_fixture_v2']:
    assert required in ids, f'missing fixture id: {required}'
allowed = {'PRESENT','MISSING','RESTORED','REGENERATABLE','BLOCKED','NOT_APPLICABLE'}
for fam in data['families']:
    for fx in fam.get('fixtures', []):
        assert fx.get('status') in allowed, f'bad status: {fx}'
print('T01 inventory sanity PASS')
PY
```

Production diff guard:

```bash
if git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx' | grep -v '^codex/' | grep -v '^canvases/' ; then
  echo 'STOP: unexpected production code diff'
  exit 1
else
  echo 'PASS: no production code diff'
fi
```

## Checklist és report

Hozd létre:

- `codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`

A report a `docs/codex/report_standard.md` struktúráját kövesse. A DoD → Evidence Matrix a canvas Definition of Done pontjait 1:1-ben tartalmazza.

## Repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
```

Ha a verify piros, a report legyen FAIL, kivéve ha minden T01 DoD teljesült és a hiba bizonyítottan pre-existing / környezeti. Ilyenkor PASS_WITH_NOTES megengedett, de csak részletes indoklással.

## Végső elvárt állapot

A T01 akkor kész, ha a Phase 0 következő taskjai már pontosan tudják:

- melyik LV8 276 fixture-t használják;
- van-e használható LV8 179 fixture, vagy melyik blokkert kell előbb kezelni;
- melyik kis-synthetic SA guard fixture-t használják;
- milyen konkrét web_platform / contract_freeze anchorokra támaszkodhatnak;
- milyen fixture hiányok blokkolják T02–T06 futását.
