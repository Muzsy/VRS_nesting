# `jagua-rs` + saját optimizer átállás — canvas+YAML+runner task-bontás

**Projekt:** DXF Nesting / VRS_nesting  
**Forrás terv:** `jagua_rs_sajat_optimizer_fejlesztesi_terv.md`  
**Repo snapshot alapján igazított terület:** `egyedi_solver`  
**Cél:** a stratégiai terv lebontása olyan agent-delegálható taskokra, amelyek a repo jelenlegi `canvas + goal YAML + runner + checklist + report` szabályrendszerét követik.

---

## 0. Rövid döntés

A tervet a repo szabályai szerint **nem egyetlen nagy implementációs taskra**, hanem egy hosszú, gate-elt munkaláncra érdemes bontani.

A javasolt munkaterület:

```text
canvases/egyedi_solver/
codex/goals/canvases/egyedi_solver/
codex/prompts/egyedi_solver/<TASK_SLUG>/run.md
codex/codex_checklist/egyedi_solver/
codex/reports/egyedi_solver/
```

Indok:

- A repo-ban már létezik `egyedi_solver` terület.
- A `rust/vrs_solver/Cargo.toml` már tartalmaz `jagua-rs = "0.6.4"` dependencyt.
- A `rust/vrs_solver/src/main.rs` jelenleg egyszerű, monolit, sor/cursor jellegű baseline solver, tehát jó kiindulási pont egy fokozatos jagua-alapú saját optimizerhez.
- A `vrs_nesting/runner/vrs_solver_runner.py` és `vrs_nesting/runner/solver_adapter.py` már ad futtatási boundaryt.
- A `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py` már releváns alap a Phase 3 cavity-prepack réteghez.

---

## 1. Kötelező repo-szabályok, amelyeket minden tasknak követnie kell

Minden task package kötelező artefaktjai:

```text
canvases/egyedi_solver/<TASK_SLUG>.md
codex/goals/canvases/egyedi_solver/fill_canvas_<TASK_SLUG>.yaml
codex/prompts/egyedi_solver/<TASK_SLUG>/run.md
codex/codex_checklist/egyedi_solver/<TASK_SLUG>.md
codex/reports/egyedi_solver/<TASK_SLUG>.md
codex/reports/egyedi_solver/<TASK_SLUG>.verify.log
```

Minden goal YAML kizárólag ezt a sémát használhatja:

```yaml
steps:
  - name: "<lépés neve>"
    description: >
      <végrehajtható utasítás>
    inputs:
      - "<opcionális bemeneti fájl>"
    outputs:
      - "<létrehozható vagy módosítható fájl>"
```

Minden YAML utolsó lépése:

```yaml
  - name: "Repo gate (automatikus verify)"
    description: >
      Futtasd a standard repo gate-et wrapperrel:
      ./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md
    outputs:
      - "codex/reports/egyedi_solver/<TASK_SLUG>.md"
      - "codex/reports/egyedi_solver/<TASK_SLUG>.verify.log"
```

Nem alkuképes szabályok:

1. Csak a YAML `outputs` listájában szereplő fájl módosítható vagy hozható létre.
2. Nem lehet nem létező fájlt, mezőt, parancsot vagy repo-konvenciót kitalálni.
3. Minden task elején olvasni kell: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
4. A végén kötelező a `./scripts/verify.sh --report ...` wrapper.
5. Invalid nesting layout soha nem lehet PASS.
6. Phase 1-ben a hole-os partokat tilos csendben kezelni vagy eldobni.
7. Phase 2-ben az irregular/remnant sheet nem jelent container-hole támogatást.
8. Phase 3-ban a cavity-prepack expansion után a darablista és exact final validation kötelező.
9. A régi `rust/nesting_engine` exact NFP motor nem keverendő össze ezzel a munkalánccal; összehasonlító benchmarkban használható, de nem ennek a core-ja.
10. Ha egy task túl nagy diffet okozna, STOP + report, és split javaslat.

---

## 2. Valós repo-anchorok a snapshot alapján

Ezek a fájlok a bontás során valós kiindulópontként kezelhetők, de minden agent futáskor újra ellenőrizni kell őket.

