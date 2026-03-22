# DXF Nesting Platform Codex Task - H2-E5-T1 Manufacturing preview SVG
TASK_SLUG: h2_e5_t1_manufacturing_preview_svg

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
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260318103000_h1_e3_t3_security_and_schema_bridge_fixes.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/geometry_derivative_generator.py`
- `worker/sheet_svg_artifacts.py`
- `api/routes/runs.py`
- `canvases/web_platform/h2_e5_t1_manufacturing_preview_svg.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t1_manufacturing_preview_svg.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task preview artifact task, nem postprocessor, nem exporter, nem worker
  full auto-integracio es nem frontend redesign.
- A preview source-of-truth-ja a persisted manufacturing plan vilag:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
  - `run_layout_sheets`
  - `geometry_derivatives` (`manufacturing_canonical`)
- Ne olvass raw solver outputot preview rendereleshez.
- Ne olvass live `project_manufacturing_selection` allapotot.
- Ne irj vissza `run_manufacturing_plans`, `run_manufacturing_contours`,
  `run_manufacturing_metrics`, `geometry_contour_classes` vagy barmely mas
  korabbi truth tablaba.
- A task legfeljebb a `run_artifacts` retegbe irhat.
- A jelenlegi generic artifact list/download flow mar elegendo review-celra;
  ne nyiss uj dedikalt preview route vagy nagy `viewer-data` redesign scope-ot.

Implementacios elvarasok:
- Vezesd be a `manufacturing_preview_svg` artifact kindot migrationnel.
- Frissitsd a legacy <-> enum bridge fuggvenyeket is, hogy a `run_artifacts`
  insert/list flow ezt a tipust konzisztensen kezelje.
- Keszits dedikalt `api/services/manufacturing_preview_generator.py` service-t.
- A generator per-sheet SVG-ket gyartson a persisted H2 plan truth es a
  `manufacturing_canonical` contour pontok alapjan.
- A preview legalabb ezt jelenitse meg:
  - contour pathok,
  - outer/inner megkulonboztetes,
  - entry marker,
  - lead-in / lead-out jeloles,
  - alap cut-order review info.
- A render maradjon gepfuggetlen preview: ne vallaljon toolpath emit-et,
  postprocessor-specifikus pathot vagy export artifactot.
- A filename, metadata es storage path legyen deterministic es auditalhato.
  Jo irany:
  - `out/manufacturing_preview_sheet_001.svg`
  - hash-alapu canonical storage path
  - metadata: `filename`, `sheet_index`, `size_bytes`, `content_sha256`,
    `legacy_artifact_type='manufacturing_preview_svg'`.
- Az artifact persistence ugyanarra a run + sheet logical targetre legyen
  idempotens.

A smoke script bizonyitsa legalabb:
- valid plan -> preview artifact letrejon;
- a preview gyartasi meta-informaciot is hordoz;
- a render a `manufacturing_canonical` geometriat hasznalja;
- outer/inner megkulonboztetes jelen van;
- rerun idempotens;
- nincs write korabbi truth tablaba;
- nincs export/postprocess artifact;
- hiba jon hianyzo derivative vagy hibas contour-link eseten.

A reportban kulon nevezd meg:
- milyen persisted truthbol epul a preview;
- hogyan kezeljuk a `manufacturing_preview_svg` artifact kind bevezeteset;
- hogyan biztosithato a deterministic SVG + storage/metadata policy;
- miert marad ez a task preview scope-ban;
- hogy mit NEM szallit le meg:
  - machine-neutral export,
  - postprocessor adapter,
  - worker auto-behuzas,
  - preview-specifikus frontend oldal.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
