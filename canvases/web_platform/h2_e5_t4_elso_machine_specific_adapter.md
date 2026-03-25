# H2-E5-T4 elso machine-specific adapter

## 🎯 Funkcio

Ez a task a H2 postprocess ag elso valos, konkret celgepre irt adaptere.
A mainline H2 mar kesz:
- manufacturing truth letrejon,
- a manufacturing snapshot es plan builder mukodik,
- a `manufacturing_preview_svg` artifact megvan,
- a `manufacturing_plan_json` machine-neutral export megvan,
- a postprocessor profile/version domain aktiv.

Innen a kovetkezo lepés mar nem uj manufacturing truth, hanem a mar kesz,
persisted export **gep-specifikus emitje**.

A task celja:

- pontosan **egy** konkret celgep-csaladot tamogato adapter;
- bemenetkent a mar meglevo `manufacturing_plan_json` artifact;
- snapshotolt postprocessor selection + `postprocessor_profile_versions.config_jsonb`
  alkalmazasa;
- per-sheet, deterministic `machine_program` artifactok eloallitasa;
- a postprocessor modul kulon boundary-n maradjon;
- a reszletes lead-in/out technologiai rendszer tovabbra se csusszon bele ebbe a taskba.

Ez a task tovabbra is **opcionalis H2 ag**. A T4 hianya nem minositi vissza a H2
mainline PASS allapotat.

## 🧠 Fejlesztesi reszletek

### Konkret target befagyasztas

A task indithato, mert a konkret celadapter most mar rogzitheto:

- `TARGET_MACHINE_FAMILY`: `hypertherm_edge_connect`
- `TARGET_ADAPTER_KEY`: `hypertherm_edge_connect`
- `TARGET_OUTPUT_FORMAT`: `basic_plasma_eia_rs274d`
- `TARGET_LEGACY_ARTIFACT_TYPE`: `hypertherm_edge_connect_basic_plasma_eia`
- `TARGET_ARTIFACT_KIND`: `machine_program`

Fontos:
- itt **nem** XPR embedded-process adapterrol van szo;
- az elso prototipus az EDGE Connect basic plasma EIA/RS-274D irany;
- a task ettol meg nem vallalja a teljes Hypertherm technologiatudastar lemodellezeset.

### Scope

Benne van:
- dedikalt `api/services/machine_specific_adapter.py` service;
- owner-scoped runhoz a `manufacturing_plan_json` artifact beolvasasa;
- a snapshotolt postprocessor selection ellenorzese (`adapter_key`, `output_format`,
  `schema_version`);
- a kapcsolt `config_jsonb` szukitett boundary szerinti alkalmazasa;
- a `manufacturing_plan_json`-ban levo `plan_id` + `contour_index` alapjan
  `run_manufacturing_contours` / `geometry_derivatives` lookup a canonical
  manufacturing konturpontok feloldasahoz;
- per-sheet `machine_program` artifact generalas;
- deterministic filename / content hash / storage path policy;
- task-specifikus smoke.

Nincs benne:
- uj lead-in/out rendszer vagy technology pack modell;
- `cut_rule_sets`, `cut_contour_rules`, contour classification vagy
  `manufacturing_plan_builder` ujratervezese;
- globalis adapter-plugin framework vagy multi-adapter registry;
- worker auto-trigger, queue hook vagy frontend export UI;
- `machine_ready_bundle` zip;
- globalis SQL seed a postprocessor profilokra;
- manufacturing truth tablaba vagy postprocessor truth tablaba torteno visszairas.

### Miert nincs SQL seed migration?

A `postprocessor_profiles` es `postprocessor_profile_versions` owner-scoped truth.
Ezert ebben a taskban **nem** szabad globalis migrationnel "demo" profilt seedelni
ismeretlen owner ala.

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
  - H2-E5-T4 optionalis celgép-csalad adapter.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - postprocessor kulon modul, machine-neutral export utan adapter reteg.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - a H2-E5-T4 optionalis, nem H2 blocker.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - postprocess = kulon modul; bemenet a manufacturing plan + postprocessor profile.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - worker/export oldalon snapshot-first es persisted truth elv.
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
A service nem kerulheti meg a `manufacturing_plan_json` artifactot.

