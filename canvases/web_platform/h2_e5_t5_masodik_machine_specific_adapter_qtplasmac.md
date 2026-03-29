# H2-E5-T5 masodik machine-specific adapter (QtPlasmaC, optionalis)

## 🎯 Funkcio

Ez a task a mar elkeszult `H2-E5-T4` Hypertherm EDGE Connect adapter utan a
H2 optionalis postprocess ag masodik konkret celgep-csaladjat vezeti be.

A mainline H2 tovabbra is kesz:
- manufacturing truth letrejon,
- snapshotolt manufacturing + postprocessor selection megvan,
- `manufacturing_preview_svg` artifact megvan,
- `manufacturing_plan_json` machine-neutral export megvan,
- az elso machine-specific adapter (`hypertherm_edge_connect`) mar implementalt.

A task celja most:
- a mar meglevo machine-neutral export masodik konkret targetre torteno emitje;
- a jelenlegi egy-targetes adapter service minimalis, stabil kiterjesztese ugy,
  hogy a Hypertherm viselkedes ne torjon;
- egy masodik owner-scoped postprocessor profile/version configgal a
  `linuxcnc_qtplasmac` csalad tamogatasa;
- per-sheet deterministic `machine_program` artifactok eloallitasa;
- a reszletes lead-in/out technologiai rendszer tovabbra se csusszon bele ebbe a taskba.

Ez a task is **optionalis H2 postprocess ag**. A T5 hianya nem minositi vissza a
H2 mainline PASS allapotat.

## 🧠 Fejlesztesi reszletek

### Konkret target befagyasztas

A taskban a masodik konkret celadapter most mar rogzitheto:

- `TARGET_MACHINE_FAMILY`: `linuxcnc_qtplasmac`
- `TARGET_ADAPTER_KEY`: `linuxcnc_qtplasmac`
- `TARGET_OUTPUT_FORMAT`: `basic_manual_material_rs274ngc`
- `TARGET_LEGACY_ARTIFACT_TYPE`: `linuxcnc_qtplasmac_basic_manual_material`
- `TARGET_ARTIFACT_KIND`: `machine_program`

Fontos:
- ez **nem** multi-tool / scribe / spotting adapter;
- ez **nem** automatic material change (`M190`/`M66`) adapter;
- az elso prototipus a **basic manual-material QtPlasmaC** irany;
- a task nem vallalja a teljes LinuxCNC / QtPlasmaC technologiai tudastar
  lemodellezeset.

### Scope

Benne van:
- a mar meglevo `api/services/machine_specific_adapter.py` service minimalis,
  visszafele kompatibilis kiterjesztese ket-targetes dispatchra;
- a Hypertherm target teljes megtartasa regresszio nelkul;
- dedikalt QtPlasmaC emitter ag ugyanabban a service-ben vagy ugyanazon modulon
  belul elkulonitett emitter-fuggvenyekkel;
- owner-scoped runhoz a `manufacturing_plan_json` artifact beolvasasa;
- snapshotolt postprocessor selection ellenorzese (`adapter_key`,
  `output_format`, `schema_version`);
- a kapcsolt `config_jsonb` szukitett boundary szerinti alkalmazasa;
- a `manufacturing_plan_json`-ban levo `plan_id` + `contour_index` alapjan
  `run_manufacturing_contours` / `geometry_derivatives` lookup a canonical
  manufacturing konturpontok feloldasahoz;
- per-sheet `machine_program` artifact generalas QtPlasmaC-hez;
- deterministic filename / content hash / storage path policy;
- task-specifikus smoke, amely a Hypertherm target regressziojat is ellenorzi.

Nincs benne:
- uj lead-in/out rendszer vagy technology pack modell;
- `cut_rule_sets`, `cut_contour_rules`, contour classification vagy
  `manufacturing_plan_builder` ujratervezese;
- globalis adapter-plugin framework vagy altalanos registry-rendszer;
- worker auto-trigger, queue hook vagy frontend export UI;
- `machine_ready_bundle` zip;
- globalis SQL seed a postprocessor profilokra;
- manufacturing truth tablaba vagy postprocessor truth tablaba torteno visszairas.

