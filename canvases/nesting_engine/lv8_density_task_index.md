# LV8 packing density — task index

A T00 scaffold által létrehozott, gépileg követhető index a T01–T22 agent-delegálható
task-csomagokhoz (canvas + goal YAML + per-task runner). Ez a dokumentum **nem**
implementáció — a későbbi packaging taskok ebből generálják a hiányzó fájlokat.

## Source of truth

A teljes fejlesztési lánc forrása a végleges
`development_plan_packing_density_20260515.md` v2.2 terv. A terven tartalmilag nem
szabad változtatni; ez az index csak végrehajtható task-bontássá alakítja.

Repo-szinten kötelező betartani:

- `AGENTS.md` — agent szabálygyűjtemény és kötelező sorrend.
- `docs/codex/overview.md` — Codex workflow és DoD.
- `docs/codex/yaml_schema.md` — root `steps` séma; minden stepben `name`,
  `description`, `outputs`, opcionálisan `inputs`. Más sémát írni tilos.
- `docs/codex/report_standard.md` — Report Standard v2 (DoD → Evidence + Advisory).
- `docs/qa/testing_guidelines.md` — minőségkapu (`./scripts/check.sh` /
  `./scripts/verify.sh`) elvárások.

## Global invariants

Minden T0x–T22 task köteles tartani:

1. Tilos silent BLF fallback quality pathon. Ha az NFP/quality kernel fail, a státusz
   `unsupported` vagy `degraded`, explicit `fallback_occurred` jelzéssel.
2. Tilos a végleges fejlesztési terv tartalmi módosítása. Az index és a runner csak
   végrehajtási bontás.
3. Tilos nem létező fájlra hivatkozni ellenőrzés nélkül. Minden anchor előbb
   `ls`-szel igazolt, ha hiányzik: STOP + report.
4. Tilos a `PlacementResult` output kontraktus törése.
5. Tilos a `NestSheet` fixture-séma törése.
6. Tilos a `search/sa.rs` Phase 0-ban törölni; SA deprecation csak T21 keretében
   az ADR-0002 elfogadása után.
7. Tilos a `quality_beam_lns` és `quality_beam_lns_explore` eredményeit aggregálni;
   külön reportban kell mindkettő.
8. Tilos a `quality_beam_lns_explore` paramétereit kézzel állítani: kötelezően
   `accept_worse_pct=2.0`, `accept_worse_prob=0.05`.
9. Tilos long benchmark eredményt polygon-aware validation gate
   (`worker/cavity_validation.py`) nélkül PASS-ként kezelni.
10. Tilos Rust / Python production kódot módosítani olyan task keretében, amelynek
    canvas/YAML scope-ja nem ír elő ilyet (pl. T00 / index / runner-only task).
11. Minden task YAML utolsó stepje a Repo gate (`./scripts/verify.sh --report …`).
12. Csak az `outputs` listában szereplő fájlt szabad létrehozni vagy módosítani.

## Real repo anchors

A T00 audit során ellenőrzött, a fejlesztési láncban használt repo-kiindulópontok.
Mindegyik megléte futás előtt újra ellenőrzendő.

| Kategória | Útvonal | Szerep |
|---|---|---|
| Engine NFP cache | `rust/nesting_engine/src/nfp/cache.rs` | Phase 1 audit / hardening célpontja. |
| Placement loop | `rust/nesting_engine/src/placement/nfp_placer.rs` | Candidate sort + stats + Phase 2 scoring belépési pont. |
| Multi-sheet | `rust/nesting_engine/src/multi_bin/greedy.rs` | Multi-sheet run és cache életciklus. |
| Quality profile registry | `vrs_nesting/config/nesting_quality_profiles.py` | Quality profile bővítés (Phase 5 LNS, T20). |
| Concave NFP diag | `rust/nesting_engine/src/nfp/concave.rs` | `[CONCAVE NFP DIAG]` gate (T03). |
| LV8 benchmark harness | `scripts/experiments/lv8_2sheet_claude_search.py` | LV8 shadow run / benchmark belépés. |
| Legacy AABB validator | `scripts/experiments/lv8_2sheet_claude_validate.py` | Referencia: legacy validator, nem helyettesíti a polygon-aware-t. |
| Polygon validation | `worker/cavity_validation.py` | Polygon-aware validation gate (T05, T22). |
| LV8 276 fixture | `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` | Fő LV8 fixture. |
| SA guard fixture | `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` | Kis-synthetic / SA guard fixture (Phase 0 shadow run egyik családja). |

