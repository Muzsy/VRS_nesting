# DXF Nesting Platform Codex Task - H2-E3-T2 cut contour rules model
TASK_SLUG: h2_e3_t2_cut_contour_rules_model

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `api/routes/cut_rule_sets.py`
- `api/services/cut_rule_sets.py`
- `canvases/web_platform/h2_e3_t2_cut_contour_rules_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t2_cut_contour_rules_model.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A task H2-E3-T2, nem H2-E3-T3. Ezert ne implementalj contour class -> rule
  matching logikat, ne irj `rule_id`-t a `geometry_contour_classes` tablaba,
  es ne oldj fel manufacturing plan donteseket.
- A task H2-E3-T2, nem manufacturing profile binding. Ezert ne kosd be a
  contour rule-okat manufacturing profile versionbe, project selectionbe,
  snapshotba vagy plan builderbe.
- A contour rule owner-scope a kapcsolt `cut_rule_set_id` ownerjen keresztul
  ervenyesuljon. Ne talalj ki kulon owner mezot, ha a meglevo repo-mintakhoz a
  kapcsolat-alapu owner-scope tisztabban illeszkedik.
- `contour_kind` kezdetben csak `outer|inner` legyen.
- `lead_in_type` / `lead_out_type` csak szuk, dokumentalt kor legyen.
- A hosszak/radiusok, ha jelen vannak, pozitivak legyenek.
- `min_contour_length_mm <= max_contour_length_mm`, ha mindketto jelen van.
- A task ne talaljon ki gep-/anyag-katalogus FK-kat, es ne nyissa ki a preview,
  export vagy postprocess scope-ot.

Implementacios fokusz:
- Vezess be minimalis `app.cut_contour_rules` truth-ot.
- Keszits explicit `api/services/cut_contour_rules.py` service-t.
- Keszits minimalis `api/routes/cut_contour_rules.py` route-okat, es kotd be az
  `api/main.py`-ba.
- A route legyen a rule set ala szervezve.
- A smoke script bizonyitsa a fo sikeres es hibas agakat.
- A report kulon nevezze meg, hogy a task mit NEM szallit le meg:
  - rule matching,
  - manufacturing profile binding,
  - snapshot / plan / preview / export,
  - contour class eredmenyek konkret rule-ra kotese.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
