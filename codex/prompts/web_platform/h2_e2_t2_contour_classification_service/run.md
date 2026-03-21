# DXF Nesting Platform Codex Task - H2-E2-T2 contour classification service
TASK_SLUG: h2_e2_t2_contour_classification_service

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `supabase/migrations/20260322001000_h2_e2_t1_manufacturing_canonical_derivative_generation.sql`
- `api/services/geometry_derivative_generator.py`
- `api/services/dxf_geometry_import.py`
- `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
- `canvases/web_platform/h2_e2_t2_contour_classification_service.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e2_t2_contour_classification_service.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A task kozvetlenul a H2-E2-T1-re epul. A source truth a jelenlegi
  `manufacturing_canonical` derivative `contours` payloadja.
- A classification eredmeny kulon `app.geometry_contour_classes` tablaba kerul,
  nem a derivative JSON payloadba.
- A kezdeti `contour_kind` vilag maradjon minimalis es repo-hu:
  - `outer`
  - `inner`
- A `feature_class` lehet kezdetben egyszeru (`default`), de legyen stabil es
  auditálhato.
- A service csak `manufacturing_canonical` derivative-re epithet. Ne hasznalj
  `nesting_canonical` vagy `viewer_outline` payloadot contour truth-kent.
- A task ne nyisson H2-E3 vagy H2-E4 scope-ot:
  - nincs `cut_rule_sets`
  - nincs `cut_contour_rules`
  - nincs rule matching
  - nincs manufacturing snapshot / plan / preview / export
- A contour metricak (`area_mm2`, `perimeter_mm`, `bbox_jsonb`, `is_closed`)
  legyenek determinisztikusan szamolva a contour `points` listabol.
- A service legyen idempotens ugyanarra a derivative-re es contour_indexre.

Implementacios fokusz:
- Keszits minimalis, de valos schema-t `app.geometry_contour_classes` neven.
- Keszits explicit `api/services/geometry_contour_classification.py` service-t.
- Kotesd be a `api/services/dxf_geometry_import.py` validated import pipeline-ba.
- A classification legalabb outer/hole -> outer/inner mappinget tudjon.
- A reportban kulon nevezd meg, hogy ez a task mit NEM szallit le meg:
  - cut rule rendszer
  - rule matching
  - manufacturing plan builder
  - snapshot manufacturing bovites
  - preview / postprocess / export

A smoke script bizonyitsa:
- contour class rekordok letrehozhatok;
- a mapping helyes;
- a metric mezo(k) kitoltodnek;
- az upsert idempotens;
- nem manufacturing derivative-re nincs classification;
- rejected geometry pipeline nem gyart classification truth-ot.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t2_contour_classification_service.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