Megjegyzés: a végleges tervben szereplő
`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` „LV8 179” fixture
nem stabil snapshot-eleme a repónak. A T00 audit során az adott snapshotban
elérhető volt, de a T01 task **kötelezően** újra ellenőrzi és szükség esetén
helyreállítja (fixture inventory). A T01 előtt egyik task sem támaszkodhat rá.

## Task list

A T00–T22 lánc taskjai. Minden taskhoz a packaging step elkészíti a canvas +
goal YAML + per-task runner hármast (`canvases/nesting_engine/<TASK_SLUG>.md`,
`codex/goals/canvases/nesting_engine/fill_canvas_<TASK_SLUG>.yaml`,
`codex/prompts/nesting_engine/<TASK_SLUG>/run.md`).

### T00 — lv8_density_t00_task_scaffold_and_master_runner

- **Phase:** 0 / scaffold (jelenlegi task).
- **Cél:** Index + master runner + T00 checklist + report létrehozása. Nem
  implementál engine-kódot.
- **Fő érintett fájlok:** `canvases/nesting_engine/lv8_density_task_index.md`,
  `codex/prompts/nesting_engine/lv8_density_master_runner.md`,
  `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`,
  `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`.
- **Függőségek:** —
- **Kötelező outputok:** lásd fenti négy fájl + a verify log.
- **Acceptance gate:** repo gate zöld + sanity tokenek megvannak + nincs production
  kódmódosítás.

### T01 — lv8_density_t01_phase0_fixture_inventory

- **Phase:** 0 (mérési higiénia).
- **Cél:** LV8 család (LV8 179 + LV8 276), web_platform / contract_freeze család,
  kis-synthetic / SA guard fixture inventory. Hiányzó fixture esetén helyreállítási
  terv vagy STOP, NEM kitalálni.
- **Fő érintett fájlok:** `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`,
  `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`,
  `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`, web_platform fixture útvonalak.
- **Függőségek:** T00.
- **Kötelező outputok:** fixture inventory dokumentum a canvas alá, opcionális
  fixture restore script — engine kód nem érintett.
- **Acceptance gate:** minden fixture státusz dokumentálva (PRESENT / MISSING /
  RESTORED); nincs placeholder fixture.

### T02 — lv8_density_t02_phase0_quality_profile_shadow_switch

- **Phase:** 0.
- **Cél:** Shadow run quality profile kapcsoló bekötése a fixture-családokon
  (csak read/observe, nem új algoritmus).
- **Fő érintett fájlok:** `vrs_nesting/config/nesting_quality_profiles.py`,
  shadow run runner (LV8 2sheet harness).
- **Függőségek:** T01.
- **Kötelező outputok:** új shadow profil bejegyzés (read-only),
  baseline shadow report.
- **Acceptance gate:** shadow profile elérhető a registry-ben; eredménye nem
  bukik el polygon-aware validation gate-en.

### T03 — lv8_density_t03_phase0_nfp_diag_gate

- **Phase:** 0.
- **Cél:** `[CONCAVE NFP DIAG]` eprintln gate (env flag), hogy a shadow runokban
  rögzítsük az NFP diag jeleket.
- **Fő érintett fájlok:** `rust/nesting_engine/src/nfp/concave.rs`,
  shadow run wrapper.
- **Függőségek:** T01.
- **Kötelező outputok:** diag flag + dokumentáció a canvas alatt.
- **Acceptance gate:** flag default off, prod path változatlan; diag log csak
  bekapcsolt módban.

### T04 — lv8_density_t04_phase0_engine_stats_export

- **Phase:** 0.
- **Cél:** Engine stats (placement loop + cache hit/miss) reproducibilis export
  JSON formátumban shadow runokhoz.
- **Fő érintett fájlok:** `rust/nesting_engine/src/placement/nfp_placer.rs`,
  `rust/nesting_engine/src/multi_bin/greedy.rs`, stats serializer.
- **Függőségek:** T01.
- **Kötelező outputok:** stats JSON séma + shadow run integráció.
- **Acceptance gate:** stats output stabil hash a fixáló seed mellett; séma
  dokumentálva.

### T05 — lv8_density_t05_phase0_polygon_validation_gate

- **Phase:** 0.
- **Cél:** A `worker/cavity_validation.py` polygon-aware validációja shadow run
  utáni kötelező gate-ként a benchmark wrapperben.
- **Fő érintett fájlok:** `worker/cavity_validation.py`,
  `scripts/experiments/lv8_2sheet_claude_search.py`, validator wrapper.
