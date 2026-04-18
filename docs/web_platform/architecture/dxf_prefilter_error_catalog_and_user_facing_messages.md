# DXF Prefilter Error Catalog and User-Facing Messages (E1-T7)

## 1. Cel
Ez a dokumentum docs-only modban lefagyasztja a DXF prefilter V1 error catalog es
user-facing message szerzodeset. A cel nem backend/frontend implementacio, hanem
stabil, repo-grounded hiba- es uzenetkontraktus adasa a kesobbi E2/E3/E4 taskokhoz.

## 2. Scope boundary
- Ez architecture-level error-catalog freeze.
- Nem exception translator service implementacio.
- Nem API response model vagy OpenAPI schema implementacio.
- Nem frontend komponens vagy i18n/localization implementacio.
- Nem support tooling implementacio.

## 3. Current-code error truth (repo-grounded)

### 3.1 Importer structured DXF codes
- A `vrs_nesting/dxf/importer.py` `DxfImportError(code, message)` formatumban dob
  stabil kodokat (`DXF_*`).
- Reprezentativ current-code kodok:
  - `DXF_NO_OUTER_LAYER`
  - `DXF_OPEN_OUTER_PATH`
  - `DXF_OPEN_INNER_PATH`
  - `DXF_MULTIPLE_OUTERS`
  - `DXF_UNSUPPORTED_ENTITY_TYPE`
  - `DXF_UNSUPPORTED_UNITS`
- A raw `message` technikai kontextust is tartalmazhat (layer, entity path, stb.),
  ez jelenleg nem user-facing szerzodes.

### 3.2 Geometry validation issue codes + severity
- A `api/services/geometry_validation_report.py` issue objektumot epit:
  `code`, `severity`, `path`, `message`, opcionisan `details`.
- Reprezentativ `GEO_*` kodok:
  - `GEO_CANONICAL_MISSING`
  - `GEO_BBOX_ROW_MISMATCH`
  - `GEO_HOLE_OUTSIDE_OUTER`
  - `GEO_CANONICAL_HASH_MISMATCH`
  - `GEO_SOURCE_LINEAGE_MISSING`
- A `severity` jelenleg legalabb `error`/`warning` szinteket formal, es ezekbol
  summary is kepzodik.

### 3.3 Global runtime error format and prefixes
- A global catalog (`docs/error_code_catalog.md`) mar rogzit:
  - runtime format: `ERROR: <CODE>: <message>`
  - stabil prefix policy (`DXF_*`, `E_RUN_*`, `E_DXF_*`, stb.)
- Ez alapot ad a prefilter domain stable code naming policy-hez.

### 3.4 Frontend raw error presentation points
- `ProjectDetailPage.tsx`, `NewRunPage.tsx`, `RunDetailPage.tsx`, `ViewerPage.tsx`
  tobb ponton nyers `err.message` vagy `run.error_message` stringet jelenit meg.
- A jelenlegi viselkedes hasznos debughoz, de nem eleg user-facing contract freeze-hez.

### 3.5 Current-gap summary
- Van stabil technical code truth (DXF/GEO), de nincs explicit user-facing
  title/message/suggested_action contract.
- Nincs kulon policy a raw technical details elkulonitesere a user-level
  kommunikaciotol.

## 4. Future canonical DXF prefilter error catalog (V1, docs-level)

### 4.1 Canonical category family
| Kategoria | Leiras | Current truth anchor | V1 status |
| --- | --- | --- | --- |
| `file_ingest_upload_boundary` | Upload path/hash/bucket boundary hibak | `api/routes/files.py` ingest flow | Canonical |
| `dxf_parse_readability_unsupported` | DXF beolvasas/unsupported input hibak | `DxfImportError` `DXF_*` | Canonical |
| `contour_topology_layer_contract` | Layer/contour/topology contract hibak | importer + validator `GEO_*` | Canonical |
| `repair_policy` | Auto-repair ambiguities/gap policy hibak | T3 policy + importer fail-fast | Canonical |
| `acceptance_gate` | Prefilter acceptance/reject gate hibak | T1/T4 acceptance boundary | Canonical |
| `geometry_validation` | Canonical geometry validator issue-k | `geometry_validation_report.py` | Canonical |
| `review_required` | Nem blokkolo, de review-t igenylo allapot | T4 `preflight_review_required` | Canonical |
| `replace_rerun_info` | Replace/rerun informacios/warning allapotok | files/runs flow mintak | Canonical (info/warn) |

### 4.2 Minimum catalog-item contract
Minden canonical catalog elem minimum mezoi:
- `code`: stabil, machine-searchable kulcs.
- `severity`: `error` | `warning` | `info` | `review_required`.
- `title`: rovid user-facing cim.
- `user_message`: emberi nyelvu magyarazo uzenet.
- `suggested_action`: konkret kovetkezo lepes usernek.
- `debug_evidence_source`: hivatkozas a technical forrasra (module, raw code,
  path/details context).
- opcionais `support_notes`: support/internal triage segedmegjegyzes.

### 4.3 Severity/presentation elvek (docs-level)
- `error`: blokkolo allapot; folyamat nem mehet tovabb automatikusan.
- `warning`: nem feltetlen blokkolo; tovabblepes policy-fuggo figyelmeztetessel.
- `info`: informacios allapot, nincs blocker szerep.
- `review_required`: explicit emberi dontest kero allapot (nem azonos a hard errorral).

