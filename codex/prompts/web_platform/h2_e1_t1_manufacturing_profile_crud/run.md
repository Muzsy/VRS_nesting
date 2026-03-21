# DXF Nesting Platform Codex Task - H2-E1-T1 Manufacturing profile CRUD (retroaktiv scope-rendezes)
TASK_SLUG: h2_e1_t1_manufacturing_profile_crud

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`
- `canvases/web_platform/h2_e1_t1_manufacturing_profile_crud.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e1_t1_manufacturing_profile_crud.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task dokumentacios scope-rendezes, ne keszuljon uj migration vagy uj API kod.
- A reportban explicit legyen a hatar:
  - H2-E1-T1: manufacturing profile domain schema/policy alap
  - H2-E1-T2: project manufacturing selection API flow
- A reportban kulon nevezd meg, hogy dedikalt manufacturing profile CRUD API
  tovabbi follow-up.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t1_manufacturing_profile_crud.md`
