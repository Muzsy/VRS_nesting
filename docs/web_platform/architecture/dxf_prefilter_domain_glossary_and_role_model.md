# DXF Prefilter Domain Glossary and Role Model (E1-T2)

## 1. Cel
Ez a dokumentum a DXF prefilter lane domain-szohasznalatat fagyasztja be docs-only modban.
A cel az, hogy a kovetkezo taskok (policy matrix, state machine, data model, API contract, UI flow)
azonos fogalmi retegekkel dolgozzanak, ne keverjek a kulonbozo role-szinteket.

## 2. Scope boundary
- Ez a dokumentum current-code truth + future canonical terminology rogzitese.
- Nem implementacios specifikacio.
- Nem enum/migration/API/UI kodmodositas.

## 3. Absztrakcios szintek

### 3.1 File/object-level (current-code truth)
- Source-of-truth: `app.file_kind` es upload route normalizalas.
- Current-code terminusok:
  - `source_dxf`
  - `source_svg`
  - `import_report`
  - `artifact`
- Jelentes:
  - storage/object ingest kategoria, nem geometry role.

### 3.2 Geometry revision-level (current-code truth)
- Source-of-truth: `app.geometry_role` enum.
- Current-code terminusok:
  - `part`
  - `sheet`
- Jelentes:
  - geometry revision domain-szerep, nem contour-level vagy DXF layer-level szerep.

### 3.3 Contour-level (current-code truth)
- Source-of-truth: manufacturing derivative payload + contour classification.
- Current-code terminusok:
  - `contour_role`: `outer`, `hole`
  - `contour_kind`: `outer`, `inner` (classification/matching oldalon)
- Jelentes:
  - kontur-tipus manufacturing derivalt es manufacturing szabaly oldalon.

### 3.4 DXF layer-level importer role (current-code truth)
- Source-of-truth: `vrs_nesting/dxf/importer.py`.
- Current-code terminusok:
  - `CUT_OUTER`
  - `CUT_INNER`
- Jelentes:
  - DXF layer konvencio az importer beolvasasi szintjen.

### 3.5 Frontend legacy upload terminology (current-code, de nem source-of-truth)
- Source: `ProjectDetailPage.tsx`, `NewRunPage.tsx`.
- Legacy UI terminusok:
  - `stock_dxf`
  - `part_dxf`
- Fontos:
  - ezek UI-level megnevezesek;
  - backend oldalon `source_dxf`-re normalizalodnak;
  - nem domain truth role-taxonomy.

### 3.6 DXF prefilter canonical layer-role (future canonical terminology)
- E1-T1 + E1-T2 glossary-szintu future canonical keszlet:
  - `CUT_OUTER`
  - `CUT_INNER`
  - `MARKING`
- Fontos boundary:
  - `MARKING` jelenleg future canonical glossary-term;
  - jelenleg nincs bekotve geometry import truth-kent a meglevo pipeline-ba.

## 4. Terminology table

| Fogalom | Szint | Statusz | Jelenlegi source-of-truth | Megjegyzes |
| --- | --- | --- | --- | --- |
| `file_kind=source_dxf` | file/object | current-code truth | migration + `api/routes/files.py` | ingest objektumtipus |
| `geometry_role=part/sheet` | geometry revision | current-code truth | migration + geometry import | geometry revision szerep |
| `contour_role=outer/hole` | contour | current-code truth | manufacturing derivative payload | derivalt kontur szerep |
| `contour_kind=outer/inner` | contour | current-code truth | contour classification + cut rules | `contour_role`-bol kepzett/hasznalt terminus |
| `CUT_OUTER/CUT_INNER` | DXF layer | current-code truth | importer | layer-konvencio |
| `stock_dxf/part_dxf` | frontend UI | legacy current-code | `ProjectDetailPage.tsx`, `NewRunPage.tsx` | nem domain source-of-truth |
| `MARKING` | DXF prefilter canonical | future canonical glossary | E1-T1/E1-T2 docs | meg nincs bekotve importer/geometry truth-kent |

## 5. Role taxonomy (normativ)
- File/object role kerdeseket `file_kind` nyelven kell megfogalmazni.
- Geometry revision role kerdeseket `geometry_role` nyelven kell megfogalmazni.
- Contour-level kerdeseket `contour_role` / `contour_kind` nyelven kell megfogalmazni.
- DXF prefilter canonical layer-role kerdeseket `CUT_OUTER` / `CUT_INNER` / `MARKING` nyelven kell megfogalmazni.
- A fenti szintek kozul egyik sem helyettesitheti a masikat automatikusan.

## 6. Tiltott osszemosasok (anti-pattern lista)
- `geometry_role` != `contour_role`
- `contour_role` != `DXF layer role`
- `file_kind` != `upload_kind`
- `stock_file` != `sheet geometry revision`
- `part_dxf` != `CUT_OUTER`
- `MARKING` != current geometry import truth
- `source_dxf` != `part` (egy file kind nem egyenlo geometry role-lal)

## 7. Current-code truth vs future canonical megkulonboztetes

### 7.1 Current-code truth (implementalt)
- `app.file_kind` ingest-tipusok.
- `app.geometry_role` = `part`/`sheet`.
- importer layer-konvencio: `CUT_OUTER`/`CUT_INNER`.
- manufacturing contour payload: `contour_role=outer/hole`.
- classification oldali `contour_kind=outer/inner`.

### 7.2 Future canonical prefilter terminology (glossary)
- `CUT_OUTER`/`CUT_INNER`/`MARKING` prefilter canonical role-vilag.
- `MARKING` jelenleg csak glossary-szintu commitment, nem bekotott geometry import role.

## 8. Ajanlott szohasznalat a kovetkezo taskokhoz
- Policy matrix: kulon oszlopban kezelje a file, geometry revision, contour es prefilter layer-role szintet.
- State machine: explicit allapot-atmenet only level-aware terminusokkal (`file_kind` trigger, `geometry_role` target, stb.).
- Data model/API contract: mezonevekben ne keveredjen a `role`, `kind`, `layer` fogalom.
- UI labels: legacy upload label kulon kezelendo, domain truth ne legyen belole visszakepezetlenul.

## 9. Bizonyitek forrasok
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/routes/files.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
