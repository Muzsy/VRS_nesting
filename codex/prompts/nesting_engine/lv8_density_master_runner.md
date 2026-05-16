# LV8 Density Master Runner

## Cél

Ez a dokumentum egy agent számára önállóan futtatható útmutató a végleges
LV8 packing density fejlesztési lánc (T00–T22) végrehajtásához. A master runner
nem implementálja az egyes taskokat — minden taskhoz külön canvas + goal YAML
+ per-task runner csomag tartozik, amelyet a packaging step hoz létre.
A master runner feladata a sorrend, a kötelező ellenőrzések és a checkpointok
rögzítése.

A teljes index forrása: [`canvases/nesting_engine/lv8_density_task_index.md`](../../../canvases/nesting_engine/lv8_density_task_index.md).
A végleges terv: `development_plan_packing_density_20260515.md` v2.2.

## Kötelező olvasnivaló

A futás megkezdése előtt az alábbi fájlokat ebben a sorrendben kell elolvasni:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/nesting_engine/lv8_density_task_index.md` (T00 output, gépileg
   követhető T01–T22 index)
7. A futtatandó task saját canvas + goal YAML + runner csomagja:
   - `canvases/nesting_engine/<TASK_SLUG>.md`
   - `codex/goals/canvases/nesting_engine/fill_canvas_<TASK_SLUG>.yaml`
   - `codex/prompts/nesting_engine/<TASK_SLUG>/run.md`
8. Mintaként a meglévő nesting_engine master runner és per-task runner:
   - `codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md`
   - `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`

Ha bármelyik kötelező szabályfájl hiányzik: STOP, a task reportjába `FAIL` és
a hiányzó útvonal kerül.

## Baseline preflight

A teljes lánc bármelyik tényleges (nem scaffold) task elindítása előtt a
következő preflight ellenőrzéseket kell lefuttatni:

```bash
python3 --version
cargo --version
python3 -c "import shapely; print('shapely OK')" 2>/dev/null || echo "WARN: shapely hiányzik"

ls AGENTS.md
ls docs/codex/yaml_schema.md
ls docs/codex/report_standard.md
ls docs/qa/testing_guidelines.md

ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json
ls poc/nesting_engine/f2_4_sa_quality_fixture_v2.json

cargo check -p nesting_engine
```

Phase 1 indítása előtt a Phase 0 baseline-nak léteznie kell:

```bash
ls codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md \
  || echo "STOP: Phase 0 shadow baseline report missing (T06)"