### Miert nincs SQL seed migration?

A `postprocessor_profiles` es `postprocessor_profile_versions` owner-scoped truth.
Ezert ebben a taskban **nem** szabad globalis migrationnel demo/prototype
QtPlasmaC profilt seedelni ismeretlen owner ala.

A konkret target baseline:
- smoke fixture-ben;
- reportban;
- es az adapter service altal elvart valid config szerzodesben
jelenjen meg, nem pedig globalis adatseedkent.

### Talalt relevans fajlok

- `AGENTS.md`
  - output szabaly, verify wrapper, valos repo elv.
- `docs/codex/overview.md`
  - canvas/yaml workflow, repo gate, kotelezo artefaktok.
- `docs/codex/yaml_schema.md`
  - csak `steps` schema hasznalhato.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H2-E5 optionalis postprocess ag helye; ide kell rogzitve megjelenjen a T5.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - postprocessor kulon modul, machine-neutral export utan adapter reteg.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - H2 optionalis adapter-ag helyes kezelese.
- `api/services/machine_specific_adapter.py`
  - a jelenlegi Hypertherm-only implementacio, amelyet minimalisan ket-targetesse
    kell boviteni.
- `scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`
  - a jelenlegi target-specific smoke minta.
- `api/services/postprocessor_profiles.py`
  - version-level `adapter_key`, `output_format`, `schema_version`, `config_jsonb`.
- `api/services/run_snapshot_builder.py`
  - snapshotolt postprocessor selection szerkezete.
- `api/services/machine_neutral_exporter.py`
  - a gepfuggetlen export forrasa es current contractja.
- `api/services/manufacturing_plan_builder.py`
  - `run_manufacturing_contours` truth, `geometry_derivative_id`, lead descriptorok.
- `api/services/geometry_derivative_generator.py`
  - `manufacturing_canonical` derivative payload szerkezete (`contours[].points`).
- `worker/sheet_dxf_artifacts.py`
  - per-sheet artifact naming + hash + storage path minta.
- `api/routes/runs.py`
  - generic artifact list/download a `metadata_jsonb` alapjan.
- `api/supabase_client.py`
  - signed download + object letoltes helper a `manufacturing_plan_json`
    artifact beolvasasahoz.

### Fo boundary-k

#### 1. A primer adapter-bemenet a `manufacturing_plan_json` artifact
A service a runhoz tartozo persisted `manufacturing_plan_json` artifactot keresi meg
es annak payloadjabol indul ki.

Tilos:
- live `project_manufacturing_selection` olvasasa;
- raw solver output vagy run-dir olvasasa;
- `manufacturing_preview_svg` parse-olasa;
- worker stdout/stderr vagy preview artifact alapjan emitet generalni.

#### 2. Canonical geometry lookup csak feloldas, nem alternativ truth
A `manufacturing_plan_json` payload a sheet/plan/contour strukturat adja.
A gep-specifikus emitter a geometriai pontokat owner-scoped modon,
a payloadban szereplo `plan_id` + `contour_index` alapjan oldhatja fel innen:
- `run_manufacturing_contours.geometry_derivative_id`
- `geometry_derivatives.derivative_jsonb` (`manufacturing_canonical`)

Ez **nem** live selection fallback, hanem persisted manufacturing truth feloldas.
A service nem kerulheti meg a `manufacturing_plan_json`-t es nem olvashat kozvetlen
upstream manufacturing selectiont vagy raw solver outputot.

#### 3. A `config_jsonb` szukitett adapter-boundary marad
A QtPlasmaC adapter sem tolhat vissza technologiai packot a postprocessor configba.
A taskban csak ezek a blokkok ertelmezhetok:
- `program_format`
- `motion_output`
- `coordinate_mapping`
- `command_map`
- `lead_output`
- `artifact_packaging`
- `capabilities`
- `fallbacks`
- `export_guards`
- opcionálisan `process_mapping`

Tilos ide visszacsempeszni:
- material/thickness technology packot;
- feed / kerf / pierce parameter konyvtarat;
- contour-level manufacturing policyt;
- cut-order policyt;
- uj lead strategiat.

