# DXF Nesting Platform Codex Task - H2-E5-T4 elso machine-specific adapter
TASK_SLUG: h2_e5_t4_elso_machine_specific_adapter

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
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
- `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task tovabbra is **optionalis H2 adapter-ag**. Nem minositheted at H2
  blockerre a T4 hianyat.
- A target **befagyasztott es nem targyalhato ezen a taskon belul**:
  - `TARGET_MACHINE_FAMILY=hypertherm_edge_connect`
  - `TARGET_ADAPTER_KEY=hypertherm_edge_connect`
  - `TARGET_OUTPUT_FORMAT=basic_plasma_eia_rs274d`
  - `TARGET_LEGACY_ARTIFACT_TYPE=hypertherm_edge_connect_basic_plasma_eia`
- A task nem XPR embedded-process adapterrol szol.
- A task nem tervez uj lead-in/out rendszert. A persisted lead descriptorok
  csak mapping/fallback scope-ban maradnak.
- A task nem vezet be uj artifact kindot. A meglevo `machine_program`
  artifact kindot kell hasznalni.
- A task nem csinal globalis SQL seed migrationt a postprocessor profilokhoz,
  mert a domain owner-scoped.

Primer truth boundary:
- A service primer bemenete a runhoz tartozo persisted `manufacturing_plan_json`
  artifact legyen.
- Ne olvass live `project_manufacturing_selection` allapotot.
- Ne olvass raw solver outputot, worker run directory-t vagy preview SVG-t.
- A canonical geometry feloldasa megengedett, de csak a
  `manufacturing_plan_json` payloadban szereplo `plan_id` + `contour_index`
  alapjan, owner-scoped modon:
  - `run_manufacturing_contours.geometry_derivative_id`
  - `geometry_derivatives.derivative_jsonb` (`manufacturing_canonical`)
- Ez geometry feloldas, nem alternativ truth vagy live selection fallback.

`config_jsonb` boundary:
- Kizarolag ezek a blokkok ertelmezhetok:
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
- Tilos ide visszacsempeszni:
  - material/thickness technology packot
  - feed / kerf / pierce parameter konyvtarat
  - contour-level manufacturing policyt
  - cut-order policyt
  - uj lead strategyt

Implementacios elvarasok:
- Keszits dedikalt `api/services/machine_specific_adapter.py` service-t.
- A service owner-scoped runhoz:
  1) megtalalja es letolti a `manufacturing_plan_json` artifactot;
  2) ellenorzi a snapshotolt postprocessor selectiont;
  3) betolti a kapcsolt `postprocessor_profile_versions.config_jsonb`-t;
  4) csak akkor dolgozik tovabb, ha `adapter_key` es `output_format` pontosan
     egyezik a targettel;
  5) per-sheet emitet general determinisztikus sorrendben;
  6) a kimenetet `machine_program` artifactkent regisztralja;
  7) a metadata-ban kitolti a custom legacy type-ot:
     `hypertherm_edge_connect_basic_plasma_eia`.
- A filename legyen stabil, jo irany:
  - `{run_id}_sheet_{sheet_index}.txt`
- A storage path legyen stabil es auditálhato, jo irany:
  - `projects/{project_id}/runs/{run_id}/machine_program/hypertherm_edge_connect/{sha256}.txt`
- Ne tegyel a kimenetbe volatilis timestampet vagy mas nem determinisztikus mezot.
- Ugyanarra a truthra ujrageneralaskor ne maradjanak duplikalt target artifactok.

Tiltott mellekhatasok:
- nincs `machine_ready_bundle`
- nincs zip vagy extra bundle
- nincs generic fallback emitter
- nincs worker auto-trigger
- nincs frontend/export UI
- nincs write ezekbe a truth tablaba:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
  - `run_manufacturing_metrics`
  - `geometry_contour_classes`
  - `cut_contour_rules`
  - `postprocessor_profile_versions`

A smoke script bizonyitsa legalabb:
- valid export + valid target config -> per-sheet `machine_program` artifactok;
- `artifact_kind='machine_program'` es a custom legacy type metadata helyes;
- hash / filename / storage path deterministic;
- unsupported lead / arc eseten fallback vagy determinisztikus hiba;
- ownership boundary ervenyesul;
- hianyzo export artifact / hianyzo target metadata / hianyzo config blokkok
  eseten hiba jon;
- nincs forbidden write vagy forbidden artifact kind;
- nincs masodik implicit adapter-output.

A reportban kulon nevezd meg:
- miert a `manufacturing_plan_json` artifact a primer bemenet;
- hogyan oldjuk fel a canonical geometryt a persisted truthbol;
- miert a meglevo `machine_program` kindot hasznaljuk uj enum helyett;
- miert nincs globalis SQL seed;
- miert marad ki a reszletes lead-in/out rendszer;
- hogy a task tovabbra is optionalis H2 ag;
- hogy a konkret target:
  `hypertherm_edge_connect / basic_plasma_eia_rs274d`.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
