Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj historical preflight-runs endpointot.
- Ne nyiss diagnostics drawer / modal / review / replace-rerun / accepted->parts scope-ot.
- Ne bovitsd a `NewRunPage.tsx` legacy wizardot.
- A helyes current-code truth most: a file list endpoint optional `latest_preflight_summary`
  projectionjat kell gazdagitani, es erre kell a DxfIntakePage jobb oldali latest runs
  tablajat felepiteni.
- A `summary_jsonb` parse-olasa backend oldalon tortenjen; a frontend lapos, stabil,
  optional-safe summary shape-et fogyasszon.
- A T3 actions oszlop current-code truth szerint csak `recommended action / next step`
  jellegu, user-facing label lehet; ne talalj ki uj gombokat vagy mutating actionokat.

Modellezesi elvek:
- A `latest_preflight_summary` minimal bovitett alakja legalabb ezeket tudja:
  - `preflight_run_id`
  - `run_seq`
  - `run_status`
  - `acceptance_outcome`
  - `finished_at`
  - `blocking_issue_count`
  - `review_required_issue_count`
  - `warning_issue_count`
  - `total_issue_count`
  - `applied_gap_repair_count`
  - `applied_duplicate_dedupe_count`
  - `total_repair_count`
  - `recommended_action`
- A `recommended_action` backend-projected, stabil enum-like string legyen, pl.:
  - `ready_for_next_step`
  - `review_required_wait_for_diagnostics`
  - `rejected_fix_and_reupload`
  - `preflight_in_progress`
  - `preflight_not_started`
- A route a `preflight_runs.summary_jsonb` alapjan szamolja ki a counts mezoket.
- Ha a `summary_jsonb` reszben hianyzik vagy ures, a projection maradjon null-safe es
  ne torje el a file list route-ot.
- A frontend oldalon kulon helper-ek legyenek a badge-ekhez, pl.:
  - `formatRunStatusBadge(...)`
  - `formatAcceptanceOutcomeBadge(...)`
  - `formatIssueCountBadge(...)`
  - `formatRepairCountBadge(...)`
  - `formatRecommendedActionLabel(...)`
- A jobb oldali kartya jelenitse meg minimum ezeket az oszlopokat:
  - `Filename`
  - `Run status`
  - `Issues`
  - `Repairs`
  - `Acceptance`
  - `Recommended action`
  - opcionálisan `Finished` vagy `Run #`

Kulon figyelj:
- a route latest-run kivalasztasi logikaja ne torjon el;
- a `include_preflight_summary=false` viselkedes maradjon valtozatlan;
- a frontend build forduljon;
- a smoke determinisztikusan bizonyitsa az uj summary mezoket es a tablazat oszlopait.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_summary.py scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
- `python3 -m pytest -q tests/test_project_files_preflight_summary.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`

A reportban kulon terj ki erre:
- miert a file-onkenti latest run projection a helyes T3 minimal modell a jelenlegi repo truth mellett;
- pontosan mely uj summary mezoket vetiti ki most a backend;
- hogyan all ossze a `recommended_action` mapping;
- miert marad kesobbi scope-ban a diagnostics drawer, review modal es historical runs endpoint.
