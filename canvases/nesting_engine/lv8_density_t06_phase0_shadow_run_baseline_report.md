# LV8 Density T06 — Phase 0 shadow run baseline report

## 🎯 Funkció

A T06 feladat célja a Phase 0 lezárása: a T02–T05 során előkészített mérési infrastruktúra alapján **aggregált shadow baseline riportot** kell készíteni az SA-alapú legacy quality profile-ok és a no-SA shadow profile-ok összehasonlításáról.

A T06 nem új algoritmust fejleszt. Ez egy mérési, auditálási és döntés-előkészítő task.

A végleges terv szerint a Phase 0 csak akkor tekinthető lezártnak, ha:

1. a T02 shadow profile-párok mérhetőek,
2. a T03 diagnosztikai stderr zaj nem zavarja a méréseket,
3. a T04 engine stats megjelennek a `summary.json`-ban,
4. a T05 polygon-aware validation gate binding része a végső `valid` döntésnek,
5. a három fixture-család eredménye aggregált baseline riportban szerepel.

---

## T06 előfeltételek

A task csak akkor indulhat implementációval / futtatással, ha ezek a reportok léteznek és `PASS` vagy `PASS_WITH_NOTES` státuszúak:

```text
codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
```

Ha bármelyik hiányzik vagy FAIL/BLOCKED, a T06 report státusza legyen `FAIL/BLOCKED`, és ne induljon hosszabb benchmark.

---

## Valós repo-kiindulópontok a friss snapshot alapján

### Quality profile párok

A T02 után a shadow profile-párokat a kód tartalmazza:

```text
vrs_nesting/config/nesting_quality_profiles.py
```

Elvárt helper:

```python
from vrs_nesting.config.nesting_quality_profiles import get_phase0_shadow_profile_pairs
```

Elvárt párok:

```text
quality_default    -> quality_default_no_sa_shadow
quality_aggressive -> quality_aggressive_no_sa_shadow
```

### LV8 / engine harness

A T04+T05 után a fő engine benchmark harness:

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A summary-ban kötelezően szerepelnie kell:

```text
engine_stats
valid_quantity_gate
valid_polygon_gate
polygon_validation
valid
quality_profile
seed
fixture_path
runtime_sec
placed_instances
required_instances
utilization_pct
sheets_used
```

### Polygon-aware gate

A T05 után a binding validator:

```text
scripts/experiments/lv8_polygon_validator.py
```

A `summary["valid"]` csak akkor lehet true, ha a completion, quantity és polygon gate is true.

### Fixture-családok

A T01 döntései alapján a három család:

#### 1. LV8 család

Kötelező elsődleges fixture:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

LV8 179 single-sheet fixture:

```text
tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json
```

Fontos: a friss snapshotban ezt újra kell ellenőrizni. Ha hiányzik, nem szabad placeholdert gyártani. A T06 reportban `fixture_missing` státusszal kell szerepeltetni, és a hard-cut decision nem lehet `APPROVE`.

#### 2. Small synthetic / SA guard család

```text
poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
```

Ez kötelezően futtatandó, mert ez védi azt az esetet, hogy kis fixture-ön az SA még hasznos lehet.

#### 3. web_platform / contract_freeze család

A T01 report alapján a jelenlegi repo-anchor:

```text
scripts/smoke_svg_export.py
samples/dxf_demo/stock_rect_1000x2000.dxf
samples/dxf_demo/part_arc_spline_chaining_ok.dxf
codex/reports/web_platform_phase0_contract_freeze.md
```

Ez a család nem feltétlenül quality-profile-aware engine fixture. T06-ban ezért két dolgot kell külön rögzíteni:

1. lefutott-e a contract-freeze smoke/regression gate,
2. van-e közvetlen SA vs no-SA profile összehasonlítási lehetőség.

Ha nincs közvetlen quality-profile comparison path, ezt `shadow_profile_applicability = "not_applicable"` értékkel kell riportolni, nem szabad hamis util/placed összehasonlítást gyártani.

---

## T06 scope

### T06 feladata

1. Ellenőrizni T01–T05 előfeltételeket.
2. Ellenőrizni a három fixture-család aktuális elérhetőségét.
3. Létrehozni egy kis shadow matrix futtató / aggregáló scriptet, vagy a meglévő harness hívásokkal egyenértékű dokumentált futtatási flow-t.
4. Lefuttatni az engine fixture-ökön a shadow profile-párokat:
   - `quality_default` vs `quality_default_no_sa_shadow`,
   - `quality_aggressive` vs `quality_aggressive_no_sa_shadow`.
