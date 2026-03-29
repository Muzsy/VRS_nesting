# DXF Nesting Platform Codex Task - Placement export bbox origin fix
TASK_SLUG: placement_export_bbox_origin_fix

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/solver_io_contract.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `canvases/web_platform/placement_export_bbox_origin_fix.md`
- `codex/goals/canvases/web_platform/fill_canvas_placement_export_bbox_origin_fix.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez targeted bugfix task. Ne vezess be uj H2/H3 feature-scope-ot.
- Ne terjeszkedj solver-redesign, viewer API redesign vagy frontend atalakitas
  iranyba.
- A task ne irja at a solver policyjat arra, hogy shape-aware modon uj
  rotaciokat valasszon. A jelenlegi `rust/vrs_solver` bbox-alapu kontroll
  solvernek tekintendő.

Implementacios elvarasok:
- A worker oldalon legyen egyetlen, kovetkezetes placement-transform truth.
- A `rotation_deg` erteket a worker ne dobja el, hanem korrektul alkalmazza ott,
  ahol a projection/export retegnek ezt hasznalnia kell.
- A `bbox_jsonb` szamitas a normalizalt lokalis bbox-bol menjen, ne a nyers,
  negativ lokalis minimumokbol.
- Az SVG es a DXF export ugyanazzal a bbox-min referencia-korrekcioval dolgozzon.
- Legyen determinisztikus guard arra, hogy a projectalt bbox ne loghasson ki a
  sheetbol csendben.

Kulon figyelj:
- a mostani valodi bug a negativ lokalis bbox-os geometriak export/projection
  referenciahibaja;
- a haromszogek 0 fokos solver-kimenete nem automatikusan worker-bug;
- a smoke ezt a ket temat szandekosan valassza szet: bizonyitsd, hogy a worker
  tud 180 fokot korrektul kezelni, de ne allitsd, hogy ez a task shape-aware
  solver nestinget vezet be.

A smoke script bizonyitsa legalabb:
- negativ lokalis bbox eseten a normalizer helyes global bbox-ot ad;
- az SVG es DXF export ugyanarra a helyre rajzol;
- `rotation_deg=180.0` eseten a worker reteg kovetkezetesen alkalmazza a
  rotaciot;
- a guard hibazik, ha a geometry kilogna a sheetbol;
- nincs szukseg valos Supabase kapcsolatra vagy solver binaryra.

A reportban kulon nevezd meg:
- hol volt a konkret referenciahiba;
- hogyan lett kozosen harmonizalva a normalizer/SVG/DXF szemantika;
- milyen guard akadalyozza meg a csendes ervenytelen `done` allapotot;
- miert marad out-of-scope a shape-aware rotation valasztas.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
