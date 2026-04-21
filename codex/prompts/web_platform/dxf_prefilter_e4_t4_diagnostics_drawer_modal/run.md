Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj historical preflight-runs endpointot.
- Ne talalj ki uj `/preflight-runs/{id}` detail endpointot.
- Ne nyiss review modal, replace-rerun, accepted->parts vagy barmilyen mutalo row action scope-ot.
- A helyes current-code truth most: a meglevo `/projects/{project_id}/files` route optional
  latest diagnostics projectionjat kell bevezetni, es erre kell a DxfIntakePage diagnostics
  drawer/modal nezetet felepiteni.
- A diagnostics truth a persisted T7 `summary_jsonb`-bol jojjon; a frontend ne parse-olja kozvetlenul a nyers blobot.
- Az artifact references current-code truth szerint local backend referenciak; ne talalj ki signed URL-t vagy download route-ot.
- Ne bovitsd a `NewRunPage.tsx` legacy wizardot.

Modellezesi elvek:
- A route optional query-je lehet peldaul `include_preflight_diagnostics=true`, de a T3 alapviselkedes
  `include_preflight_summary=true` agan ne ronts.
- A file-onkenti latest run modell maradjon valtozatlan; a T4 is latest preflight truthra epuljon.
- A backend stabil, drawer-ready diagnostics payloadot adjon vissza, legalabb ezekkel a retegekkel:
  - `source_inventory_summary`
  - `role_mapping_summary`
  - `issue_summary`
  - `repair_summary`
  - `acceptance_summary`
  - `artifact_references`
- A frontend kapjon dedikalt tipust, pl. `ProjectFileLatestPreflightDiagnostics`, es a `ProjectFile`
  optional `latest_preflight_diagnostics` mezot.
- A `DxfIntakePage` kapjon non-mutating `View diagnostics` jellegu triggereket es page-local drawer/modal state-et.
- A drawer/modal minimum ezeket jelenitse meg:
  - file nev + run status + acceptance + run seq/finished;
  - source inventory;
  - role mapping;
  - issue summary es normalized issue lista;
  - repair summary;
  - acceptance highlights;
  - artifact references (label/path/exists).
- Ha nincs diagnostics payload, a drawer ne nyiljon meg hibasan; legyen hidden vagy disabled trigger.

Kulon figyelj:
- a file-list route latest-run kivalasztasi logikaja ne torjon el;
- a diagnostics projection maradjon null-safe ures/hianyos `summary_jsonb` eseten is;
- az `include_preflight_diagnostics=false` viselkedes maradjon valtozatlan;
- a frontend build forduljon;
- a smoke determinisztikusan bizonyitsa a diagnostics trigger + drawer/modal + route projection jelenletet.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_diagnostics.py scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`
- `python3 -m pytest -q tests/test_project_files_preflight_diagnostics.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`

A reportban kulon terj ki erre:
- miert a meglevo file-list route optional diagnostics projectionja a helyes T4 minimal modell a jelenlegi repo truth mellett;
- pontosan mely diagnostics reteg(ek)et vetiti ki most a backend;
- hogyan marad read-only/local-reference az artifact block;
- miert marad kesobbi scope-ban a review modal, replace-rerun, accepted->parts es a historical/detail endpoint vilag.