```

Ha bármelyik preflight piros: STOP, reportba a konkrét hiányt és a következő
javító lépést.

## Global hard rules

A teljes láncra érvényesek. Megsértésük automatikus FAIL.

1. **Tilos silent BLF fallback quality pathon.** Ha az NFP/quality kernel fail,
   explicit `unsupported` / `degraded` státusz + `fallback_occurred=true` jelzés.
2. **Tilos a végleges fejlesztési terv tartalmi módosítása.** A master runner
   csak végrehajtási sorrendet és gate-eket rögzít.
3. **Tilos nem létező fájlra ellenőrzés nélkül hivatkozni.** Minden anchor
   `ls`-szel igazolva; hiányzónál STOP, nem kitalálás.
4. **Tilos a `PlacementResult` output kontraktus törése.**
5. **Tilos a `NestSheet` fixture-séma törése.**
6. **Tilos `rust/nesting_engine/src/search/sa.rs` törlése Phase 0-ban.** SA
   deprecation csak T21 keretében, ADR-0002 elfogadása után.
7. **Tilos a `quality_beam_lns` és `quality_beam_lns_explore` eredményeit
   aggregálni.** Mindkét profil saját sorban / reportban.
8. **Tilos long benchmark eredményt polygon-aware validation gate
   (`worker/cavity_validation.py`) nélkül PASS-ként kezelni.**
9. **Tilos `quality_beam_lns_explore` paramétereit kézzel módosítani.**
   Kötelezően `accept_worse_pct=2.0`, `accept_worse_prob=0.05`.
10. **Tilos olyan fájlt módosítani, ami nem szerepel a task YAML stepjének
    `outputs` listájában.** A séma forrása: `docs/codex/yaml_schema.md`.
11. **Minden task utolsó stepje a Repo gate** (`./scripts/verify.sh --report …`).
12. **Tilos placeholder / synthetic fixture-t valós fixture-ként kezelni.**

## Files and fixtures to verify before start

Minden tényleges task indítása előtt a következő anchorokat kell `ls`-szel
ellenőrizni. A T00 scaffoldban már ellenőrzött lista:

```bash
ls rust/nesting_engine/src/nfp/cache.rs
ls rust/nesting_engine/src/placement/nfp_placer.rs
ls rust/nesting_engine/src/multi_bin/greedy.rs
ls vrs_nesting/config/nesting_quality_profiles.py
ls rust/nesting_engine/src/nfp/concave.rs
ls scripts/experiments/lv8_2sheet_claude_search.py
ls scripts/experiments/lv8_2sheet_claude_validate.py
ls worker/cavity_validation.py
ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json
ls poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
```

A végleges tervben szereplő LV8 179 tmp fixture
(`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`) **nem
garantált** snapshot-elem. T01 felelős a fixture inventory / helyreállításért.
T01 előtt egyetlen task sem támaszkodhat rá.

## Execution order

A futtatás kötelező sorrendje (részletes függőség: a task index Dependency graph
szekciója; rövid alak: a task index Critical path szekciója):

```text
T00 → T01 → T02 ∥ T03 ∥ T04 ∥ T05 → T06 → T07 → T08 ∥ T09 → T10 → T11 → T12 → T14 → T15 → T16 → T17 → T18 ∥ T19 → T20 → T22
```

- `∥` = párhuzamosítható (külön agentre delegálható).
- T13 opcionális; csak akkor lép a critical pathra, ha Phase 2a+2b nem éri el a
  Phase 3 baseline-t.
- T21 keresztmetsző sáv: T06 után indítható, T22 előtt zárandó.

A packaging taskokat (canvas + YAML + runner csomag létrehozása) az index
"First package batch" szekciója sorolja: T01 → T02 → T03 → T04 → T05 → T06.

## Checkpoints

A láncon kötelező mérési pontok. Egy checkpoint addig nem PASS, amíg minden
függő task FAIL-mentesen lezárt.

- **CHECKPOINT-0 (Baseline preflight):** A "Baseline preflight" parancsok
  hibátlan futása; `cargo check -p nesting_engine` zöld; LV8 + SA guard
  fixture jelen. Ha piros: STOP.
- **CHECKPOINT-1 (Phase 0 lezárás, T06 után):** Mindhárom fixture-család
  (LV8 / web_platform contract_freeze / SA guard) shadow run baseline
  reportja létezik, polygon-aware validation gate zöld. Ha piros: STOP.
- **CHECKPOINT-2 (Phase 1 lezárás, T10 után):** NfpCache audit + stats
  hardening + shape-id verification + benchmark riport zöld. Ha piros: STOP.
- **CHECKPOINT-3 (Phase 2 lezárás, T12 után):** Phase 2a + 2b scoring opt-in
  ágon mérhető pozitív density delta; gate zöld. Ha 2c-re van szükség (T13),
  azt itt kell aktiválni.
- **CHECKPOINT-4 (Phase 3 lezárás, T15/T16 után):** Critical lookahead +
  `nfp_place_starting_from` infrastruktúra kész; unit tesztek zöldek.
- **CHECKPOINT-5 (Phase 4 lezárás, T17 után):** Critical-only beam (B=4)
  bekapcsolható; gate zöld.
- **CHECKPOINT-6 (Phase 5 lezárás, T20 után):** `quality_beam_lns` és
  `quality_beam_lns_explore` külön reportban; az `_explore` paraméterei
  `accept_worse_pct=2.0`, `accept_worse_prob=0.05`. Ha aggregálva van: FAIL.
- **CHECKPOINT-FINAL (T22 lezárás):** Benchmark mátrix + release closure
  zöld minden fixture-családon, minden érintett quality profilon, polygon-aware
  validation gate-tel.

Minden checkpointon kötelező:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/<TASK_SLUG>.md
```

## Per-task runner references

A T00 packaging-en kívül a T01–T22 task csomagok még nem léteznek a repóban.
A master runner ezeket **expected path** formában rögzíti. Egy task tényleges
futtatása előtt a hozzá tartozó packaging Codex feladatnak létre kell hoznia a
canvas + goal YAML + per-task runner hármast.

