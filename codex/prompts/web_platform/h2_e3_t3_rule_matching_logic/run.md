# DXF Nesting Platform Codex Task - H2-E3-T3 rule matching logic
TASK_SLUG: h2_e3_t3_rule_matching_logic

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `api/services/geometry_contour_classification.py`
- `api/services/cut_rule_sets.py`
- `api/services/cut_contour_rules.py`
- `scripts/smoke_h2_e2_t2_contour_classification_service.py`
- `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
- `canvases/web_platform/h2_e3_t3_rule_matching_logic.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t3_rule_matching_logic.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A task tree szerint ez a task matching engine, nem CRUD, nem resolver es nem
  manufacturing plan builder. Maradj ebben a scope-ban.
- A matching explicit `cut_rule_set_id` inputtal dolgozzon. Ne probalj
  manufacturing profile-t, project manufacturing selectiont vagy postprocess
  vilagot feloldani.
- A matching a mar meglevo truth retegekre epul:
  - `geometry_contour_classes`
  - `cut_contour_rules`
  - `cut_rule_sets`
- Ne vezess be uj migraciot vagy persisted matching tablakat.
- Ne irj vissza `geometry_contour_classes` vagy mas truth tablaba `rule_id`-t,
  `matched_rule_id`-t vagy hasonlo allapotot.
- Ne nyisd ki a kovetkezo scope-okat:
  - manufacturing profile resolver
  - snapshot manufacturing bovites
  - run_manufacturing_plans / run_manufacturing_contours
  - preview / postprocess / export

Implementacios elvarasok:
- Keszits dedikalt `api/services/cut_rule_matching.py` service-t.
- A matching minimum ezeket a szabalyokat alkalmazza:
  1) `contour_kind` egyezes kotelezo,
  2) `feature_class` specifikus egyezes elonyben,
  3) `feature_class=default` fallback,
  4) csak `enabled=true` jeloltek,
  5) `perimeter_mm` alapu min/max tartomanyszures,
  6) determinisztikus tie-break.
- A tie-break szabaly legyen explicit es a reportban is nevezd meg.
- Az eredmeny adjon vissza contouronkenti matching-outputot, de ez maradjon csak
  service-return ertek, ne persisted truth.
- Unmatched contour eseten legyen tiszta `unmatched_reason`.

A smoke script bizonyitsa legalabb:
- outer es inner contour alap matching,
- specifikus feature_class > default fallback,
- disabled rule kizárása,
- hossztartomany miatti unmatched ag,
- determinisztikus tie-break,
- no-write guarantee.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H2-E3-T3 matching reteghez;
- hogy mit NEM szallit le meg:
  - resolver,
  - plan builder,
  - persisted run contour rule assignment,
  - preview / export;
- hogy a kesobbi H2-E4 plan builder ezt a matching service-t fogyasztja majd,
  de ez a task meg nem keszit manufacturing plant.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