- **Függőségek:** T01.
- **Kötelező outputok:** gate hook + report kimenet.
- **Acceptance gate:** validator fail = run FAIL, soha nem PASS.

### T06 — lv8_density_t06_phase0_shadow_run_baseline_report

- **Phase:** 0 (záró).
- **Cél:** Aggregált baseline report az LV8, web_platform/contract_freeze és
  SA guard fixture-családokon T02–T05 outputok alapján.
- **Fő érintett fájlok:** `codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md`
  (új), shadow run scriptek.
- **Függőségek:** T02, T03, T04, T05.
- **Kötelező outputok:** baseline report Evidence Matrix-szel.
- **Acceptance gate:** mindhárom család zöld validation gate-tel; metrikák
  reprodukálhatóak.

### T07 — lv8_density_t07_phase1_0_cache_path_discovery_spike

- **Phase:** 1.0 (cache path discovery spike, kötelező első al-lépés).
- **Cél:** Az NfpCache valós hívási útjának feltérképezése (read-only),
  cache key flow audit. Nem új cache építése.
- **Fő érintett fájlok:** `rust/nesting_engine/src/nfp/cache.rs`, hívók a
  placement / multi_bin modulban.
- **Függőségek:** T06.
- **Kötelező outputok:** discovery report (utvonalak, kulcsképzés, élethossz).
- **Acceptance gate:** cache hot/cold ütemezése dokumentálva; nincs prod
  módosítás.

### T08 — lv8_density_t08_phase1_cache_stats_hardening

- **Phase:** 1.
- **Cél:** Cache hit/miss/eviction statisztikák hardening + observability
  (még mindig audit-jellegű, additive).
- **Fő érintett fájlok:** `rust/nesting_engine/src/nfp/cache.rs`,
  stats export hook.
- **Függőségek:** T07.
- **Kötelező outputok:** stats mezők + unit teszt.
- **Acceptance gate:** stats mezők elérhetők shadow runban; nincs algoritmus
  változás.

### T09 — lv8_density_t09_phase1_shape_id_cache_key_verification

- **Phase:** 1.
- **Cél:** Shape-id / cache-key invariáns ellenőrzés és teszt: ugyanaz a part
  ugyanazt a kulcsot adja, eltérő part nem ütközik.
- **Fő érintett fájlok:** `rust/nesting_engine/src/nfp/cache.rs`,
  shape-id helper, teszt-fixture.
- **Függőségek:** T07.
- **Kötelező outputok:** unit teszt + fixture.
- **Acceptance gate:** invariáns teszt zöld; collision counter = 0.

### T10 — lv8_density_t10_phase1_cache_usage_audit_and_benchmark

- **Phase:** 1 (záró).
- **Cél:** Cache használat aggregált audit + LV8 + SA guard benchmark, hogy
  a Phase 2 baseline-ja egyértelmű legyen.
- **Fő érintett fájlok:** `scripts/experiments/lv8_2sheet_claude_search.py`,
  cache stats consumer.
- **Függőségek:** T08, T09.
- **Kötelező outputok:** Phase 1 benchmark report.
- **Acceptance gate:** mérhető cache hit-rate; polygon-aware validation zöld.

### T11 — lv8_density_t11_phase2a_bbox_growth_scoring

- **Phase:** 2a.
- **Cél:** Bbox-growth scoring komponens bevezetése a placement candidate
  sortolásba.
- **Fő érintett fájlok:** `rust/nesting_engine/src/placement/nfp_placer.rs`,
  scoring helper.
- **Függőségek:** T10.
- **Kötelező outputok:** scoring függvény + opt-in flag + teszt.
- **Acceptance gate:** baseline-nál nem rosszabb LV8 density; gate zöld.

### T12 — lv8_density_t12_phase2b_extent_penalty_scoring

- **Phase:** 2b.
- **Cél:** Extent penalty komponens (bbox-growth tetejére).
- **Fő érintett fájlok:** `rust/nesting_engine/src/placement/nfp_placer.rs`,
  scoring helper.
- **Függőségek:** T11.
- **Kötelező outputok:** scoring komponens + teszt.
- **Acceptance gate:** LV8 density Phase 2b ≥ Phase 2a baseline.

### T13 — lv8_density_t13_phase2c_contact_bonus_scoring_optional

- **Phase:** 2c (opcionális).
- **Cél:** Contact bonus scoring opt-in formában. Csak akkor kerül a critical
  pathra, ha Phase 2a+2b nem éri el a Phase 3 baseline-t.
