# Report — h2_e5_t4_elso_machine_specific_adapter

**Status:** BLOCKED

## 1) Meta

* **Task slug:** `h2_e5_t4_elso_machine_specific_adapter`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml`
* **Futtas datuma:** 2026-03-24
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Scripts

## 2) Scope

### 2.1 Cel
- A `config_jsonb` elso valos alkalmazasi pontja: a mar letezo `manufacturing_plan_json` artifact + snapshotolt postprocessor selection + version-level `config_jsonb` konkret, egycelu adapter-oldali alkalmazasa.
- Pontosan egy konkret celgep-csaladra irt adapter implementalasa.
- Machine-ready artifact eloallitasa a `run_artifacts` retegen.

### 2.2 Nem-cel (explicit)
- Uj lead-in/out rendszer vagy technology pack.
- `cut_rule_sets`, `cut_contour_rules`, contour classification atirasa.
- Live `project_manufacturing_selection` olvasasa exporthoz.
- Tobb adapteres plugin-rendszer altalanositasa.
- Frontend/export UI redesign.

## 3) BLOCKED indoklas

A canvas explicit STOP szabalya szerint a task implementacioja csak akkor inditthato, ha az alabbi harom mezo konkretan rogzitesre kerult:

| Mezo | Elvaras | Jelenlegi allapot |
| --- | --- | --- |
| `TARGET_MACHINE_FAMILY` | konkret celgep-csalad | **TODO** |
| `TARGET_ADAPTER_KEY` | konkret adapter kulcs | **TODO** |
| `TARGET_OUTPUT_FORMAT` | konkret kimeneti formatum | **TODO** |

Mindharom mezo `TODO` allapotban van. A canvas es a run.md szerint tilos celgep-csaladot, dialektust vagy adapter-kulcsot kitalalni. A task BLOCKED allapotban marad, amig ezek az ertekek rogzitesre nem kerulnek.

### Elkeszult artefaktok (Step 1)
A task dokumentacios artefaktlanca elkeszult:
- `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml`
- `codex/prompts/web_platform/h2_e5_t4_elso_machine_specific_adapter/run.md`
- `codex/codex_checklist/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
- `codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`

### Nem indithato lepesek (Step 2-4)
Az alabbi lepesek a BLOCKED allapot miatt nem indultak:
- Migration + adapter service implementacio (Step 2)
- Task-specifikus smoke script (Step 3)
- Repo gate (Step 4)

## 4) Verifikacio

### 4.1 Kotelezo parancs
* Nem futtatva — a task BLOCKED, implementacio nem tortent.

### 4.2 Opcionalis parancsok
* Nem relevans BLOCKED allapotban.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo teszt |
| -------- | ------: | ---------- | ---------- | ---------------- |
| #1 Optionalis adapter-ag, nem H2 blocker | N/A | `h2_lezarasi_kriteriumok_es_h3_entry_gate.md` section 3 | H2-E5-T4 a task tree-ben `(opcionalis)` jelolessel | — |
| #2 `manufacturing_plan_json` artifact alapu | BLOCKED | — | TARGET mezok hianyoznak | — |
| #3 Konkret target adapter rogzitve | BLOCKED | canvas `TARGET_*` = TODO | Nincs rogzitett celgep-csalad | — |
| #4 `config_jsonb` boundary enforce | BLOCKED | — | Implementacio nem indult | — |
| #5 Nincs uj lead-in/out rendszer | BLOCKED | — | Implementacio nem indult | — |
| #6 Csak `run_artifacts` bovites | BLOCKED | — | Implementacio nem indult | — |
| #7 Smoke script | BLOCKED | — | Implementacio nem indult | — |
| #8 verify.sh PASS | BLOCKED | — | Implementacio nem indult | — |

## 8) Advisory notes

- A H2-E5-T4 task optionalis ag; a H2 mainline closure PASS feltetelei kozott NEM szerepel.
- A task dokumentacios artefaktlanca (canvas, YAML, prompt, checklist, report) elkeszult, igy a task barmikor felveheto, amint egy konkret celgep-csalad igeny megalapozotta valik.
- A machine-neutral export (H2-E5-T3) a stabil kimeneti interfesz, amelyre az adapter epulhet.
- A `config_jsonb` szukitett boundary-ja (program_format, motion_output, coordinate_mapping, command_map, lead_output, artifact_packaging, capabilities, fallbacks, export_guards) a canvasban rogzitett.

## 9) Follow-ups

- Konkret `TARGET_MACHINE_FAMILY` / `TARGET_ADAPTER_KEY` / `TARGET_OUTPUT_FORMAT` rogzitese, amint uzleti igeny rogziti a celgep-csaladot.
- A BLOCKED feloldasa utan a YAML Step 2-4 vegrehajtasa.