| Kategória | Útvonal | Szerep |
|---|---|---|
| Repo szabály | `AGENTS.md` | Elsődleges agent szabályfájl. |
| Workflow | `docs/codex/overview.md` | Canvas/YAML/report workflow. |
| YAML séma | `docs/codex/yaml_schema.md` | Egyetlen elfogadott goal YAML séma. |
| Report standard | `docs/codex/report_standard.md` | DoD → Evidence report. |
| QA | `docs/qa/testing_guidelines.md` | Repo gate és teszt minimumok. |
| Jelenlegi jagua crate | `rust/vrs_solver/Cargo.toml` | Már tartalmaz `jagua-rs = "0.6.4"`. |
| Jelenlegi solver main | `rust/vrs_solver/src/main.rs` | Monolit, egyszerű table solver; refaktorálandó. |
| Solver IO contract | `docs/solver_io_contract.md` | V1 JSON input/output boundary. |
| VRS solver runner | `vrs_nesting/runner/vrs_solver_runner.py` | Fájl-alapú solver subprocess runner. |
| Solver adapter boundary | `vrs_nesting/runner/solver_adapter.py` | `vrs_solver` / `sparrow` adapter mintázat. |
| Output validator | `vrs_nesting/nesting/instances.py` | Multi-sheet output és geometry validation. |
| Cavity prepack | `worker/cavity_prepack.py` | Meglévő cavity-prepack logika. |
| Cavity validation | `worker/cavity_validation.py` | Polygon-aware cavity validation. |
| Result normalizer | `worker/result_normalizer.py` | Layout projection/normalization. |
| Quality profiles | `vrs_nesting/config/nesting_quality_profiles.py` | Későbbi backend/profile integráció. |
| Worker entry | `worker/main.py` | Backend futtatási bridge. |
| Old exact NFP engine | `rust/nesting_engine/*` | Összehasonlító baseline, nem az új core. |
| Existing jagua canvas | `canvases/egyedi_solver/jagua_rs_feasibility_integration.md` | Korábbi jagua feasibility előzmény. |
| Existing irregular backlog | `docs/egyedi_solver/irregular_engine_backlog_p0_p3.md` | Régi stratégiai backlog, részben hasznos, de a mostani terv felülírja a prioritást. |

---

## 3. Névkonvenció

Task slug forma:

```text
jagua_optimizer_tNN_<rövid_leírás>
```

Példa:

```text
jagua_optimizer_t04_jagua_adapter_contract_poc
```

Package pathok:

```text
Canvas:     canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
Goal YAML:  codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml
Runner:     codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md
Checklist:  codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
Report:     codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
Verify log: codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.verify.log
```

---

## 4. Fázisok

```text
Phase 0 — scaffold, repo/source audit, modularizációs előkészítés
Phase 1 — rectangular multi-sheet, hole nélkül
Phase 2 — irregular/remnant sheet, hole nélkül
Phase 3 — cavity-prepack + macro-part expansion
Phase 4 — profile/backend integration
Phase 5 — benchmark + release döntés
```

---

## 5. Globális invariánsok

Minden taskban szerepeljen canvas szinten:

- **Hole policy:** Phase 1–2 alatt item hole kezelése tilos; explicit unsupported/warning kell.
- **No silent geometry loss:** DXF/part metadata nem veszhet el.
- **Exact final validation:** elfogadott layout csak validator PASS után lehet sikeres.
- **Determinism:** seed + input → reprodukálható output/metrika.
- **Time budget:** minden hosszú keresésnek legyen explicit time limit és stopping policy.
- **Feature gating:** új jagua optimizer profil ne törje a meglévő `vrs_solver`/`sparrow`/`nesting_engine` útvonalakat.
- **Small steps:** nagy refaktor tilos egyben; moduláris bontás.
- **Report evidence:** minden DoD ponthoz fájl/szakasz/parancs bizonyíték kell.

---

## 6. Task lista

### JG-00 — `jagua_optimizer_t00_task_scaffold_and_master_runner`

**Phase:** 0 / scaffold  
**Cél:** A teljes jagua-rs + saját optimizer fejlesztési lánc repo-kompatibilis task-indexének és master runnerének létrehozása. Ez még nem implementál solver-kódot.  
**Függőség:** —

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t00_task_scaffold_and_master_runner.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log`

**Érintett fókusz:** canvases/egyedi_solver/jagua_optimizer_task_index.md; codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md; checklist/report

**Acceptance gate:** Task index tartalmazza JG-00…JG-27 taskokat, dependency graphot, critical pathot, phase gate-eket; master runner önállóan futtatható; production kód nem módosul.

**Megjegyzés:** Ez a legelső futtatható csomag: ebből készülhetnek a konkrét JG-01…JG-27 package-ek.

### JG-01 — `jagua_optimizer_t01_repo_and_source_audit`

**Phase:** 0 / audit  
**Cél:** Repo + jagua-rs + Sparrow valóságellenőrzés: mi létezik már, mit szabad újrahasznosítani, mi a kockázat.  
**Függőség:** JG-00

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t01_repo_and_source_audit.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`
- `docs/egyedi_solver/jagua_optimizer_source_audit.md`

**Érintett fókusz:** Audit report, nem termékkód. Ellenőrzi `rust/vrs_solver`, `docs/solver_io_contract.md`, runner adapterek, meglévő cavity pipeline, Sparrow minták, jagua-rs API használatát.

**Acceptance gate:** A report külön táblában rögzíti: használható repo anchorok, jagua-rs képességek, Sparrowból átvehető minták, rectangular/irregular/hole kockázatok, licenc/dependency megjegyzések.