5. Minden engine runnál rögzíteni:
   - `summary.json`,
   - `polygon_validation.json`,
   - `engine_stats`,
   - `valid_quantity_gate`,
   - `valid_polygon_gate`,
   - `valid`.
6. Lefuttatni a contract-freeze smoke/regression gate-et, vagy explicit dokumentálni, ha nem futtatható.
7. Elkészíteni az aggregált Phase 0 baseline riportot.
8. Döntést adni:
   - `APPROVE_NO_SA_HARD_CUT`,
   - `DEFER_HARD_CUT`,
   - `BLOCKED`.

### T06 nem célja

- Nem módosítja a Rust engine algoritmust.
- Nem módosítja az NFP cache-t.
- Nem módosítja a T05 polygon validator logikáját, csak használja.
- Nem törli vagy hard-cutolja automatikusan a legacy SA profile-okat, ha nincs teljes evidence.
- Nem futtat Phase 1 cache auditot.
- Nem hoz létre placeholder fixture-t hiányzó LV8 179 helyett.

---

## Javasolt implementáció

### 1) Shadow matrix script

Javasolt új fájl:

```text
scripts/experiments/lv8_phase0_shadow_run_matrix.py
```

A script feladata:

- importálja a `get_phase0_shadow_profile_pairs()` helper-t,
- ellenőrzi a fixture pathokat,
- engine fixture-ök esetén meghívja a meglévő `scripts/experiments/lv8_2sheet_claude_search.py` scriptet subprocessből,
- minden run outputját külön run könyvtárba írja,
- aggregálja a `summary.json` fájlokat,
- contract-freeze esetén futtatja a `python3 scripts/smoke_svg_export.py` smoke-ot, és külön regression row-t ír,
- létrehozza az összesítő JSON/MD artefaktokat.

Javasolt CLI:

```bash
python3 scripts/experiments/lv8_phase0_shadow_run_matrix.py \
  --out-root tmp/lv8_density_phase0_shadow_runs \
  --time-limit-sec 600 \
  --seed 42 \
  --include-lv8-179 auto \
  --run-contract-freeze-smoke 1
```

A `--include-lv8-179 auto` jelentése:

- ha a T01 szerinti LV8 179 fixture létezik, futtasd,
- ha nem létezik, rögzíts `fixture_missing` row-t, és a hard-cut decision legyen legfeljebb `DEFER_HARD_CUT`.

### 2) Output struktúra

A T06 script / task hozza létre legalább:

```text
tmp/lv8_density_phase0_shadow_runs/runs.jsonl
tmp/lv8_density_phase0_shadow_runs/phase0_shadow_matrix.json
tmp/lv8_density_phase0_shadow_runs/phase0_shadow_matrix.md
tmp/lv8_density_phase0_shadow_runs/hard_cut_decision.json
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
```

A `lv8_density_phase0_shadow_baseline.md` checkpoint report lehet rövid összefoglaló / alias, de léteznie kell, mert a T00 master runner erre hivatkozik.

### 3) Döntési logika

#### Engine fixture comparison

Egy profile-pár engine fixture-en akkor `pair_pass`, ha:

- no-SA placed_instances ≥ legacy SA placed_instances,
- no-SA utilization_pct ≥ legacy SA utilization_pct, ha mindkettő numerikus,
- no-SA valid_polygon_gate nem rosszabb, mint legacy,
- no-SA timed_out nem rosszabb, mint legacy,
- no-SA return_code nem rosszabb, mint legacy.

Ha a legacy SA timeoutol vagy nincs valid solver stdout, de a no-SA valid és jobb placed countot ad, a row `pair_pass = true` lehet, de a reportban külön jelölni kell `legacy_failed_or_timeout = true`.

#### Contract-freeze comparison

A contract-freeze család minimum gate-je:

```bash
python3 scripts/smoke_svg_export.py
```

Ha ez PASS, a család regression gate-je PASS.

Ha nincs quality-profile-aware comparison path, a row:

```json
{
  "family_id": "web_platform_contract_freeze",
  "shadow_profile_applicability": "not_applicable",
  "regression_gate": "PASS"
}
```