## 5. User-facing vs technical/debug evidence separation
- A `user_message` NEM azonos a nyers technical exception szoveggel.
- UI-ban rovid, kontextusos `title + user_message + suggested_action` jelenjen meg.
- Nyers technical reszletek (`raw code`, `path`, `details`, stack-kozel info)
  kulon diagnostics/support evidence retegben maradjanak.
- Support/debug celra a `debug_evidence_source` mezo kotelezoen visszavezessen
  a valos forraskodra es issue payloadra.

## 6. Grounded mapping examples (current -> canonical)

| Current source code | Current source module | Canonical severity | User-facing title | User-facing message (HU) | Suggested action | Debug evidence source |
| --- | --- | --- | --- | --- | --- | --- |
| `DXF_NO_OUTER_LAYER` | `vrs_nesting/dxf/importer.py` | `error` | Hianyzik a kulso kontur | Nem talalhato ervenyes, zart kulso kontur a vart retegen. | Ellenorizd a `CUT_OUTER` reteget es hogy legalabb egy zart kontur legyen rajta. | `importer DxfImportError.code + outer layer context` |
| `DXF_OPEN_OUTER_PATH` | `vrs_nesting/dxf/importer.py` | `error` | Nyitott kulso kontur | A kulso kontur nyitott, ezert a preflight nem tudja elfogadni a fajlt. | Zard le a kulso vagokonturt es exportalj uj DXF-et. | `importer code + layer path` |
| `DXF_OPEN_INNER_PATH` | `vrs_nesting/dxf/importer.py` | `error` | Nyitott belso kontur | A belso konturok kozul legalabb egy nyitott. | Zard le a belso kivagas konturokat (`CUT_INNER`). | `importer code + inner layer path` |
| `DXF_MULTIPLE_OUTERS` | `vrs_nesting/dxf/importer.py` | `review_required` | Tobb kulso kontur | A fajl tobb kulso konturt tartalmaz, ez ambiguus eset. | Valaszd szet a geometriat kulon fajlokra vagy jelold ki egyertelmuen az egy fo kulso konturt. | `importer code + contour count evidence` |
| `DXF_UNSUPPORTED_ENTITY_TYPE` | `vrs_nesting/dxf/importer.py` | `error` | Nem tamogatott DXF elem | A fajl nem tamogatott entity tipust tartalmaz. | Konvertald a nem tamogatott elemeket tamogatott gorbe/poliline tipusra. | `importer code + entity type` |
| `DXF_UNSUPPORTED_UNITS` | `vrs_nesting/dxf/importer.py` | `error` | Nem tamogatott mertekegyseg | A DXF INSUNITS ertek nem tamogatott vagy ervenytelen. | Exportalj mm-ben vagy tamogatott INSUNITS beallitassal. | `importer code + INSUNITS raw value` |
| `GEO_CANONICAL_MISSING` | `api/services/geometry_validation_report.py` | `error` | Hianyzik a canonical geometria | A validaciohoz szukseges canonical geometria hianyzik. | Ismeteld meg az importot vagy ellenorizd a forrasfajlt. | `validation issue code/path` |
| `GEO_HOLE_OUTSIDE_OUTER` | `api/services/geometry_validation_report.py` | `error` | Belsokontur kivul esik | Egy vagy tobb belsokontur a kulso konturon kivul helyezkedik el. | Javitsd a konturok topologiajat a forras DXF-ben. | `validation issue code + hole index path` |
| `GEO_BBOX_ROW_MISMATCH` | `api/services/geometry_validation_report.py` | `warning` | Geometria merethatar elteres | A tarolt merethatar es a szamitott geometria eltér. | Ellenorizd az import-forrast; ha szukseges, futtasd ujra a normalizalast. | `validation issue code + computed bbox details` |
| `GEO_CANONICAL_HASH_MISMATCH` | `api/services/geometry_validation_report.py` | `error` | Geometria integritas hiba | A canonical hash nem egyezik a geometriaval. | Ujraimportalas es forrasintegritas ellenorzes szukseges. | `validation issue code + expected/actual hash` |
| `GEO_SOURCE_LINEAGE_MISSING` | `api/services/geometry_validation_report.py` | `warning` | Hianyos lineage adat | Hianyzik a source lineage metaadat. | Ellenorizd a pipeline metaadat generator lepeset. | `validation issue code/path` |

## 7. Kapcsolat T4/T5/T6 contractokkal
- T4 state machine miatt kulon kell kezelni a `review_required` es a hard
  `error/rejected` jellegu allapotokat.
- T5 data-model contract mar kijeloli a strukturalt diagnostics persistence
  alapot (`severity`, `code`, `message`, `path`, `details_jsonb`).
- T6 API contract mar kijeloli, hogy a diagnostics/artifact family a future
  preflight run read surface-ben jelenik meg.
- A fenti HTTP response schema konkretizalasa NEM T7 scope.

## 8. Explicit anti-scope lista
- Nincs backend translator/service implementacio.
- Nincs `api/services/*.py` vagy `api/routes/*.py` modositas.
- Nincs frontend page/component modositas.
- Nincs OpenAPI response schema vagy error payload implementacios definicio.
- Nincs localization/i18n rendszer implementacios tervezese.
- Nincs support tooling implementacio.

## 9. Later extension jeloltek (nem V1 minimum)
- Lokalizalt message registry (HU/EN) kulon domainben.
- Domain-specific support playbook linkeles catalog-item szinten.
- Error telemetry aggregation dashboard.
- Cross-run failure pattern clustering.

## 10. Bizonyitek forrasok
- `docs/error_code_catalog.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `api/services/geometry_validation_report.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/ViewerPage.tsx`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