- **Fő érintett fájlok:** scoring helper, contact detection util.
- **Függőségek:** T12.
- **Kötelező outputok:** opt-in scoring + dokumentált activation feltétel.
- **Acceptance gate:** opt-in default off; ha aktív, gate zöld.

### T14 — lv8_density_t14_phase3_criticality_queue

- **Phase:** 3.
- **Cél:** Critical-part-focused queue / prioritizálás bevezetése (lookahead
  alapja).
- **Fő érintett fájlok:** `rust/nesting_engine/src/placement/nfp_placer.rs`,
  queue modul.
- **Függőségek:** T12.
- **Kötelező outputok:** queue komponens + teszt.
- **Acceptance gate:** critical part flag tiszta; LV8 density nem regresszál.

### T15 — lv8_density_t15_phase3_critical_lookahead

- **Phase:** 3.
- **Cél:** Lookahead a kritikus partokra a queue tetején.
- **Fő érintett fájlok:** placement loop, lookahead modul.
- **Függőségek:** T14.
- **Kötelező outputok:** lookahead bekapcsolható ágként.
- **Acceptance gate:** mérhető density nyereség Phase 3-on; gate zöld.

### T16 — lv8_density_t16_phase3_5_nfp_place_starting_from

- **Phase:** 3.5 (önálló infrastruktúra-fázis).
- **Cél:** `nfp_place_starting_from` infrastruktúra: adott pozícióból induló
  NFP placement keresés, nem új scoring.
- **Fő érintett fájlok:** `rust/nesting_engine/src/nfp/`, placement loop.
- **Függőségek:** T10 (Phase 1 lezárva); kötelező T17/T19 előtt.
- **Kötelező outputok:** API + unit teszt.
- **Acceptance gate:** unit teszt zöld; integráció nélkül érintett ágak
  változatlanok.

### T17 — lv8_density_t17_phase4_critical_beam_b4

- **Phase:** 4.
- **Cél:** Critical-only beam (B=4) keresési stratégia.
- **Fő érintett fájlok:** placement / beam modul.
- **Függőségek:** T15, T16.
- **Kötelező outputok:** beam impl + opt-in profile bekötés.
- **Acceptance gate:** baseline-hoz képest pozitív density delta LV8-on.

### T18 — lv8_density_t18_phase5_lns_core_acceptance

- **Phase:** 5.
- **Cél:** LNS refinement core: elfogadási kritérium + framework.
- **Fő érintett fájlok:** `rust/nesting_engine/src/` (új LNS modul).
- **Függőségek:** T16.
- **Kötelező outputok:** LNS core skeleton + unit teszt.
- **Acceptance gate:** unit teszt zöld; quality profile nem aktivált alapból.

### T19 — lv8_density_t19_phase5_lns_destroy_repair

- **Phase:** 5.
- **Cél:** LNS destroy/repair operátorok.
- **Fő érintett fájlok:** LNS modul, operátor lib.
- **Függőségek:** T16, T18.
- **Kötelező outputok:** operátor impl + teszt.
- **Acceptance gate:** elfogadási kritériumra illeszkedik; egységteszt zöld.

### T20 — lv8_density_t20_phase5_quality_profiles_lns

- **Phase:** 5 (záró).
- **Cél:** `quality_beam_lns` és `quality_beam_lns_explore` quality profilok bekötése.
  Az `_explore` változat kötelezően `accept_worse_pct=2.0`,
  `accept_worse_prob=0.05`. A két profil eredménye soha nem aggregálódik.
- **Fő érintett fájlok:** `vrs_nesting/config/nesting_quality_profiles.py`,
  runner wiring.
- **Függőségek:** T17, T19.
- **Kötelező outputok:** két profil + külön report scaffold.
- **Acceptance gate:** invariáns: paraméterek nem felülírhatók, eredmény külön
  reportban.

### T21 — lv8_density_t21_adr_0002_sa_deprecation

- **Phase:** keresztmetsző (Phase 0 után, T22 előtt).
- **Cél:** ADR-0002 SA deprecation: `search/sa.rs` deprecation döntés
  dokumentációja és előkészítés. Phase 0-ban nem törölhető, csak deprecate
  jelölés.
- **Fő érintett fájlok:** `docs/adr/0002_sa_deprecation.md` (új), `search/sa.rs`
  jelölés.
- **Függőségek:** T06 (Phase 0 baseline lezárult).
- **Kötelező outputok:** ADR + jelölés + report.
- **Acceptance gate:** ADR elfogadva; SA path továbbra is fordít.