Ez önmagában nem igazolja a no-SA hard-cutot, de nem is hamis regresszió.

#### Hard-cut decision

A `hard_cut_decision.json` értékei:

```text
APPROVE_NO_SA_HARD_CUT
DEFER_HARD_CUT
BLOCKED
```

`APPROVE_NO_SA_HARD_CUT` csak akkor engedélyezett, ha:

- minden kötelező engine fixture elérhető,
- minden engine fixture profile-pár `pair_pass = true`,
- a small synthetic / SA guard is `pair_pass = true`,
- minden futott row polygon-aware gate-tel riportolt,
- contract-freeze smoke PASS,
- nincs hiányzó output vagy parse error.

Ha az LV8 179 hiányzik, vagy contract-freeze nem profil-komparábilis, a döntés legyen `DEFER_HARD_CUT`, ne `APPROVE`.

---

## Tesztelési terv

### Kötelező célzott tesztek

Ha új shadow matrix script készül, legyen célzott pytest:

```text
tests/test_lv8_phase0_shadow_run_matrix.py
```

Fedje legalább:

- profile pair import és stabil mapping,
- missing fixture → `fixture_missing` row + `DEFER_HARD_CUT`,
- summary comparison: no-SA jobb/equal → pair_pass true,
- polygon gate false → pair_pass false vagy row invalid,
- contract-freeze not_applicable row nem számol hamis util/placed összehasonlítást.

### Kötelező parancsok

```bash
python3 -m py_compile scripts/experiments/lv8_phase0_shadow_run_matrix.py
python3 -m pytest tests/test_lv8_phase0_shadow_run_matrix.py -q
python3 -m py_compile scripts/experiments/lv8_2sheet_claude_search.py
python3 -m py_compile scripts/experiments/lv8_polygon_validator.py
```

Ha a release binary hiányzik, a T06 runner építheti:

```bash
cargo build --release -p nesting_engine
```

A teljes repo gate továbbra is kötelező:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
```

---

## Definition of Done

- [ ] T01–T05 report státuszok ellenőrizve és dokumentálva.
- [ ] Fixture availability újraellenőrizve a friss snapshoton.
- [ ] LV8 276 shadow profile-párok lefutottak vagy BLOCKED indokolt.
- [ ] LV8 179 lefutott, ha fixture létezik; ha hiányzik, `fixture_missing` row és `DEFER_HARD_CUT`.
- [ ] Small synthetic / SA guard shadow profile-párok lefutottak.
- [ ] Contract-freeze smoke/regression gate lefutott vagy explicit BLOCKED.
- [ ] Minden engine run summary tartalmazza `engine_stats`, `valid_polygon_gate`, `polygon_validation`, `quality_profile`, `seed`, `fixture_path` mezőket.
- [ ] Aggregált `phase0_shadow_matrix.json` és `.md` elkészült.
- [ ] `hard_cut_decision.json` elkészült, döntése indokolt.
- [ ] `codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md` checkpoint report elkészült.
- [ ] T06 task report Report Standard v2 szerint, DoD → Evidence Matrix-szal elkészült.
- [ ] Repo gate lefutott wrapperrel, verify loggal.

---

## Rollback / failure policy

Ha bármely binding előfeltétel hiányzik:

- ne módosíts quality profile hard-cutot,
- ne induljon hosszú benchmark,
- report státusz: `FAIL` vagy `BLOCKED`,
- következő task, T07, nem indulhat.

Ha benchmark fut, de eredmény vegyes:

- report státusz lehet `PASS_WITH_NOTES`, ha a futtatási infrastruktúra és riport teljes,
- hard-cut decision legyen `DEFER_HARD_CUT`,
- T07 csak akkor indulhat, ha explicit döntés születik, hogy a Phase 1 cache audit nem függ a hard-cut véglegesítésétől.

---

## Advisory

A T06 hosszabb futású task lehet. Hermes / hosszabb futású agent esetén célszerű a teljes matrixot futtatni. Rövidebb Codex futás esetén legalább a célzott teszteket és a kis fixture shadowt kell futtatni, majd a hiányzó LV8 hosszú futásokat `BLOCKED` vagy `DEFER_HARD_CUT` státusszal dokumentálni. A reportban tilos úgy `PASS`-t írni, hogy a hard-cut evidence nem teljes.
