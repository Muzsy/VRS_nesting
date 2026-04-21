# DXF Prefilter E4-T2 Preflight settings panel
TASK_SLUG: dxf_prefilter_e4_t2_preflight_settings_panel

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_preflight_persistence.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `tests/test_dxf_preflight_runtime.py`
- `canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `canvases/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t2_preflight_settings_panel.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **preflight settings panel** task. Ne nyiss diagnostics drawer, review modal,
  detailed runs table, accepted->parts flow, replace/rerun vagy feature flag scope-ot.
- Current-code truth szerint nincs implementalt named rules-profile domain; ne epits
  profile CRUD-ot, profile listat, owner/version tablat vagy project-level persisted
  settings API-t.
- A helyes V1 bridge most: frontend draft settings -> optional complete_upload payload ->
  preflight runtime -> persisted rules_profile_snapshot_jsonb.
- A route ne akarja policy-szinten ujravalidalni a snapshotot; a minimalis mapping
  boundary utan az E2 service-ek mar amugy is sajat minimal normalizacioval dolgoznak.
- A `canonical_layer_colors` teljes editor scope-ja most out-of-scope; maradjon
  backend-default / kesobbi task.
- A `NewRunPage.tsx` legacy wizardot ne bovitsd prefilter funkciokkal.
- A legacy `validate_dxf_file_async(...)` secondary signal maradjon bent.

Modellezesi elvek:
- A DxfIntakePage read-only defaults blokkja helyett legyen valodi settings panel.
- A panel minimal user-facing mezői legyenek:
  - `strict_mode`
  - `auto_repair_enabled`
  - `interactive_review_on_ambiguity`
  - `max_gap_close_mm`
  - `duplicate_contour_merge_tolerance_mm`
  - `cut_color_map`
  - `marking_color_map`
- A `cut_color_map` / `marking_color_map` UI-ja lehet egyszeru comma-separated ACI lista.
- Legyen `Reset to defaults` muvelet.
- A defaultok igazodjanak a backend jelenlegi service-defaultjaihoz:
  - `strict_mode = false`
  - `auto_repair_enabled = false`
  - `interactive_review_on_ambiguity = true`
  - `max_gap_close_mm = 1.0`
  - `duplicate_contour_merge_tolerance_mm = 0.05`
  - `cut_color_map = []`
  - `marking_color_map = []`
- A frontend draftot explicit tipus vagy helper alakban kezeld; ne legyen nyers,
  ad hoc `Record<string, unknown>` komponensallapot.
- Az upload finalize payload optional `rules_profile_snapshot_jsonb` mezot kapjon.
- A backend `FileCompleteRequest` ezt optional mappingkent fogadja.
- A runtime szuntesse meg a `rules_profile=None` hardcode-ot es tenylegesen adja
  tovabb a snapshotot a role resolver / gap repair / duplicate dedupe /
  normalized writer / persistence hivasoknak.
- Ne nyiss named profiles vagy project-level settings persistence scope-ot.

Kulon figyelj:
- a route response shape ne torjon el;
- ha nincs snapshot, a korabbi viselkedes maradjon valtozatlan;
- a smoke bizonyitsa a settings panel jelenletet es a plumbing szerzodest;
- a reportban nevezd meg, hogy ez miert upload-session szintu bridge, es miert nem
  teljes rules-profile domain.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile api/routes/files.py api/services/dxf_preflight_runtime.py tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- `python3 -m pytest -q tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`

A reportban kulon terj ki erre:
- miert a settings panel + upload payload bridge a helyes minimalis lepes a jelenlegi
  code truth mellett;
- mely defaultok lettek a UI-ban befagyasztva;
- pontosan mely rules-profile mezok lettek most user-facing modon bekotve;
- mi marad kesobbi scope-ban (`canonical_layer_colors` editor, named profiles,
  project-level persistence, diagnostics/review UI).
