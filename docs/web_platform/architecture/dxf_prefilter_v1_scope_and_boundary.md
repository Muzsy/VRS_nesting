# DXF Prefilter V1 - Scope and Boundary Freeze

## 1. CEl es statusz
Ez a dokumentum a DXF prefilter lane E1-T1 contract freeze (docs-only) source-of-truthja.
A cel most nem implementacio, hanem a V1 scope, integration boundary es out-of-scope hatarok rogzitese a jelenlegi kodra epitve.

## 2. Jelenlegi, kodbol igazolt baseline
A jelenlegi backend/frontend lanc mar meglevo elemei:

- DXF importer mag: `vrs_nesting/dxf/importer.py`
  - strict layer-konvencio: `CUT_OUTER` / `CUT_INNER` (`OUTER_LAYER_DEFAULT`, `INNER_LAYER_DEFAULT`)
  - fail-fast hibakodok nyitott vagy ketertelmu geometriara (pl. `DXF_OPEN_OUTER_PATH`, `DXF_MULTIPLE_OUTERS`, `DXF_OPEN_INNER_PATH`)
- Geometry import service: `api/services/dxf_geometry_import.py`
  - uploadolt forrasbol `import_part_raw` hivas
  - canonical geometry + validation report + derivative/classification lanc
- Geometry validation report: `api/services/geometry_validation_report.py`
  - canonical payload validacio, bbox-ellenorzes, topology check
- Legacy readability check: `api/services/dxf_validation.py`
  - basic `ezdxf.readfile` probe; nem teljes preflight gate
- File upload route: `api/routes/files.py`
  - `complete_upload` utan automatikusan fut az async geometry import task
- Frontend entrypointok:
  - `frontend/src/pages/ProjectDetailPage.tsx` (upload + file lista)
  - `frontend/src/pages/NewRunPage.tsx` (legacy run wizard)

Kovetkeztetes:
- Van meglevo upload -> geometry import -> validation alaplanc.
- Nincs dedikalt deterministic prefilter/preflight acceptance gate a geometry import elott.

## 3. V1 termek-scope (in-scope)
A V1 prefilter lane contractja:

- A prefilter egy acceptance gate modul lesz a meglevo import/validation lanc ele epitve.
- A belso truth layer-alapu marad, canonical role-vilaggal:
  - `CUT_OUTER`
  - `CUT_INNER`
  - `MARKING`
- A szin input-hint szerepet kap, de nem a belso truth forrasa.
- A V1 fail-fast policyvel mukodik, es csak egyertelmu javitasokat vegezhet.
- A V1 eredmenye egy explicit acceptance dontes:
  - `accepted` -> tovabblepes a meglevo geometry import service fele
  - `rejected` / `review_required` -> stop a geometry import elott

## 4. V1 fail-fast policy (contract)
A V1 prefilter NEM talalgat. Csak explicit, egyertelmu javitas engedett:

- Engedett:
  - nagyon kis, egyertelmu kontur-gap zaras konfiguralt `max_gap_close_mm` kuszob alatt
  - egyertelmu, duplikalt zart kontur deduplikacio
- Nem engedett:
  - tobb outer-jelolt kozotti automatikus valasztas
  - bizonytalan topology auto-javitas
  - nyitott vagokontur csendes javitasa

## 5. Backend boundary es jovobeli bekotesi pont
A jovobeli backend hook pont helye a jelenlegi lanc szerint:

1. upload URL + file feltoltes
2. `POST /projects/{project_id}/files` (`complete_upload`) metadata finalize
3. **itt lep be a DXF prefilter gate**
4. csak `accepted` file menjen tovabb `import_source_dxf_geometry_revision_async` iranyba

Ez azt jelenti, hogy a prefilter a file upload utan, de a geometry import elott helyezkedik el.

## 6. UI boundary es irany
V1 UI irany:

- Nem a legacy `NewRunPage.tsx` tovabbi foltozasa.
- Kulon `DXF Intake / Project Preparation` oldal a helyes irany.
- A kulon intake oldal minimumban ezeket fogja ossze:
  - upload + replace flow
  - rules profile / gyors beallitasok
  - preflight status
  - diagnostics es explicit review allapot
- Csak accepted allapot utan legyen tovabblepes geometry/part/run iranyba.

Indok:
- A `NewRunPage.tsx` jelenleg run-konfiguracios wizard, nem ingest-review workflow.
- A `ProjectDetailPage.tsx` uploadot kezel, de nincs benne dedikalt preflight diagnostics allapotgep.

## 7. Mi nincs benne a V1-ben (out-of-scope)
Ez a task es a V1 freeze explicit NEM tartalmazza:

- uj DXF parser motor fejlesztese
- parhuzamos import stack a meglevo importer mellett
- Python/TypeScript/SQL implementacio ebben a taskban
- uj migration vagy API endpoint implementacio ebben a taskban
- teljes state machine vagy vegleges API schema implementalasa
- teljes UI komponens implementacio

## 8. Miert nem uj parhuzamos DXF motor
A repoban mar letezik es hasznalt a `vrs_nesting.dxf.importer.import_part_raw`, amelyre mar a geometry import pipeline is epul.
A V1 prefilter helyes feladata a meglevo truth-lanc ele epitett acceptance policy, nem egy masodik parser-olvasat.

## 9. Kapcsolodo forrasok (scope freeze alap)
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/dxf_validation.py`
- `api/routes/files.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `canvases/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
