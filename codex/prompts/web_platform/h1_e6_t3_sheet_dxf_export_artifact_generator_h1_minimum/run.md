# DXF Nesting Platform Codex Task - H1-E6-T3 Sheet DXF/export artifact generator (H1 minimum)
TASK_SLUG: h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `api/services/geometry_derivative_generator.py`
- `api/routes/runs.py`
- `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, artifact kindot, storage bucketet vagy route
  contractot: a meglavo H0/H1 truthbol indulj ki.
- Ez a task H1 minimum **sheet DXF / basic export artifact** scope: ne csussz at
  bundle ZIP, manufacturing canonical, machine-program vagy nagy frontend/API
  redesign iranyba.
- A projection tovabbra is source of truth; a DXF csak derived export artifact.
- Az export projection truth + snapshot geometry/`nesting_canonical` derivative
  adatokra uljon, ne raw solver output parserre es ne `viewer_outline`-ra.
- Az artifactok a canonical `run-artifacts` bucketbe keruljenek, `sheet_dxf`
  artifactkent, route-kompatibilis filename + `sheet_index` metadata mellett.
- A worker `done` zarasa csak sikeres sheet DXF generalas utan tortenhet.

Implementacios elvarasok:
- Legyen explicit worker-oldali sheet DXF generator helper/boundary.
- Per hasznalt sheet legalabb egy deterministic DXF dokumentum generalodjon.
- A geometriak a `nesting_canonical` derivative-bol rajzolodjanak, a placement
  transzformaciot kovetve.
- A DXF legyen minimum szinten visszaolvashato/ellenorizheto, de ne akarj H2-s
  manufacturing-fidelitast vagy eredeti entitasmegorzest.
- Az artifact storage/regisztracio ugyanarra a bemenetre legyen determinisztikus
  es retry-biztos.
- A jelenlegi route-okat ne tervezd ujra; eleg olyan artifactokat gyartani,
  amelyeket a route mar felismer (filename `.dxf`, `sheet_index` metadata).
- Ha hianyzik a `nesting_canonical` derivative vagy ervenytelen a
  placement/sheet kapcsolat, legyen determinisztikus task-hiba.

A reportban kulon nevezd meg:
- milyen projection/snapshot/derivative adatokbol keszul a DXF export;
- hogyan biztosithato a deterministic DXF kimenet;
- hogyan tortenik az artifact upload + `run_artifacts` regisztracio;
- miert kompatibilis a kimenet a jelenlegi route-tal es artifact listaval;
- hogy a task mit NEM vallal meg (bundle_zip, manufacturing canonical,
  machine-program, frontend redesign).

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