### T22 — lv8_density_t22_final_benchmark_matrix_and_release_closure

- **Phase:** záró.
- **Cél:** Végső benchmark mátrix (LV8 + web_platform/contract_freeze + SA guard,
  összes érintett quality profil), release closure report. Long benchmark a
  polygon-aware validation gate után.
- **Fő érintett fájlok:** benchmark runner, riport sablon.
- **Függőségek:** T20, T21.
- **Kötelező outputok:** mátrix report + closure dokumentum.
- **Acceptance gate:** minden fixture/profil zöld validation gate-tel;
  `quality_beam_lns` és `quality_beam_lns_explore` külön sorban.

## Dependency graph

```text
T00 -> T01
T01 -> T02, T03, T04, T05
T02 + T03 + T04 + T05 -> T06
T06 -> T07
T07 -> T08, T09
T08 + T09 -> T10
T10 -> T11 -> T12
T12 -> T14 -> T15
T16 depends on T10, can run after Phase 1 but before T17/T19
T15 + T16 -> T17
T16 + T18 -> T19
T17 + T19 -> T20
T20 -> T22
T21 can start after T06, final before T22
```

T13 opcionális; a critical pathra akkor kerül, ha Phase 2a+2b nem éri el a
Phase 3-hoz szükséges baseline-t.

## Critical path

```text
T00 → T01 → T02/T03/T04/T05 → T06 → T07 → T08/T09 → T10 → T11 → T12 → T14 → T15 → T16 → T17 → T18/T19 → T20 → T22
```

T13 normál esetben opcionális; csak akkor lép be a kritikus útba, ha a Phase 2a+2b
mérés nem éri el a Phase 3 baseline-t.

T21 (SA deprecation ADR) párhuzamos sáv: T06 után indítható, T22 előtt zárandó.

## Parallelization notes

- **Phase 0 wave (T02, T03, T04, T05):** T01 után párhuzamosíthatók. Külön agentre
  delegálhatók; közös output a T06 baseline reportba aggregálódik.
- **Phase 1 wave (T08, T09):** T07 után párhuzamosíthatók.
- **T16 (Phase 3.5):** logikailag infrastruktúra, T10 után már indítható, nem
  blokkolja T11–T15-öt, de T17/T19 előtt kötelező lezárni.
- **T18 + T19:** T16 után; T18-at követheti T19 vagy párhuzamos kezdés, ha az
  operátor framework T18 első checkpointja után kész.
- **T21:** keresztmetsző sáv. T06 után bármikor; T22 előtt mindenképp.
- **T13:** csak feltételes párhuzamosítás (Phase 2a+2b gap esetén).

## First package batch

A T00 csak indexet és master runnert hoz létre, nem T01–T22 packaging-et. A javasolt
első batch a packaging taskoknak (mindegyik külön Codex feladat):

1. **T01** packaging — fixture inventory canvas + YAML + runner.
2. **T02** packaging — quality profile shadow switch (read/observe).
3. **T03** packaging — `[CONCAVE NFP DIAG]` gate flag.
4. **T04** packaging — engine stats export.
5. **T05** packaging — polygon validation gate.

A batch tartalmazza még a T06 packaging-et a Phase 0 lezárásához, mihelyt T02–T05
canvas csomagok elkészültek és átnézhetők.

## Stop conditions

A láncot **azonnal meg kell állítani**, ha bármelyik teljesül:

1. Egy task kritikus repo anchor fájlja hiányzik a vártnál (pl. `cache.rs`,
   `nfp_placer.rs`, `nesting_quality_profiles.py`, LV8 fixture). Pótlást kitalálni
   tilos.
2. Egy task production kódot módosítana a saját scope-ján kívül (pl. T00 / index
   / runner-only task érinti a Rust engine-t vagy Python production kódot).
3. A polygon-aware validation gate (`worker/cavity_validation.py`) FAIL státuszt
   ad egy benchmark / shadow run végén — long benchmark eredmény nem PASS-olható.
4. A `quality_beam_lns` és `quality_beam_lns_explore` outputok aggregálódnának
   egy reportban.
5. Silent BLF fallback történne a quality pathon (`fallback_occurred=true` és
   nincs explicit `unsupported` / `degraded` jelzés).
6. A repo gate (`./scripts/verify.sh`) piros, és a hiba nem dokumentált a
   reportban — ilyenkor a task státusza FAIL.

Bármely STOP feltételnél a task report `FAIL` státuszt kap, és a stop ok
pontosan rögzítendő a következő javító lépéssel együtt.
