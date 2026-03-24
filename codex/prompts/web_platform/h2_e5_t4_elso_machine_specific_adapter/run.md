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
- `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
- `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
- `api/services/postprocessor_profiles.py`
- `api/services/run_snapshot_builder.py`
- `api/services/machine_neutral_exporter.py`
- `api/routes/runs.py`
- `canvases/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t4_elso_machine_specific_adapter.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task a **H2-E5-T4 optionalis adapter-ag**. Ne minositsd at H2 blockerre
  pusztan azert, mert a T4 hianyzott eddig.
- A source-of-truth az adapterhez a gepfuggetlen export oldalon mar letezo
  `manufacturing_plan_json` artifact. Ne olvass live `project_manufacturing_selection`
  allapotot exporthoz, ne hasznalj raw solver outputot, es ne a preview SVG-bol dolgozz.
- A `config_jsonb` csak szuk adapter-konfig. Kizarolag az alabbi blokkok
  ertelmezhetok:
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
- A reszletes lead-in/out rendszer ebben a taskban **kifejezetten out of scope**.
  A task nem tervez uj lead geometriat, csak a bejovo persisted descriptorokat
  mapeli, vagy a config szerinti fallback/error agra fut.
- Ha a canvas `TARGET_MACHINE_FAMILY` / `TARGET_ADAPTER_KEY` /
  `TARGET_OUTPUT_FORMAT` mezoi nincsenek kitoltve, **allj meg BLOCKED allapottal**.
  Ne talalj ki celgep-csaladot vagy dialektust.
- Pontosan egy konkret adaptert implementalj. Ne epits altalanos plugin-rendszert,
  multi-adapter registryt vagy univerzalis frameworkot.
- A task legfeljebb a `run_artifacts` reteget bovitheti machine-ready artifacttal.
  Ne irj vissza `run_manufacturing_plans`, `run_manufacturing_contours`,
  `run_manufacturing_metrics`, `geometry_contour_classes`, `cut_contour_rules`
  vagy `postprocessor_profile_versions` truth tablaba.

Implementacios elvarasok:
- Vezess be machine-ready artifact kindot migrationnel, es frissitsd a legacy
  <-> enum bridge fuggvenyeket is.
- Keszits dedikalt `api/services/machine_specific_adapter.py` service-t.
- A service a `manufacturing_plan_json` artifact payloadjat, a snapshotolt
  postprocessor selection metadatajat es a kapcsolt `config_jsonb`-t hasznalja.
- A kimenet legyen deterministic ugyanarra a truthra.
- Unsupported lead / arc / command eseten csak a config szerinti fallback vagy
  determinisztikus hiba engedelyezett.
- Ne tegyel a kimenetbe volatilis timestampet vagy mas nem determinisztikus mezot.
- A filename, metadata es storage path legyen deterministic es auditálhato.
- A task ne vezessen be frontend export UI-t.

A smoke script bizonyitsa legalabb:
- valid machine-neutral export + valid adapter config -> machine-ready artifact letrejon;
- ugyanarra a truthra deterministic kimenet keletkezik;
- unsupported szerzodesi elemnel fallback vagy hiba lep eletbe;
- nincs write manufacturing truth retegekbe;
- ownership boundary ervenyesul;
- target adapter metadata vagy kotelezo `config_jsonb` blokkok hianyaban hiba jon;
- nincs masodik implicit generic adapter vagy plugin-keretrendszer-mellekhatas.

A reportban kulon nevezd meg:
- melyik konkret target adaptert implementalod;
- hogyan ervenyesitjuk a szukitett `config_jsonb` boundary-t;
- miert marad ki a reszletes lead-in/out rendszer;
- hogy a task a `manufacturing_plan_json` artifactra epit, nem live selectionre;
- hogy a task tovabbra is optionalis adapter-ag.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