#### 4. Basic manual-material QtPlasmaC target boundary
A task basic QtPlasmaC adaptert vezet be.

Benne van:
- standard G-code mozgás (`rapid`, `linear`, `arc_cw`, `arc_ccw`) a
  `config_jsonb.command_map` szerint;
- basic cut start/stop mapping;
- manual-material workflow, vagyis a material kiválasztást a file nem kotelezoen
  automatizalja.

Nincs benne:
- `M190` automatic material select es a kapcsolt `M66` wait workflow;
- THC override, feed override, hole rule vagy egyeb process-makro logika;
- multi-tool, scribe, spot, router vagy megemelt Z-motion policy.

#### 5. Nincs uj artifact kind
A task tovabbra sem vezet be uj `artifact_kind` enumot.
A gep-specifikus kimenet a mar meglevo:
- `artifact_kind='machine_program'`
vilagot hasznalja.

A QtPlasmaC target megkulonboztetese a `metadata_jsonb`-ben tortenjen:
- `legacy_artifact_type='linuxcnc_qtplasmac_basic_manual_material'`;
- `adapter_key='linuxcnc_qtplasmac'`;
- `output_format='basic_manual_material_rs274ngc'`.

#### 6. Determinizmus es idempotencia
A generalt artifactok:
- ugyanarra a `manufacturing_plan_json` truthra ugyanazt a content hash-et adjak;
- determinisztikus sheet-sorrendet hasznaljanak;
- stabil filename es storage path policy-t kovessenek, peldaul:
  `projects/{project_id}/runs/{run_id}/machine_program/linuxcnc_qtplasmac/{sha256}.ngc`.

Ujrageneralaskor ugyanazon run + same-target kombinal ne maradjon duplikalt,
elozo QtPlasmaC target artifact.

#### 7. Minimalis architekturalis irany: ket-targetes dispatch, nem plugin-framework
A jelenlegi egy-targetes service-t minimalisan bovitsuk ugy, hogy:
- a Hypertherm target teljesen megmaradjon;
- a masodik targethez dedikalt emitter-ag jojjon letre;
- a dispatch alapja a snapshotolt `adapter_key` + `output_format` legyen.

De **nem** cel:
- altalanos adapter plugin rendszer;
- dinamikus import registry;
- admin-szintu adapter modulkereso keretrendszer.

A cel a minimalis, auditálhato, ket-targetes bovitmeny.

## ✅ Definition of Done

- A task explicit targetet rogzit: `linuxcnc_qtplasmac` /
  `basic_manual_material_rs274ngc`.
- A roadmapban is megjelenik, hogy ez a H2 optionalis postprocess ag masodik
  adapter-taskja.
- A `machine_specific_adapter.py` a Hypertherm target regresszio nelkul tamogatja a
  QtPlasmaC targetet is.
- A primer bemenet tovabbra is a persisted `manufacturing_plan_json` artifact.
- A canonical geometry feloldas tovabbra is csak a persisted manufacturing truth
  tabla-lancbol tortenik.
- A QtPlasmaC emitter per-sheet `machine_program` artifactokat general.
- A QtPlasmaC artifact metadata kitolti a target-specifikus legacy type-ot.
- A storage path es filename deterministic.
- A task nem vezet be uj artifact kindot.
- A task nem vezet be globalis SQL seed migrationt.
- A task nem ir manufacturing truth vagy postprocessor truth tablaba.
- A task nem vezet be `M190`/`M66` material auto-change workflowt.
- A task nem tervez uj lead-in/out rendszert.
- A smoke script ellenorzi a QtPlasmaC pozitiv utat, a Hypertherm regressziot,
  es a dispatch boundary-ket.
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
  lefut.

## 🧪 Ellenorzesi minimum

- `./scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py`
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`

## 📦 Erintett / letrehozando fajlok

- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `canvases/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.yaml`
- `codex/prompts/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac/run.md`
- `api/services/machine_specific_adapter.py`
- `scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py`
- `codex/codex_checklist/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
- `codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md`