**Megjegyzés:** Ne README-szintű audit legyen: kódszintű anchorokat kell megadni. Ha külső forrás nem érhető el, ezt explicit blockernek kell jelölni.

### JG-02 — `jagua_optimizer_t02_solver_module_scaffold`

**Phase:** 0 / architecture  
**Cél:** A jelenlegi monolit `rust/vrs_solver/src/main.rs` moduláris előkészítése viselkedésváltozás nélkül.  
**Függőség:** JG-01

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t02_solver_module_scaffold.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/main.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`

**Érintett fókusz:** `rust/vrs_solver/src/*` modulstruktúra: io, geometry, sheet, item, adapter, optimizer, validation. A main.rs csak CLI/orchestration maradjon.

**Acceptance gate:** A meglévő solver output byte-szinten vagy szemantikailag változatlan a meglévő smoke inputokon; `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS; repo gate PASS.

**Megjegyzés:** Ez refaktor, nem új optimizer. Ha túl nagy diff lenne, kisebb rész-taskra kell bontani.

### JG-03 — `jagua_optimizer_t03_outer_only_contract_and_hole_gate`

**Phase:** 1 / rectangular preflight  
**Cél:** Outer-only Phase 1 contract rögzítése: hole-os partokat tilos csendben kezelni vagy eldobni.  
**Függőség:** JG-02

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t03_outer_only_contract_and_hole_gate.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/nesting/instances.py`
- `scripts/smoke_jagua_optimizer_outer_only_contract.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`

**Érintett fókusz:** Solver IO contract kiegészítés `solver_profile`, `capabilities`, `unsupported_reason` jelzésekkel; input validation a vrs_solverben és Python runner/validator oldalon.

**Acceptance gate:** Hole-os part input Phase 1 profile alatt deterministic unsupported/error státuszt ad; stock hole/remnant kezelés nincs véletlenül engedélyezve; rectangle-only korábbi smoke nem törik.

**Megjegyzés:** A későbbi cavity-prepack miatt a hole metadata megmarad, de Phase 1 solverbe nem jut be.

### JG-04 — `jagua_optimizer_t04_jagua_adapter_contract_poc`

**Phase:** 1 / backend adapter  
**Cél:** Vékony `JaguaAdapter` contract és proof-of-contact: polygon/rect itemek ütközésének ellenőrzése, backend elrejtése az optimizer mögé.  
**Függőség:** JG-02, JG-03

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs`
- `scripts/smoke_jagua_adapter_contract.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`

**Érintett fókusz:** Adapter trait/struct, geometry conversion, egyszerű item-item és item-sheet smoke tesztek.

**Acceptance gate:** Adapter smoke felismeri valid és invalid elhelyezést; jagua-rs típusok nem szivárognak át az optimizer publikus modelljébe; f32/f64 konverziós kockázat dokumentált.

**Megjegyzés:** Nem teljes jagua layout API bekötés; elsőként collision/feasibility backend.

### JG-05 — `jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures`

**Phase:** 1 / rectangular sheets  
**Cél:** Rectangular sheet provider és determinisztikus outer-only fixture pack létrehozása.  
**Függőség:** JG-03, JG-04

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/sheet.rs`
- `tests/fixtures/egyedi_solver/jagua_rect_smoke.json`
- `tests/fixtures/egyedi_solver/jagua_rect_medium.json`
- `scripts/smoke_jagua_rectangular_sheet_provider.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md`

**Érintett fókusz:** Sheet expansion, stable sheet_index mapping, small/medium rectangular fixtures, smoke script.

**Acceptance gate:** Több quantity-s stock stabil expanded sheet sorrendet ad; fixture-ök a contract szerint validak; validator PASS.

**Megjegyzés:** Irregular/remnant még tiltott.

### JG-06 — `jagua_optimizer_t06_item_geometry_store_and_rotation_cache`

**Phase:** 1 / item model  
**Cél:** ItemGeometryStore, instance expansion és rotációs cache bevezetése outer-only polygonokra.  
**Függőség:** JG-05

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t06_item_geometry_store_and_rotation_cache.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/io.rs`
- `scripts/smoke_jagua_item_geometry_store.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`

**Érintett fókusz:** Item instance id, area/bbox, allowed rotations, rotated proxy geometry cache; determinisztikus sorrend.

**Acceptance gate:** Ugyanarra az inputra stabil instance list és stabil rotation ordering készül; unsupported rotációk explicit hibát adnak; 0/90/180/270 regresszió nem törik.

**Megjegyzés:** Finomabb rotáció későbbi task; itt még policy-előkészítés.

### JG-07 — `jagua_optimizer_t07_layout_state_and_candidate_model`

**Phase:** 1 / optimizer core  
**Cél:** Optimizer állapotmodell: placed/unplaced, transforms, sheets, candidate moves, score breakdown skeleton.  
**Függőség:** JG-06

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t07_layout_state_and_candidate_model.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/optimizer/state.rs`
- `rust/vrs_solver/src/optimizer/moves.rs`
- `rust/vrs_solver/src/optimizer/score.rs`
- `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`

**Érintett fókusz:** LayoutState, PlacementTransform, CandidateMove, ObjectiveBreakdown; JSON diagnosztika alapjai.

**Acceptance gate:** State unit tesztek PASS; state szerializálható diagnosztikába; output contract továbbra is v1 kompatibilis.

**Megjegyzés:** Még nincs minőségi keresés; csak adatmodell.

### JG-08 — `jagua_optimizer_t08_initial_construction_placer_v1`

**Phase:** 1 / initial placement  
**Cél:** Első saját construction placer: area/bbox rendezés + candidate-point próbák jagua collision checkkel.  
**Függőség:** JG-07, JG-04

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t08_initial_construction_placer_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/initializer.rs`
- `rust/vrs_solver/src/optimizer/candidates.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/main.rs`
- `scripts/smoke_jagua_initial_construction.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`

**Érintett fókusz:** Initializer, basic candidate generation rectangular sheetre, első valid layout létrehozása.

**Acceptance gate:** Small fixture minden partot validan elhelyez; medium fixture legalább részleges, de invalid layout soha nincs ok/partial sikernek hazudva; exact validator PASS a placements-re.

**Megjegyzés:** Ez válthatja a sor/cursor baseline-t feature flag/profile mögött.

### JG-09 — `jagua_optimizer_t09_exact_validation_bridge_and_metrics`

**Phase:** 1 / validation  
**Cél:** A Rust solver output és a Python exact validator/report metrikák zárása: invalid layout ne lehessen sikeres eredmény.  
**Függőség:** JG-08

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t09_exact_validation_bridge_and_metrics.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`
- `scripts/smoke_jagua_exact_validation_bridge.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`

**Érintett fókusz:** Runner meta, metrics, validation smoke; outputban objective/validation fields opcionális bővítés.

**Acceptance gate:** Out-of-sheet/overlap fixture FAIL/unsupported; valid fixture PASS; reportban runtime, placed, unplaced, used_sheets, utilization megjelenik.

**Megjegyzés:** A validator lehet Python/Shapely; a lényeg független végső igazság.

### JG-10 — `jagua_optimizer_t10_repair_search_loop_v1`

**Phase:** 1 / repair search  
**Cél:** Sparrow-elvű repair-search V1: overlap/boundary hibák javítása, move/reinsert/rotate próbákkal.  
**Függőség:** JG-09

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t10_repair_search_loop_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/moves.rs`
- `rust/vrs_solver/src/optimizer/repair.rs`
- `rust/vrs_solver/src/optimizer/stopping.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `scripts/smoke_jagua_repair_search_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`

**Érintett fókusz:** MoveGenerator, RepairEngine, StoppingPolicy; deterministic seed és time budget.

**Acceptance gate:** Repair smoke legalább egy mesterségesen hibás induló állapotot valid állapotra javít; time limit betartott; azonos seed determinisztikus.

**Megjegyzés:** Nem kell még tökéletes kihasználtság, de a javító mechanika működjön.

### JG-11 — `jagua_optimizer_t11_score_model_v1`

**Phase:** 1 / objective  
**Cél:** ScoreModel V1: placed area, unplaced penalty, sheet count, overlap/boundary penalty, compactness proxy.  
**Függőség:** JG-10

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/score.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `docs/egyedi_solver/jagua_optimizer_score_model_v1.md`
- `scripts/smoke_jagua_score_model_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`

**Érintett fókusz:** ObjectiveBreakdown, score weights profile, diagnosztikus output.

**Acceptance gate:** Score breakdown auditálható; invalid layout score-ja mindig rosszabb valid alternatívánál; profile default dokumentált.

**Megjegyzés:** A cél tuningolható súlyrendszer, nem hard-coded magic number káosz.

### JG-12 — `jagua_optimizer_t12_multi_sheet_manager_v1`

**Phase:** 1 / multi-sheet  
**Cél:** MultiSheetManager V1: több rectangular sheet kezelése, sheetenkénti construction/repair, stable ordering.  
**Függőség:** JG-11

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t12_multi_sheet_manager_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/multisheet.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/main.rs`
- `scripts/smoke_jagua_multisheet_manager_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`

**Érintett fókusz:** Sheet assignment, used_sheets számítás, unplaced kezelés, multi-sheet metrics.

**Acceptance gate:** Több sheetes fixture valid; sheet_index contract nem törik; `sheet_count_used` pontos; determinisztikus seed PASS.

**Megjegyzés:** Még nem sheet elimináció; csak stabil multi-sheet alap.

### JG-13 — `jagua_optimizer_t13_sheet_elimination_v1`

**Phase:** 1 / sheet count reduction  
**Cél:** Sheet elimináció V1: leggyengébb sheet ürítése, reinsert más sheetekre, rollback ha romlik.  
**Függőség:** JG-12

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t13_sheet_elimination_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/sheet_elimination.rs`
- `rust/vrs_solver/src/optimizer/multisheet.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `scripts/smoke_jagua_sheet_elimination_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`

**Érintett fókusz:** Weakest sheet selection, reinsert order, rollback snapshot, diagnostics.

**Acceptance gate:** Mesterséges fixture-ben egy sheet eliminálható; sikertelen elimináció rollbackel és nem rontja a valid layoutot; reportban attempt/success/fail metrikák vannak.

**Megjegyzés:** Ipari szempontból ez az egyik legfontosabb minőségi lépés.

### JG-14 — `jagua_optimizer_t14_phase1_benchmark_matrix`

**Phase:** 1 / benchmark gate  
**Cél:** Phase 1 rectangular multi-sheet benchmark matrix: smoke/small/medium/realistic no-hole fixture-ök, összevetés baseline-nal.  
**Függőség:** JG-13

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t14_phase1_benchmark_matrix.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `scripts/bench_jagua_optimizer_phase1_rectangular.py`
- `codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md`

**Érintett fókusz:** Benchmark script, summary JSON/MD, validator gate, baseline compare.

**Acceptance gate:** Minden benchmark validációval zárul; placed/unplaced/used_sheets/utilization/runtime szerepel; FAIL, ha invalid layout PASS-ként jelenik meg.

**Megjegyzés:** Gate 1: Phase 2 csak akkor induljon, ha Phase 1 stabilan valid.

### JG-15 — `jagua_optimizer_t15_irregular_sheet_capability_spike`

**Phase:** 2 / irregular spike  
**Cél:** Kideríteni, hogy a jagua-rs natívan mennyire alkalmas irregular/remnant sheet boundary kezelésre, hole nélkül.  
**Függőség:** JG-14

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t15_irregular_sheet_capability_spike.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs`
- `tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json`
- `scripts/smoke_jagua_irregular_sheet_spike.py`
- `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`

**Érintett fókusz:** Spike bin/script L-alakú és konkáv remnanttal; döntés: natív jagua boundary vagy saját boundary validator + jagua item-item collision.

**Acceptance gate:** Döntési report konkrét PASS/NO-GO ággal; L-shape boundary violation felismerhető; nincs hole kezelés bekeverve.

**Megjegyzés:** Ha natív support nem elég, a terv nem bukik: saját boundary check út marad.

### JG-16 — `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

**Phase:** 2 / irregular provider  
**Cél:** Irregular/remnant sheet provider, usable polygon és margin kezelés hole nélkül.  
**Függőség:** JG-15

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t16_irregular_sheet_provider_and_margin.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/geometry.rs`
- `docs/solver_io_contract.md`
- `tests/fixtures/egyedi_solver/jagua_irregular_margin.json`
- `scripts/smoke_jagua_irregular_sheet_provider.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`

**Érintett fókusz:** SheetGeometry outer polygon, usable polygon, conservative margin, shape metadata.

**Acceptance gate:** L-alakú/remnant sheet input valid; margin utáni usable region dokumentált; túl keskeny remnant unsupported; rectangular regresszió nincs.

**Megjegyzés:** Container holes továbbra is tiltottak.

### JG-17 — `jagua_optimizer_t17_irregular_boundary_validation`

**Phase:** 2 / boundary validation  
**Cél:** Irregular sheet exact/proxy boundary validation integrálása: item nem lóghat ki usable polygonból.  
**Függőség:** JG-16

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t17_irregular_boundary_validation.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/boundary.rs`
- `rust/vrs_solver/src/adapter.rs`
- `vrs_nesting/nesting/instances.py`
- `scripts/smoke_jagua_irregular_boundary_validation.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`

**Érintett fókusz:** Boundary check, validator smoke, invalid fixture.

**Acceptance gate:** Konkáv sheetből kilógó item FAIL; sheeten belüli item PASS; boundary-touch policy dokumentált.

**Megjegyzés:** Validator legyen safe-side, ne legyen túl optimista.

### JG-18 — `jagua_optimizer_t18_irregular_candidate_generation`

**Phase:** 2 / irregular search  
**Cél:** Boundary-aware candidate generation irregular sheetre: interior samples, edge-near, vertex-near, neighbor-near pontok.  
**Függőség:** JG-17

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t18_irregular_candidate_generation.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/candidates.rs`
- `rust/vrs_solver/src/optimizer/initializer.rs`
- `rust/vrs_solver/src/optimizer/repair.rs`
- `scripts/smoke_jagua_irregular_candidate_generation.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`

**Érintett fókusz:** Candidate generator kiterjesztés; deterministic sampling seed; diagnostics.

**Acceptance gate:** Irregular fixture legalább részleges valid elhelyezést ad; candidate count és rejection reason reportolva; determinisztikus seed PASS.

**Megjegyzés:** Itt még nem remnant value model; csak geometriai candidate képesség.

### JG-19 — `jagua_optimizer_t19_remnant_score_model_v1`

**Phase:** 2 / remnant scoring  
**Cél:** Remnant/sheet cost score V1: remnant preferencia, teljes tábla nyitás büntetés, usable-area utilization.  
**Függőség:** JG-18

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t19_remnant_score_model_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `rust/vrs_solver/src/optimizer/score.rs`
- `rust/vrs_solver/src/sheet.rs`
- `docs/egyedi_solver/jagua_remnant_score_model_v1.md`
- `scripts/smoke_jagua_remnant_score_model_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`

**Érintett fókusz:** Score weights bővítése, sheet cost metadata, report breakdown.

**Acceptance gate:** Vegyes rectangular+remnant fixture-ben a score magyarázható sheet választást ad; reportban sheet_cost/utilization breakdown van.

**Megjegyzés:** Nem végleges inventory/costing, csak nesting objective proxy.

### JG-20 — `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

**Phase:** 2 / benchmark gate  
**Cél:** Phase 2 irregular/remnant benchmark matrix hole nélkül.  
**Függőség:** JG-19

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `scripts/bench_jagua_optimizer_phase2_irregular.py`
- `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`

**Érintett fókusz:** Benchmark script, L-shape/remnant/vegye sheet fixture, validator gate.

**Acceptance gate:** Irregular benchmark minden elfogadott layoutja exact validator PASS; rectangular Phase 1 fixture regresszió nincs; invalid boundary layout nem mehet át.

**Megjegyzés:** Gate 2: cavity-prepack csak stabil irregular/rectangular alap után induljon.

### JG-21 — `jagua_optimizer_t21_cavity_prepack_integration_audit`

**Phase:** 3 / cavity audit  
**Cél:** Meglévő cavity-prepack pipeline auditja az új jagua optimizerhez: mi használható, mit kell módosítani.  
**Függőség:** JG-20

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t21_cavity_prepack_integration_audit.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `docs/egyedi_solver/jagua_cavity_prepack_integration_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md`

**Érintett fókusz:** Audit `worker/cavity_prepack.py`, `worker/cavity_validation.py`, result normalizer, smoke_cavity scriptcsalád alapján.

**Acceptance gate:** Report rögzíti: meglévő cavity contract, macro/virtual part mapping, expansion pontok, validation pontok, hiányzó bridge-ek.

**Megjegyzés:** Ez audit task, nem implementáció.

### JG-22 — `jagua_optimizer_t22_cavity_extraction_and_usability_filter`

**Phase:** 3 / cavity model  
**Cél:** Cavity extraction + usability filter contract az új optimizer inputjához: használható hole régiók listázása, nem használhatóak okkódja.  
**Függőség:** JG-21

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t22_cavity_extraction_and_usability_filter.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `worker/cavity_prepack.py`
- `worker/cavity_validation.py`
- `docs/egyedi_solver/jagua_cavity_model_v1.md`
- `scripts/smoke_jagua_cavity_extraction_v1.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md`

**Érintett fókusz:** Cavity metadata, usable polygon, min dimension/area filter, diagnostics.

**Acceptance gate:** Hole metadata nem vész el; usable/ignored cavity count és reason reportolva; Phase 1/2 solver hole nélküli core-ja nem kap nyers hole-os partot.

**Megjegyzés:** Cavity használat még nem kötelező, csak modellezett és auditált.

### JG-23 — `jagua_optimizer_t23_single_child_cavity_prepack_v1`

**Phase:** 3 / cavity prepack v1  
**Cél:** Single-child cavity-prepack: egy kisebb child part behelyezése egy parent cavitybe, macro-part metadata előállítása.  
**Függőség:** JG-22, JG-14

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t23_single_child_cavity_prepack_v1.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `worker/cavity_prepack.py`
- `worker/cavity_validation.py`
- `tests/fixtures/egyedi_solver/jagua_cavity_single_child.json`
- `scripts/smoke_jagua_cavity_single_child_prepack.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md`

**Érintett fókusz:** Candidate child matching, local cavity placement, macro-part quantity delta, report.

**Acceptance gate:** Egy child lokálisan validan bekerül egy cavitybe; child kikerül a globális main solver item listából; macro metadata auditálható.

**Megjegyzés:** Több child/cavity még nem cél.

### JG-24 — `jagua_optimizer_t24_macro_part_expansion_and_final_validation`

**Phase:** 3 / expansion  
**Cél:** Macro-part expansion: parent globális transform + child lokális transform kompozíció, exact final validation.  
**Függőség:** JG-23

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t24_macro_part_expansion_and_final_validation.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `worker/result_normalizer.py`
- `worker/cavity_validation.py`
- `scripts/smoke_jagua_macro_part_expansion.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md`

**Érintett fókusz:** Expansion bridge result_normalizer/cavity_validation felé, quantity consistency, no duplicate/no missing check.

**Acceptance gate:** Expanded layout minden eredeti instance-t pontosan egyszer tartalmaz; child inside cavity PASS; quantity mismatch FAIL; exact validator PASS nélkül nincs sikeres report.

**Megjegyzés:** Ez a Phase 3 legfontosabb biztonsági gate-je.

### JG-25 — `jagua_optimizer_t25_cavity_prepack_main_solver_bridge`

**Phase:** 3 / solver bridge  
**Cél:** Cavity-prepack és jagua optimizer end-to-end összekötése rectangular és irregular sheet alapon.  
**Függőség:** JG-24, JG-20

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t25_cavity_prepack_main_solver_bridge.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/result_normalizer.py`
- `scripts/smoke_jagua_cavity_to_solver_e2e.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md`

**Érintett fókusz:** Prepack -> main solver input -> solve -> expansion -> validation pipeline smoke.

**Acceptance gate:** Rectangular + cavity fixture E2E PASS; irregular + cavity smoke legalább supported/unsupported explicit státuszt ad; geometry loss nincs.

**Megjegyzés:** Ha irregular+cavity túl nagy scope, explicit splitelni JG-25A/JG-25B-re.

### JG-26 — `jagua_optimizer_t26_quality_profiles_and_backend_selection`

**Phase:** 4 / integration  
**Cél:** Új backend/profil bekötése a meglévő strategy/profile rendszerbe: választható jagua optimizer mód.  
**Függőség:** JG-14 vagy JG-20; cavity flags csak JG-25 után

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t26_quality_profiles_and_backend_selection.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/main.py`
- `api/services/run_strategy_resolution.py`
- `docs/how_to_run.md`
- `scripts/smoke_jagua_backend_selection.py`
- `codex/reports/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md`

**Érintett fókusz:** Quality profile registry, worker backend selector, run meta observability, docs/how_to_run.

**Acceptance gate:** Profilból explicit látszik: rectangular_only/irregular/cavity capability; run meta tartalmazza backend nevét, profile-t és capability flags-et; régi backendek nem törnek.

**Megjegyzés:** UI csak később, először backend/workflow igazság.

### JG-27 — `jagua_optimizer_t27_final_benchmark_and_release_closure`

**Phase:** 5 / release gate  
**Cél:** Teljes lánc záró benchmark és release döntési report: Phase 1/2/3 képességek, regressziók, következő irány.  
**Függőség:** JG-26; Phase 3 blokk csak akkor, ha JG-25 kész

**Canvas+YAML+runner package:**

- `canvases/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t27_final_benchmark_and_release_closure.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.verify.log`

**Fő implementációs / dokumentációs outputok a task YAML-ben:**

- `scripts/bench_jagua_optimizer_release_matrix.py`
- `codex/reports/egyedi_solver/jagua_optimizer_release_matrix.md`
- `docs/egyedi_solver/jagua_optimizer_release_decision.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md`

**Érintett fókusz:** Benchmark mátrix, összevetés régi vrs_solver baseline-nal, régi nesting_engine NFP eredményekkel és elérhető etalon reportokkal.

**Acceptance gate:** Döntési report egyértelmű: continue / revise / stop; minden elfogadott layout validator PASS; benchmark logok mentve; ismert hiányosságok nem-blokkoló vagy blokkoló státusszal jelölve.

**Megjegyzés:** Nem marketing report: mérési bizonyíték kell.

---

## 7. Dependency graph

```text
JG-00 -> JG-01 -> JG-02
JG-02 -> JG-03
JG-03 + JG-02 -> JG-04
JG-03 + JG-04 -> JG-05
JG-05 -> JG-06 -> JG-07
JG-07 + JG-04 -> JG-08
JG-08 -> JG-09 -> JG-10 -> JG-11 -> JG-12 -> JG-13 -> JG-14
JG-14 -> JG-15 -> JG-16 -> JG-17 -> JG-18 -> JG-19 -> JG-20
JG-20 -> JG-21 -> JG-22
JG-22 + JG-14 -> JG-23 -> JG-24
JG-24 + JG-20 -> JG-25
JG-14 vagy JG-20 -> JG-26
JG-26 -> JG-27
```

## 8. Critical path

A minimális értelmes út rectangular multi-sheet valid solverig:

```text
JG-00 → JG-01 → JG-02 → JG-03 → JG-04 → JG-05 → JG-06 → JG-07 → JG-08 → JG-09 → JG-10 → JG-11 → JG-12 → JG-13 → JG-14
```

A remnant/irregular út:

```text
JG-14 → JG-15 → JG-16 → JG-17 → JG-18 → JG-19 → JG-20
```

A cavity út:

```text
JG-20 → JG-21 → JG-22 → JG-23 → JG-24 → JG-25
```

A release út:

```text
JG-25 → JG-26 → JG-27
```

Ha gyorsabb tanulás kell, a cavity audit (`JG-21`) párhuzamosítható `JG-15…JG-20` mellett, de implementáció (`JG-22+`) csak Gate 2 után fusson.

---

## 9. Phase gate-ek

### Gate 0 — Scaffold és forrásaudit

Tovább Phase 1 implementációra csak akkor:

- JG-00 task index + master runner kész.
- JG-01 repo/source audit nem talált showstoppert.
- `rust/vrs_solver` jagua dependency és runner út igazolt.
- Scope eldöntve: `rust/vrs_solver` az új jagua custom optimizer munkaterület.

### Gate 1 — Rectangular multi-sheet viability

Tovább irregular/remnant felé csak akkor:

- JG-14 benchmark valid.
- Minden elfogadott layout exact validator PASS.
- Hole-os partok Phase 1 alatt explicit unsupported státuszt kapnak.
- Több sheet stabilan kezelhető.
- Sheet elimináció rollbackkel biztonságos.

### Gate 2 — Irregular/remnant viability

Tovább cavity-prepack implementációra csak akkor:

- JG-20 benchmark valid.
- Rectangular regresszió nincs.
- Irregular boundary violation nem tud PASS-ra futni.
- Margin/usable polygon policy dokumentált.

### Gate 3 — Cavity viability

Tovább production/profile integrációra csak akkor:

- JG-25 E2E cavity bridge valid.
- Macro-part expansion után minden eredeti part instance pontosan egyszer szerepel.
- Child part cavityn belül valid.
- Geometry loss nincs.

### Gate 4 — Release döntés

Release/pilot csak akkor:

- JG-27 benchmark matrix elkészült.
- Ismert hiányosságok blokkoló/nem-blokkoló bontásban szerepelnek.
- A régi útvonalak regressziója dokumentáltan nincs, vagy explicit vállalt.

---

## 10. Első csomagbatch

A következő körben nem érdemes az összes JG-01…JG-27 package-et egyszerre generálni. Első batch:

1. `jagua_optimizer_t00_task_scaffold_and_master_runner`
2. `jagua_optimizer_t01_repo_and_source_audit`
3. `jagua_optimizer_t02_solver_module_scaffold`
4. `jagua_optimizer_t03_outer_only_contract_and_hole_gate`
5. `jagua_optimizer_t04_jagua_adapter_contract_poc`

Indok:

- Ezek zárják le, hogy pontosan mire építünk.
- Még nem kockáztatnak nagy optimizer-diffet.
- A Phase 1 későbbi taskjai csak stabil adapter/contract után legyenek generálva.

---

## 11. Canvas template minden taskhoz

Minden canvas tartalmazza legalább:

```md
# <TASK_SLUG> — <rövid cím>

## 🎯 Funkció
<egyértelmű cél>

## Scope
### Benne van
- ...

### Nincs benne
- ...

## Valós repo-kiindulópontok
- `AGENTS.md`
- `docs/codex/overview.md`
- ...

## Érintett fájlok
- ...

## Végrehajtási terv
- [ ] ...

## DoD
- [ ] ...

## Teszt / verify
- `./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md`

## Kockázat + rollback
- Kockázat: ...
- Mitigáció: ...
- Rollback: ...
```

---

## 12. Runner template minden taskhoz

```md
# <TASK_SLUG> — runner

## Szerep
Senior Rust/Python nesting agent vagy. A repo szabályait szigorúan követed.

## Kötelező olvasnivaló
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/egyedi_solver/<TASK_SLUG>.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_<TASK_SLUG>.yaml`

## Szigorú szabályok
- Csak a YAML outputs listában szereplő fájlokat módosíthatod.
- Nem találhatsz ki nem létező fájlt/parancsot/mezőt.
- Invalid layout nem lehet PASS.
- A végén futtatod: `./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md`.

## Végrehajtás
A YAML `steps` lépéseit sorrendben hajtsd végre.

## Eredmény
- Frissített checklist.
- Frissített report DoD → Evidence Matrixszal.
- Verify log.
```

---

## 13. Stop conditions

Az agent álljon meg és írjon FAIL/BLOCKED reportot, ha:

- a kötelező repo anchor hiányzik;
- `jagua-rs` API nem használható a tervezett adapterhez;
- a task scope-ján túlmutató fájlmódosítás kellene;
- hole-os input Phase 1/2 alatt csak silent drop-pal lenne kezelhető;
- exact validator invalid layoutot talál;
- a repo gate nem futtatható és az ok nem dokumentálható;
- a task túl nagy diffet generálna egy biztonságos review-hoz.

---

## 14. Záró megjegyzés

Ez a bontás szándékosan konzervatív. A cél nem az, hogy egyetlen agent-futásban „átírjuk a solvert”, hanem hogy:

1. először legyen auditált jagua adapter és outer-only rectangular multi-sheet solver;
2. utána jöjjön az irregular/remnant sheet;
3. csak stabil alapra épüljön a cavity-prepack;
4. minden fázis végén legyen exact validation és benchmark gate.

Ez illeszkedik a repo jelenlegi canvas+YAML+runner munkamódszeréhez, és minimalizálja annak kockázatát, hogy a gyorsabb jagua-alapú stratégia közben elveszítsük a DXF/geometriai igazságot.
