PASS

## 1) Meta

* **Task slug:** `egyedi_solver_backlog`
* **Kapcsolódó canvas:** `canvases/egyedi_solver_backlog.md`
* **Kapcsolódó goal YAML:** `NINCS: codex/goals/canvases/fill_canvas_egyedi_solver_backlog.yaml` *(run #1-ben nem készült goal YAML)*
* **Futás dátuma:** `2026-02-12T18:56:43+01:00`
* **Branch / commit:** `main@b9e7f2f`
* **Fókusz terület:** `Docs | Planning | Mixed`

## 2) Scope

### 2.1 Cél

- Onboarding szabályok és sémák felderítése a repo standard alapján.
- A kért `tmp/egyedi_solver/*` dokumentumok feldolgozása.
- Valós kód belépési pontok feltérképezése táblás solver integrációhoz.
- P0-P3 backlog összeállítása task-címmel, sluggal, DoD-val, kockázatokkal.

### 2.2 Nem-cél (explicit)

- Funkcionális implementáció készítése.
- P0 taskokhoz külön canvas+yaml párok elkészítése.
- Sparrow pipeline logika átírása.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

* `canvases/egyedi_solver_backlog.md`
* `codex/reports/egyedi_solver_backlog.md`
* `codex/codex_checklist/egyedi_solver_backlog.md`
* `codex/reports/egyedi_solver_backlog.verify.log` *(auto, verify.sh)*

### 3.2 Miért változtak?

- A canvas rögzíti a run célját, scope-ját és a backlog rövid összefoglalóját.
- A report tartalmazza az onboarding kivonatot, evidence-listát és a részletes P0-P3 backlogot.
- A checklist auditálható DoD pontokban zárja a run-t.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver_backlog.md` -> `PASS`

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-12T18:58:32+01:00 → 2026-02-12T18:59:41+01:00 (69s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver_backlog.verify.log`
- git: `main@b9e7f2f`
- módosított fájlok (git status): 4

**git status --porcelain (preview)**

```text
?? canvases/egyedi_solver_backlog.md
?? codex/codex_checklist/egyedi_solver_backlog.md
?? codex/reports/egyedi_solver_backlog.md
?? codex/reports/egyedi_solver_backlog.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) Onboarding kivonat (kötelező szabályok)

### 5.1 Kötelező canvas szekciók

Forrás: `docs/codex/prompt_template.md` (6.2 Canvas létrehozása)

- `🎯 Funkció`
- `🧠 Fejlesztési részletek`
- `🧪 Tesztállapot`
- `🌍 Lokalizáció`
- `📎 Kapcsolódások`

### 5.2 Goal YAML `steps` séma

Forrás: `docs/codex/yaml_schema.md` (1) Elfogadott séma)

```yaml
steps:
  - name: "<lépés neve>"
    description: >
      <részletes, végrehajtható utasítások>
    outputs:
      - "<fájl útvonal>"
```

Megkötések:
- Minden módosított/létrehozott fájl szerepeljen valamelyik step `outputs` listájában.
- A legutolsó step kötelezően repo gate (`./scripts/verify.sh --report ...`).

## 6) Evidence / Inputs

### 6.1 Kötelezően kért dokumentumok (determinista sorrend)

- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md` (FOUND)
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md` (FOUND)
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md` (FOUND)
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md` (FOUND)

Fallback `docs/...` keresés nem kellett, mert mind a 4 fájl létezik.

### 6.2 Releváns kód belépési pontok (path + rövid megjegyzés)

- `scripts/check.sh`: jelenlegi repo gate belépési pont; Sparrow build + smoketest futtatás.
- `scripts/run_sparrow_smoketest.sh`: Sparrow futás runneren keresztül, majd IO validáció.
- `vrs_nesting/runner/sparrow_runner.py`: run artifact kezelés (`runs/<run_id>`), determinisztikus runner minta.
- `scripts/validate_sparrow_io.py`: jelenlegi validátor csak Sparrow IO contractra.
- `scripts/verify.sh`: report AUTO_VERIFY blokkot és `.verify.log`-ot kezeli.
- `.github/workflows/sparrow-smoketest.yml`: CI gate jelenleg Sparrow-smoketestre épül.
- `docs/sparrow_modul/sparrow_runner_modul_komplett_dokumentacio.md`: multi-sheet wrapper későbbi szerepe dokumentált, de külön modul még nincs.

### 6.3 Hiányzó elemek (`NINCS:`)

- NINCS: `vrs_nesting/cli.py`
- NINCS: `vrs_nesting/project/model.py`
- NINCS: `vrs_nesting/dxf/importer.py`
- NINCS: `vrs_nesting/geometry/polygonize.py`
- NINCS: `vrs_nesting/geometry/clean.py`
- NINCS: `vrs_nesting/geometry/offset.py`
- NINCS: `vrs_nesting/nesting/instances.py`
- NINCS: `vrs_nesting/runner/vrs_solver_runner.py`
- NINCS: `vrs_nesting/validate/solution_validator.py`
- NINCS: `vrs_nesting/dxf/exporter.py`
- NINCS: `vrs_nesting/run_artifacts/run_dir.py`
- NINCS: `rust/vrs_solver`
- NINCS: `docs/solver_io_contract.md`
- NINCS: `docs/mvp_project_schema.md`
- NINCS: `scripts/validate_nesting_solution.py`
- NINCS: `.github/workflows/nesttool-smoketest.yml`
- NINCS: `samples/project_rect_1000x2000.json`

## 7) Részletes backlog (P0-P3)

| Task title | TASK_SLUG | Prioritás | Rövid indoklás | Érintett modulok/fájlok | DoD (pipálható) | Kockázat + mitigáció |
| --- | --- | --- | --- | --- | --- | --- |
| Projekt séma + CLI skeleton + run artifact alap | `project_schema_and_cli_skeleton` | P0 | Nélkülözhetetlen minimum belépési pont és determinisztikus futási váz hiányzik. | `NINCS: vrs_nesting/cli.py`; `NINCS: vrs_nesting/project/model.py`; `NINCS: vrs_nesting/run_artifacts/run_dir.py`; `NINCS: docs/mvp_project_schema.md` | [ ] `python3 -m vrs_nesting.cli run <project.json>` belépő működik; [ ] project validáció determinisztikus hibával; [ ] run snapshot létrejön `runs/<run_id>/project.json`; [ ] minimál run log íródik | Kockázat: túl tág project schema. Mitigáció: MVP mezőlista fagyasztása + strict validáció. |
| Solver IO contract + runner integrációs réteg | `solver_io_contract_and_runner` | P0 | Stabil szerződés nélkül a solver cserélhetősége és validáció szétesik. | `NINCS: docs/solver_io_contract.md`; `NINCS: vrs_nesting/runner/vrs_solver_runner.py`; referenciák: `vrs_nesting/runner/sparrow_runner.py` | [ ] `solver_input.json`/`solver_output.json` schema dokumentált; [ ] runner bin-feloldás + log mentés; [ ] non-zero exit diagnosztika; [ ] input hash és seed riportálás | Kockázat: korai contract churn. Mitigáció: verziózott mezőstruktúra + backward kompat táblázat a doksiban. |
| Táblás MVP solver + multi-sheet ciklus | `table_solver_mvp_multisheet` | P0 | A core funkcionalitás maga hiányzik; ez oldja a strip slicing problémát. | `NINCS: rust/vrs_solver`; `NINCS: vrs_nesting/nesting/instances.py`; `feltárandó`: Python/Rust orchestration határ | [ ] instance-szintű placement kimenet; [ ] táblahatár-hűség (no overflow); [ ] multi-sheet iteráció működik; [ ] `PART_NEVER_FITS_STOCK` diagnosztika | Kockázat: túl lassú candidate keresés. Mitigáció: determinisztikus pruning + időlimit kezelése. |
| Táblás validátor + smoke gate | `nesting_solution_validator_and_smoke` | P0 | Nincs minőségkapu a jövőbeli táblás kimenetre. | `NINCS: scripts/validate_nesting_solution.py`; `NINCS: .github/workflows/nesttool-smoketest.yml`; `scripts/check.sh` (integrációs pont) | [ ] validator ellenőrzi in-bounds/hole/no-overlap/rotation; [ ] új smoke fut local + CI; [ ] failure artifact mentés; [ ] verify report evidenciával PASS | Kockázat: CI instabil függőség miatt. Mitigáció: pinned toolchain + reprodukálható minta projekt. |
| DXF export sheet-enként (MVP) | `dxf_export_per_sheet_mvp` | P0 | Gyártási kimenet nélkül a solver nem használható. | `NINCS: vrs_nesting/dxf/exporter.py`; `NINCS: samples/project_rect_1000x2000.json` | [ ] `runs/<run_id>/out/sheet_001.dxf` létrejön; [ ] placement transzform helyes; [ ] üres sheet nem exportálódik; [ ] export report tartalmaz sheet metrikát | Kockázat: eltérő DXF entitáskezelés. Mitigáció: korlátozott MVP layer-konvenció + golden minták. |
| DXF import konvenciók + clean pipeline | `dxf_import_convention_layers` | P1 | Stabil import nélkül hibás geometriára fut a solver. | `NINCS: vrs_nesting/dxf/importer.py`; `NINCS: vrs_nesting/geometry/clean.py`; referencia: `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md` | [ ] `CUT_OUTER`/`CUT_INNER` kezelés; [ ] nyitott kontúr hibaüzenet; [ ] part+holes normalizált output; [ ] import unit teszt | Kockázat: piszkos DXF-ek. Mitigáció: hibatípusonként explicit validation report. |
| Polygonize + offset robusztusság | `geometry_offset_robustness` | P1 | Spacing/margin stabilitás nélkül valid placement sem értelmezhető. | `NINCS: vrs_nesting/geometry/polygonize.py`; `NINCS: vrs_nesting/geometry/offset.py` | [ ] arc/spline feldolgozás toleranciával; [ ] part outset + stock inset szabály; [ ] degeneráció figyelmeztetés; [ ] regressziós tesztek | Kockázat: vékony fal összeomlás offsetnél. Mitigáció: min feature sanity check + debug export. |
| Rotáció policy + instance regresszió | `rotation_policy_and_instance_regression` | P1 | Gyártási szabályok és darabszám-kezelés kritikus correctness tengely. | `NINCS: vrs_nesting/nesting/instances.py`; `NINCS: vrs_nesting/validate/solution_validator.py` | [ ] `instance_id` stabil generálás; [ ] per-part rotáció policy enforced; [ ] regressziós teszt [0,180] policy-ra; [ ] duplicate instance tiltás | Kockázat: policy eltérés solver és validátor között. Mitigáció: közös contract mező + közös fixture. |
| Determinizmus + időkeret enforcement | `determinism_and_time_budget` | P1 | Reprodukálhatóság és futási SLA nélkül CI-ben ingadozó output várható. | `NINCS: rust/vrs_solver`; `NINCS: vrs_nesting/runner/vrs_solver_runner.py`; referencia: `vrs_nesting/runner/sparrow_runner.py` | [ ] azonos seed azonos hash-t ad; [ ] time_limit után unplaced korrekt; [ ] run meta tartalmaz seed/duration; [ ] teszt lefedi timeout ágat | Kockázat: floating nondeterminizmus. Mitigáció: stable sort + kvantált candidate tie-break. |
| Preview + debug export | `preview_and_debug_exports` | P2 | Hibakeresés és gyors validáció fejlesztői hatékonyságát javítja. | `NINCS: vrs_nesting/dxf/exporter.py`; `feltárandó`: preview modulhely | [ ] SVG/PNG preview generálás opcionális; [ ] debug overlay (stock + parts); [ ] run report linkeli preview fájlokat | Kockázat: vizuális félrevezetés skálázás miatt. Mitigáció: unit-converted koordináta teszt. |
| Candidate generálás tuning | `candidate_generation_tuning` | P2 | A kihasználtság javítása az MVP correctness után következő lépés. | `NINCS: rust/vrs_solver/src/heuristics/candidates.rs` | [ ] baseline vs tuned metrika összevetés; [ ] determinisztikus candidate limit; [ ] futásidő regresszió nincs | Kockázat: lassulás jobb fill árán. Mitigáció: feature flag + benchmark threshold. |
| Unplaceable diagnosztika és user-facing hiba | `failure_diagnostics_for_unplaceable_parts` | P2 | Gyors operatív döntéshez kell érthető diagnózis. | `NINCS: scripts/validate_nesting_solution.py`; `NINCS: vrs_nesting/cli.py` | [ ] `PART_NEVER_FITS_STOCK` oklista; [ ] top-N bbox riport; [ ] diagnózis bekerül report.json-be | Kockázat: fals negatív diagnózis. Mitigáció: validator cross-check. |
| Haladó objective + metaheurisztika | `advanced_objective_and_metaheuristics` | P3 | Nice-to-have optimalitás, nem blokkolja MVP használhatóságot. | `NINCS: rust/vrs_solver/src/heuristics/scoring.rs`; `NINCS: rust/vrs_solver/src/heuristics/mod.rs` | [ ] objective konfigurálható; [ ] local search opcionális; [ ] baseline javulás dokumentált | Kockázat: komplexitásrobbanás. Mitigáció: külön feature branch + benchmark gate. |
| Vegyes stock választás és prioritás | `mixed_stock_selection` | P3 | Későbbi maradéklemez-felhasználás optimalizáció. | `NINCS: vrs_nesting/project/model.py`; `NINCS: rust/vrs_solver` | [ ] több stock típus inputban; [ ] stock választási stratégia dokumentált; [ ] minta futás több stockkal | Kockázat: keresési tér drasztikusan nő. Mitigáció: greedy stock prefilter. |
| Interaktív report kiterjesztés | `interactive_reporting_extensions` | P3 | Operatív visszacsatolás és átláthatóság javítása. | `feltárandó`: report renderer útvonal; referencia: `codex/reports/*.md` | [ ] report.json + markdown összhang; [ ] sheet-szint metrikák és unplaced okok; [ ] artifact linkelés | Kockázat: formátum drift. Mitigáció: schema-validate report output. |

## 8) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
| --- | ---: | --- | --- | --- |
| #1 Onboarding források felderítve és összefoglalva | PASS | `AGENTS.md`; `docs/codex/overview.md`; `docs/codex/yaml_schema.md`; `docs/codex/report_standard.md`; `docs/codex/prompt_template.md`; `codex/prompts/task_runner_prompt_template.md` | A report 5. fejezete tartalmazza a kötelező canvas szekciókat és a YAML `steps` sémát. | Kézi felderítés + report evidence |
| #2 Kért 4 db `tmp/egyedi_solver` dokumentum beolvasva | PASS | `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`; `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`; `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`; `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md` | Mind a négy fájl `FOUND`, fallback nem szükséges. | Kézi felderítés |
| #3 Releváns kód belépési pontok listázva | PASS | `scripts/check.sh`; `scripts/run_sparrow_smoketest.sh`; `vrs_nesting/runner/sparrow_runner.py`; `scripts/verify.sh`; `.github/workflows/sparrow-smoketest.yml`; `scripts/validate_sparrow_io.py` | A report 6.2 pontja konkrét path + rövid szerep szerint listázza az integrációs pontokat. | Kézi felderítés |
| #4 P0-P3 backlog elkészült részletes task adatokkal | PASS | `codex/reports/egyedi_solver_backlog.md` | A 7. fejezet minden tasknál tartalmaz címet, slugot, prioritást, indoklást, DoD-t és kockázat/mitigációt. | Kézi ellenőrzés |
| #5 Hiányzó elemek explicit `NINCS:` jelöléssel rögzítve | PASS | `codex/reports/egyedi_solver_backlog.md` | A 6.3 pontban explicit `NINCS:` lista szerepel a hiányzó modulokról/doksikról. | Kézi ellenőrzés |
| #6 Kötelező verify wrapper lefut és log készül | PASS | `codex/reports/egyedi_solver_backlog.verify.log` | A verify wrapper lefutott, a log létrejött, az AUTO_VERIFY blokk PASS állapotot mutat. | `./scripts/verify.sh --report codex/reports/egyedi_solver_backlog.md` |

## 9) Advisory notes (nem blokkoló)

- A backlog erősen függ a tervezett `rust/vrs_solver` létrehozásától; ez jelenleg teljesen hiányzó komponens.
- A meglévő gate kizárólag Sparrow-smoketestre optimalizált, ezért a táblás pipeline bevezetésekor külön CI gate szükséges.
- A dokumentációs tervek több helyen javasolt fájlokat említenek, de ezek túlnyomó többsége még nem létezik a repóban.