#### 3. A `config_jsonb` csak szuk adapter-konfig
Ebben a taskban a `config_jsonb` kizarolag az alabbi blokkokat jelentheti:
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
- contour-level gyartastechnologiai dontest;
- cut-order policyt;
- uj lead strategyt;
- CAM planning truthot.

#### 4. Lead-in/out csak mapping es fallback
A persisted `lead_in_jsonb` / `lead_out_jsonb` descriptorokat az adapter:
- vagy ki tudja irni a target formatumnak megfeleloen,
- vagy a config szerinti fallbackot alkalmazza,
- vagy determinisztikus hibaval megall.

A task **nem** tervez uj lead geometriat.

#### 5. Artifact policy
A task **nem** vezet be uj artifact kindot.
A cel a meglevo `app.artifact_kind = 'machine_program'` hasznalata.

Elvart:
- per-sheet artifactok;
- `artifact_kind='machine_program'`;
- `metadata_jsonb.legacy_artifact_type='hypertherm_edge_connect_basic_plasma_eia'`;
- stabil fajlnev, pl. `{run_id}_sheet_{sheet_index}.txt`;
- stabil storage path, pl.
  `projects/{project_id}/runs/{run_id}/machine_program/hypertherm_edge_connect/{sha256}.txt`.

A generic artifact list/download flow mar eleg. Uj endpoint vagy bridge migration
nem kell, ameddig a metadata helyesen ki van toltve.

#### 6. Target config baseline
A smoke fixture es a report referencia-konfigja ehhez a taskhoz ez az irany.
Ez **nem** globalis seed, hanem valid baseline contract:

```json
{
  "program_format": {
    "file_extension": ".txt",
    "code_page": "ascii",
    "line_ending": "lf",
    "comment_style": "parentheses",
    "word_separator": "none",
    "decimal_places": 3,
    "sequence_numbers": {
      "mode": "none",
      "start": 10,
      "step": 10
    },
    "program_id_policy": {
      "integer_only": false,
      "max_length": 64
    }
  },
  "motion_output": {
    "units": "mm",
    "distance_mode": "incremental",
    "arc_center_mode": "incremental",
    "arc_format": "ijk",
    "rapid_mode": "G00"
  },
  "coordinate_mapping": {
    "origin_anchor": "sheet_bottom_left",
    "mirror_x": false,
    "mirror_y": false,
    "swap_xy": false
  },
  "command_map": {
    "program_start": ["G21", "G91"],
    "program_end": ["M02"],
    "rapid": "G00",
    "linear": "G01",
    "arc_cw": "G02",
    "arc_ccw": "G03",
    "process_on": "M07",
    "process_off": "M08",
    "pierce_on": null,
    "pierce_off": null
  },
  "lead_output": {
    "supports_embedded_leads": true,
    "supported_shapes": ["line", "arc"],
    "allow_zero_lead_out": true,
    "emit_entry_marker": false,
    "unsupported_lead": "error"
  },
  "process_mapping": {
    "default_tool_code": null,
    "process_code_map": {}
  },
  "artifact_packaging": {
    "program_name_template": "{run_id}_sheet_{sheet_index}",
    "ascii_only": true,
    "max_filename_length": 64,
    "one_file_per_sheet": true
  },
  "capabilities": {
    "supports_arcs": true,
    "supports_ijk_arcs": true,
    "supports_radius_arcs": false,
    "supports_comments": true,
    "supports_explicit_pierce_commands": false,
    "supports_multi_sheet_bundle": false
  },
  "fallbacks": {
    "unsupported_arc": "error",
    "unsupported_comment": "drop",
    "unsupported_pierce": "inline_process_on"
  },
  "export_guards": {
    "require_program_end": true,
    "require_process_off_at_end": true,
    "forbid_empty_output": true
  }
}
```

#### 7. Implementacios irany
A dedikalt service jo neve:
- `generate_machine_programs_for_run(...)`
vagy ezzel egyenerteku, de maradjon a `api/services/machine_specific_adapter.py`
fajlban.

A service feladata:
1. owner-scoped run ellenorzes;
2. a runhoz tartozo `manufacturing_plan_json` artifact sor + storage objektum
   beolvasasa;