```text
T00 expected runner path: codex/prompts/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner/run.md
Status: present.

T01 expected runner path: codex/prompts/nesting_engine/lv8_density_t01_phase0_fixture_inventory/run.md
Status: to be created by its own package task.

T02 expected runner path: codex/prompts/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch/run.md
Status: to be created by its own package task.

T03 expected runner path: codex/prompts/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate/run.md
Status: to be created by its own package task.

T04 expected runner path: codex/prompts/nesting_engine/lv8_density_t04_phase0_engine_stats_export/run.md
Status: to be created by its own package task.

T05 expected runner path: codex/prompts/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate/run.md
Status: to be created by its own package task.

T06 expected runner path: codex/prompts/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report/run.md
Status: to be created by its own package task.

T07 expected runner path: codex/prompts/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike/run.md
Status: to be created by its own package task.

T08 expected runner path: codex/prompts/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening/run.md
Status: to be created by its own package task.

T09 expected runner path: codex/prompts/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification/run.md
Status: to be created by its own package task.

T10 expected runner path: codex/prompts/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark/run.md
Status: to be created by its own package task.

T11 expected runner path: codex/prompts/nesting_engine/lv8_density_t11_phase2a_bbox_growth_scoring/run.md
Status: to be created by its own package task.

T12 expected runner path: codex/prompts/nesting_engine/lv8_density_t12_phase2b_extent_penalty_scoring/run.md
Status: to be created by its own package task.

T13 expected runner path: codex/prompts/nesting_engine/lv8_density_t13_phase2c_contact_bonus_scoring_optional/run.md
Status: to be created by its own package task (only if Phase 2a+2b gap requires it).

T14 expected runner path: codex/prompts/nesting_engine/lv8_density_t14_phase3_criticality_queue/run.md
Status: to be created by its own package task.

T15 expected runner path: codex/prompts/nesting_engine/lv8_density_t15_phase3_critical_lookahead/run.md
Status: to be created by its own package task.

T16 expected runner path: codex/prompts/nesting_engine/lv8_density_t16_phase3_5_nfp_place_starting_from/run.md
Status: to be created by its own package task.

T17 expected runner path: codex/prompts/nesting_engine/lv8_density_t17_phase4_critical_beam_b4/run.md
Status: to be created by its own package task.

T18 expected runner path: codex/prompts/nesting_engine/lv8_density_t18_phase5_lns_core_acceptance/run.md
Status: to be created by its own package task.

T19 expected runner path: codex/prompts/nesting_engine/lv8_density_t19_phase5_lns_destroy_repair/run.md
Status: to be created by its own package task.

T20 expected runner path: codex/prompts/nesting_engine/lv8_density_t20_phase5_quality_profiles_lns/run.md
Status: to be created by its own package task.

T21 expected runner path: codex/prompts/nesting_engine/lv8_density_t21_adr_0002_sa_deprecation/run.md
Status: to be created by its own package task.

T22 expected runner path: codex/prompts/nesting_engine/lv8_density_t22_final_benchmark_matrix_and_release_closure/run.md
Status: to be created by its own package task.
```

## Phase gates

A fázisok közötti átlépés gate-jei (mindegyik a vonatkozó task reportjában
kerül dokumentálásra):

- **Phase 0 → Phase 1 (T06 → T07):** Phase 0 baseline report zöld; mindhárom
  fixture-család validation gate-en átment; nincs aggregálatlan
  `quality_beam_lns*` mérés. Phase 1 nélküle nem indítható.
- **Phase 1 → Phase 2 (T10 → T11):** NfpCache audit + cache stats + shape-id
  invariáns + Phase 1 benchmark zöld; cache hit-rate mérhető. Phase 2
  scoring komponensei csak ezután kapcsolhatók.
- **Phase 2 → Phase 3 (T12 → T14):** Phase 2a+2b LV8 density delta ≥ baseline;
  ha nem éri el a Phase 3-hoz szükséges baseline-t, T13 (Phase 2c contact bonus)
  aktiválandó. Phase 3 csak akkor indul, ha a gap zárt.
- **Phase 3 → Phase 3.5 (T15 → T16):** Critical lookahead által hozott density
  delta mérhető; `nfp_place_starting_from` infrastruktúra unit teszttel.
- **Phase 3.5 → Phase 4 (T16 → T17):** `nfp_place_starting_from` API stabil;
  critical-only beam (B=4) opt-in profile elérhető.
- **Phase 4 → Phase 5 (T17 → T18):** Phase 4 beam zöld gate-tel; LNS framework
  kezdhető.
- **Phase 5 → Closure (T20 → T22):** mindkét `quality_beam_lns*` profil külön
  reportban; az `_explore` paraméterek fixek.
