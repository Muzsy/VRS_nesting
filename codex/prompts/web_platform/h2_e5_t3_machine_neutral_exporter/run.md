# DXF Nesting Platform Codex Task - H2-E5-T3 Machine-neutral exporter
TASK_SLUG: h2_e5_t3_machine_neutral_exporter

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql`
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/run_snapshot_builder.py`
- `worker/raw_output_artifacts.py`
- `api/routes/runs.py`
- `canvases/web_platform/h2_e5_t3_machine_neutral_exporter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t3_machine_neutral_exporter.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task gepfuggetlen export artifact task, nem machine-specific adapter,
  nem `machine_ready_bundle`, nem worker full auto-integracio es nem export UI.
- Az exporter source-of-truth-ja a persisted H2 plan/snapshot vilag:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
  - `nesting_run_snapshots.manufacturing_manifest_jsonb`
  - opcionálisan `run_manufacturing_metrics`
  - szukseg eseten `geometry_derivatives` (`manufacturing_canonical`)
- Ne olvass live `project_manufacturing_selection` allapotot exporthoz.
- Ne olvass raw solver outputot vagy preview SVG artifactot mint forrast.
- Ne irj vissza `run_manufacturing_plans`, `run_manufacturing_contours`,
  `run_manufacturing_metrics`, `geometry_contour_classes`,
  `project_manufacturing_selection` vagy `postprocessor_profile_versions`
  truth tablaba.
- A task legfeljebb a `run_artifacts` retegbe irhat derived export artifactot.
- A generic artifact list/download flow mar elegendo; ne nyiss nagy
  `api/routes/runs.py` redesign scope-ot, es ne hozz letre kulon export UI-t.

Implementacios elvarasok:
- Vezesd be a `manufacturing_plan_json` artifact kindot migrationnel.
- Frissitsd a legacy <-> enum bridge fuggvenyeket is, hogy a `run_artifacts`
  insert/list flow ezt a tipust konzisztensen kezelje.
- Keszits dedikalt `api/services/machine_neutral_exporter.py` service-t.
- A service owner-scoped runhoz deterministic, canonical JSON payloadot gyartson
  a persisted manufacturing truth es a snapshotolt postprocessor selection alapjan.
- Ha az export contracthoz szukseges, emelj be contour/path adatot a
  `manufacturing_canonical` derivative-bol, de ne alkalmazz machine-specific
  geometriat vagy toolpath-logikat.
- A payload legalabb ezt hordozza:
  - `export_contract_version`
  - `run_id`, `project_id`
  - `manufacturing_profile_version_id`
  - plan / sheet / contour szintu deterministic adatok
  - opcionálisan `manufacturing_metrics`
  - aktiv postprocessor ref eseten metadata: `active_postprocessor_profile_version_id`,
    `adapter_key`, `output_format`, `schema_version`
- Ne tegyel a payloadba volatilis timestampet vagy egyeb nem determinisztikus
  mezot, ami ugyanarra a truthra byte-szinten mas artifactot eredmenyezne.
- A filename, metadata es storage path legyen deterministic es auditalhato.
  Jo irany:
  - `out/manufacturing_plan.json`
  - hash-alapu canonical storage path
  - metadata: `filename`, `size_bytes`, `content_sha256`,
    `legacy_artifact_type='manufacturing_plan_json'`,
    `export_scope='h2_e5_t3'`.
- Az artifact persistence ugyanarra a run truth allapotra legyen idempotens.

A smoke script bizonyitsa legalabb:
- valid plan -> export artifact letrejon;
- a payload deterministic;
- snapshotolt postprocessor selection metadata bekerulhet, de nincs
  machine-specific emit;
- postprocessor ref nelkul is generalhato export;
- rerun idempotens;
- nincs write korabbi truth tablaba;
- nincs `machine_ready_bundle`, `machine_log`, G-code vagy adapter-run side effect;
- hiba jon hianyzo plan vagy ownership sertes eseten.

A reportban kulon nevezd meg:
- milyen persisted truthbol epul a machine-neutral export;
- hogyan vezetjuk be a `manufacturing_plan_json` artifact kindot;
- hogyan biztositjuk a deterministic JSON + storage/metadata policy-t;
- miert marad ez a task gepfuggetlen export scope-ban;
- hogy mit NEM szallit le meg:
  - machine-specific adapter,
  - `machine_ready_bundle`,
  - worker auto-behuzas,
  - export UI vagy uj dedikalt endpoint.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