3. snapshotolt postprocessor selection es kapcsolt `config_jsonb` ellenorzese;
4. target adapter key / output format exact match check;
5. contouronkent geometry feloldas a persisted truthbol;
6. per-sheet emit, deterministic rendezessel;
7. meglevo `machine_program` artifactok idempotens cseréje ugyanarra a
   target legacy type-ra;
8. `run_artifacts` regisztracio.

#### 8. Smoke elvarasok
A task-specifikus smoke legalabb ezt bizonyitsa:
- valid `manufacturing_plan_json` + valid target config -> per-sheet
  `machine_program` artifactok letrejonnek;
- `artifact_kind='machine_program'` es
  `legacy_artifact_type='hypertherm_edge_connect_basic_plasma_eia'`;
- ugyanarra a truthra a content hash es filename deterministic;
- a service nem general `machine_ready_bundle`-t, zip-et, generic fallback emit-et
  vagy masodik adapter-outputot;
- unsupported lead eseten a config szerinti hiba/fallback lep eletbe;
- unsupported arc eseten a config szerinti hiba/fallback lep eletbe;
- ownership boundary ervenyesul;
- hiba jon, ha nincs `manufacturing_plan_json` artifact;
- hiba jon, ha a snapshotolt adapter key/output format nem egyezik a targettel;
- hiba jon, ha a kotelezo `config_jsonb` blokkok hianyoznak;
- nincs write a kovetkezo truth tablaba:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
  - `run_manufacturing_metrics`
  - `geometry_contour_classes`
  - `cut_contour_rules`
  - `postprocessor_profile_versions`

### DoD

- [ ] A task explicit targetet rogzit: `hypertherm_edge_connect` / `basic_plasma_eia_rs274d`.
- [ ] A task megorzi, hogy a H2-E5-T4 optionalis ag, nem H2 blocker.
- [ ] A service primer bemenete a persisted `manufacturing_plan_json` artifact.
- [ ] A service legfeljebb geometry feloldasra olvas `run_manufacturing_contours` +
      `geometry_derivatives` truthot, es nem kerul vissza live selection vilagba.
- [ ] A `config_jsonb` szukitett boundary-ja tenylegesen enforce-olva van.
- [ ] A task nem tervez uj lead-in/out rendszert.
- [ ] A task nem vezet be uj artifact kindot; a meglevo `machine_program` kindot
      hasznalja custom `legacy_artifact_type` metadata-val.
- [ ] A task nem seedel globalis postprocessor profilt migrationben.
- [ ] Keszul dedikalt `api/services/machine_specific_adapter.py`.
- [ ] Keszul task-specifikus smoke script.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` PASS.

### Kockazat + rollback

Kockazatok:
- a task visszacsuszik technology-pack vagy lead-design iranyba;
- a `manufacturing_plan_json` artifact megkerulesevel a service alternativ truthot
  kezd hasznalni;
- felesleges SQL migration keszul, mikozben a `machine_program` kind mar letezik;
- a task globalis owner-scoped postprocessor seedet probal migrationbe rakni;
- a geometry feloldas nem deterministic vagy nem owner-safe;
- a service duplikalt `machine_program` artifactokat hagy maga utan.

Mitigacio:
- explicit target freeze;
- explicit no-new-artifact-kind es no-global-seed szabaly;
- explicit geometry lookup boundary;
- per-sheet deterministic ordering es delete-then-insert policy;
- smoke a forbidden writes / forbidden artifact kinds / target mismatch / missing
  config / missing export artifact esetekre.

Rollback:
- a task kod-only scope-ban maradjon: service + smoke + dokumentacios artefaktok;
- a H2 mainline exporter (`H2-E5-T3`) erintetlen maradjon;
- a `machine_program` artifactok torlesevel a task side effectje visszafordithato.

## 🧪 Tesztallapot

Kotelezo gate:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`

Feladat-specifikus ellenorzes:
- `python3 -m py_compile api/services/machine_specific_adapter.py scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`
- `python3 scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`

## 🌍 Lokalizacio

Nem relevans.

## 📎 Kapcsolodasok

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `api/services/postprocessor_profiles.py`
- `api/services/run_snapshot_builder.py`
- `api/services/machine_neutral_exporter.py`
- `api/services/manufacturing_plan_builder.py`
- `api/services/geometry_derivative_generator.py`
- `api/routes/runs.py`
- `api/supabase_client.py`
- `worker/sheet_dxf_artifacts.py`