- **ADR sáv (T21 ↔ T22):** ADR-0002 elfogadva T22 előtt; `search/sa.rs`
  továbbra is fordít.

## Final benchmark matrix

A T22 záró report **kötelezően** tartalmazza az alábbi mátrixot, fixture-családonként
és érintett quality profilonként külön sorral:

| Fixture család | Quality profile | Density delta vs. baseline | Validation gate | `fallback_occurred` | Megjegyzés |
|---|---|---|---|---|---|
| LV8 (276) | baseline | 0 | PASS | false | referencia |
| LV8 (276) | Phase 2 scoring | … | PASS | false | T11/T12 |
| LV8 (276) | Phase 3 lookahead | … | PASS | false | T14/T15 |
| LV8 (276) | Phase 4 beam B=4 | … | PASS | false | T17 |
| LV8 (276) | `quality_beam_lns` | … | PASS | false | konzervatív |
| LV8 (276) | `quality_beam_lns_explore` | … | PASS | false | `accept_worse_pct=2.0`, `accept_worse_prob=0.05` |
| LV8 (179) | minden fenti profil | … | PASS | false | T01-ben helyreállított fixture, ha kellett |
| web_platform / contract_freeze | minden fenti profil | … | PASS | false | regressziómentes |
| SA guard (`f2_4_sa_quality_fixture_v2.json`) | minden fenti profil | … | PASS | false | small-synthetic |

Tilalom: a `quality_beam_lns` és `quality_beam_lns_explore` sorai sosem
aggregálhatók egyetlen sorba.

A mátrix előfeltétele a polygon-aware validation gate
(`worker/cavity_validation.py`) zöld futása minden cellához. FAIL esetén az
egész T22 FAIL, nem mátrix-cella.

## Rollback rules

1. **Granularitás:** rollback mindig a task `outputs` listájának visszaállítását
   jelenti. Több task egyetlen rollbacke csak akkor megengedett, ha közvetlen
   függőségi láncon vannak.
2. **Rust scoring komponensek (T11/T12/T13/T17):** opt-in flag default
   `false`; rollback = a profil aktivációjának visszavonása, a kód maradhat.
3. **Cache hardening (T08/T09):** rollback = stats mezők elrejtése, a kód
   változás visszafordítása. Nem érintheti a Phase 0 baseline-t.
4. **LNS (T18/T19/T20):** rollback = quality profil eltávolítása a registryből.
   `quality_beam_lns_explore` paramétereit a rollback alatt sem szabad
   átírni — csak teljes eltávolítás.
5. **ADR-0002 (T21):** rollback = ADR státusz "Rejected"-re állítása;
   `search/sa.rs` érintetlen marad.
6. **Fixture inventory (T01):** rollback = inventory dokumentum jelzése
   "stale"-ként; semmilyen placeholder fixture nem maradhat aktívan.
7. **Master runner / index (T00):** rollback = a négy T00 output git revert-je;
   tartalmi módosítás csak új T00 follow-up taskban engedélyezett.
8. **Production diff guard megsértés:** azonnali rollback az érintett task
   outputs-án kívüli production fájlokra; a task automatikusan FAIL.

## Reporting rules

1. Minden task reportja a `docs/codex/report_standard.md` szerint készül.
2. A státusz a report elején pontosan egy a következőkből: `PASS`, `FAIL`,
   `PASS_WITH_NOTES`.
3. Az `<!-- AUTO_VERIFY_START -->` / `<!-- AUTO_VERIFY_END -->` blokkot
   kizárólag a `./scripts/verify.sh` írhatja.
4. A DoD → Evidence Matrix a canvas DoD pontjait 1:1-ben sorolja; minden
   ponthoz útvonal + sorsáv + 1–3 mondatos magyarázat.
5. A `quality_beam_lns` és `quality_beam_lns_explore` méréseit külön táblában /
   külön sorban kell jelenteni. Aggregálás = FAIL.
6. Long benchmark eredménye csak polygon-aware validation gate zöld futása
   mellett kerülhet PASS-ként a riportba.
7. Advisory notes max 5 bullet, döntés-orientált.
8. A reporthoz tartozó verify log fájl (`<TASK_SLUG>.verify.log`) outputként
   szerepeljen a task YAML utolsó stepjében.
9. Ha bármely stop condition aktiválódik (lásd a task index Stop conditions
   szekcióját), a report `FAIL` státusszal és pontos hibaleírással kerül
   lezárásra; a következő javító lépés mindig fel van tüntetve.
