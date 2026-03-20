# DXF Nesting Platform Codex Task - H1-E6-T2 Sheet SVG generator (H1 minimum)
TASK_SLUG: h1_e6_t2_sheet_svg_generator_h1_minimum

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
- `worker/raw_output_artifacts.py`
- `api/services/geometry_derivative_generator.py`
- `api/routes/runs.py`
- `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t2_sheet_svg_generator_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, artifact kindot, storage bucketet vagy route
  contractot: a meglavo H0/H1 truthbol indulj ki.
- Ez a task H1 minimum **sheet SVG / viewer artifact** scope: ne csussz at
  sheet DXF, export bundle, manufacturing preview vagy nagy frontend-redesign
  iranyba.
- A viewer source of truth tovabbra is a projection adat; az SVG csak derived
  artifact.
- A rendereles projection truth + snapshot geometry/viewer derivative adatokra
  uljon, ne raw solver output parserre.
- Az artifactok a canonical `run-artifacts` bucketbe keruljenek, `sheet_svg`
  artifactkent, route-kompatibilis filename + `sheet_index` metadata mellett.
- A worker `done` zarasa csak sikeres sheet SVG generalas utan tortenhet.

Implementacios elvarasok:
- Legyen explicit worker-oldali sheet SVG generator helper/boundary.
- Per hasznalt sheet legalabb egy deterministic SVG dokumentum generalodjon.
- A geometriak a `viewer_outline` derivative-bol rajzolodjanak, hole-kompatibilis
  renderrel (`evenodd` vagy ezzel egyenerteku megoldas).
- Az SVG payload es az artifact storage/regisztracio ugyanarra a bemenetre legyen
  determinisztikus es retry-biztos.
- A jelenlegi `/viewer-data` route-ot ne tervezd ujra; eleg olyan artifactokat
  gyartani, amelyeket a route mar felismer (filename `.svg`, `sheet_index`
  metadata).
- Ha hianyzik a `viewer_outline` derivative vagy ervenytelen a placement/sheet
  kapcsolat, legyen determinisztikus task-hiba.

A reportban kulon nevezd meg:
- milyen projection/snapshot adatokbol keszul a render;
- hogyan biztosithato a deterministic SVG kimenet;
- hogyan tortenik az artifact upload + `run_artifacts` regisztracio;
- miert kompatibilis a kimenet a jelenlegi `/viewer-data` route-tal;
- hogy a task mit NEM vallal meg (sheet_dxf, bundle_zip, manufacturing, frontend
  redesign).

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
