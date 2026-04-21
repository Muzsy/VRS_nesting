# DXF Prefilter E3-T3 — Geometry import gate bekotes

## Cel
A DXF prefilter lane-ben az E3-T2 ota a `complete_upload` mar automatikusan
elinditja a teljes preflight runtime lancot, de a geometry import ma meg mindig
**kozvetlenul a route-bol**, a nyers source DXF-re indul.

Az E3-T3 celja, hogy a geometry import mostantol **csak gate-pass utan** fusson:
- csak akkor indulhat geometry import,
- ha a preflight persisted kimenete `accepted_for_import`,
- es a T5/E3-T1 lane mar letrehozott egy tenyleges `normalized_dxf` artifact storage truth-ot.

A task celja **nem** uj API route, nem review-flow, nem replace/rerun, nem
feature flag, hanem a jelenlegi upload -> preflight -> import sorrend tenyleges,
repo-grounded atkotese ugy, hogy a geometry import mar ne tudja megkerulni a
prefilter acceptance gate-et.

## Miert most?
A jelenlegi repo-grounded helyzet:
- `api/routes/files.py` `complete_upload` source DXF-re ma is harom background taskot indit:
  - `import_source_dxf_geometry_revision_async(...)`
  - `validate_dxf_file_async(...)`
  - `run_preflight_for_upload(...)`
- az E2-T6 acceptance gate mar explicit canonical verdictet ad:
  - `accepted_for_import`
  - `preflight_rejected`
  - `preflight_review_required`
- az E3-T1 persistence mar explicit `preflight_artifacts` truth-ot tarol,
  benne a canonical `normalized_dxf` storage bucket/path referenciaval;
- az E3-T2 runtime mar birtokolja egyszerre:
  - a source file truth-ot,
  - az acceptance outcome-ot,
  - es a persisted artifact ref-eket.

Ettol fuggetlenul a geometry import ma meg **nem gate-elt**, mert a route-bol
parhuzamosan indul a nyers source DXF-re.

Ez ellentmond:
- az E1-T4 state machine-nek (`accepted_for_import` -> `imported`),
- az E1 V1 scope freeze-nek,
- es a T6 acceptance gate gyakorlati celjanak.

Ezert a helyes sorrend most:
1. E3-T1: persistence + artifact storage truth
2. E3-T2: upload utani preflight trigger
3. **E3-T3: geometry import gate**
4. kesobb explicit preflight API, replace/rerun, feature flag, UI

## Scope boundary

### In-scope
- A `complete_upload` route-bol a kozvetlen geometry import background task
  eltavolitasa source DXF finalize eseten.
- A geometry import bekotese a **preflight runtime utan**, es csak gate-pass
  eseten.
- A geometry import inputjanak atallitasa a persisted `normalized_dxf`
  artifact storage truth-ra, nem a nyers source DXF-re.
- Minimalis, current-code kompatibilis geometry import helper boundary, hogy a
  storage-backed normalized artifact ugyanazzal a geometry import pipeline-nal
  beolvashato legyen.
- Determinisztikus teszt es smoke coverage a gateelt import triggerre.

### Out-of-scope
- Uj FastAPI endpoint vagy explicit manualis preflight inditas.
- Review decision workflow.
- Replace file / rerun flow (E3-T4).
- Feature flag / rollout gate (E3-T5).
- Frontend vagy polling UI.
- Uj rules-profile domain.
- Teljes `imported` lifecycle persistence modell vagy uj migration csak azert,
  hogy a bridge allapotot kulon statuszkent taroljuk.
- Geometry validation / derivative generator logika ujrairasa vagy duplikalasa.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/routes/files.py`
  - current-code truth: source DXF finalize utan geometry import + legacy validation + preflight runtime task indul.
- `api/services/dxf_preflight_runtime.py`
  - current-code truth: a T1->T7 + E3-T1 pipeline mar vegigfut es persisted summary truth-ot ad.
- `api/services/dxf_preflight_persistence.py`
  - current-code truth: a persisted result `artifact_refs` listaban explicit `normalized_dxf` storage truth van.
- `api/services/dxf_preflight_acceptance_gate.py`
  - canonical acceptance outcome truth.
- `api/services/dxf_geometry_import.py`
  - meglevo geometry import pipeline: importer -> canonical geometry -> validation report -> derivatives.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - docs-level truth: `accepted_for_import` utan kovetkezik az import bridge.
- `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
  - current scope freeze: E3-T2-ben a geometry import trigger meg szandekosan bent maradt a route-ban.

## Jelenlegi repo-grounded helyzetkep

### 1. A gate ma megkerulheto
A `complete_upload` route source DXF-re ma azonnal geometry importot indit.
Ez azt jelenti, hogy a raw source DXF parse/validation mar akkor lefuthat,
mielott a preflight acceptance outcome egyaltalan megszuletne.

Ez a legfontosabb bizonyitott hiba a mai integracioban.

### 2. A runtime mar minden szukseges truth-ot ismer
Az E3-T2 runtime a pipeline vegen mar tudja:
- az acceptance outcome-ot,
- a persisted `preflight_run_id`-t,
- az artifact ref-eket,
- a source file object id-t,
- az eredeti `source_hash_sha256` truth-ot,
- a `project_id` / `created_by` / signed-url TTL kornyezetet.

Ez azt jelenti, hogy a geometry import gate-et **nem a route-ban**, hanem a
runtime vegen kell bekotni.

### 3. A geometry importnak a normalized DXF-re kell atallnia
A T6 acceptance gate eppen azt bizonyitja, hogy a T5 normalized DXF artifact
megy at az importer+validator probe-on.

Ha a T3 ezutan meg mindig a nyers source DXF-re inditana geometry importot,
az gate szemantikailag ures lenne.

Ezert az E3-T3 helyes current-code truth-ja:
- geometry import input = persisted `normalized_dxf` artifact storage ref
- source linkage = ugyanaz a `source_file_object_id`, mint az uploadolt fajle
- `source_hash_sha256` = marad az eredeti source file truth, ne talaljunk ki uj mezot

### 4. A geometry import pipeline-t nem szabad lemásolni
A `api/services/dxf_geometry_import.py` ma mar elvegzi:
- a storage downloadot,
- az importer probe-ot,
- a canonical geometry normalizalast,
- a validator hivasat,
- a derivative generalast.

Az E3-T3-ben nem uj import pipeline kell, hanem egy **gateelt trigger bridge**.
Ha szukseges, csak minimalis helper-nyitas vagy generic storage-import boundary nyithato.

### 5. A legacy file-level validation maradhat secondary signal
A `validate_dxf_file_async(...)` tovabbra is maradhat a route-ban.
Ez nem geometry truth, csak secondary readability signal.
A task ne torje el ezt a jelenlegi viselkedest.

## Konkret elvarasok

### 1. A geometry import keruljon ki a route-bol
A `api/routes/files.py` `complete_upload` source DXF finalize utan
**ne** regisztralja tobbe kozvetlenul az
`import_source_dxf_geometry_revision_async(...)` background taskot.

A route-ban source DXF-re ez maradjon:
1. `validate_dxf_file_async(...)`
2. `run_preflight_for_upload(...)`

A response shape maradjon valtozatlan.

### 2. A runtime a persisted acceptance outcome utan triggerelje az importot
Az `api/services/dxf_preflight_runtime.py` feladata bovuljon ugy, hogy:
- a T1->T7 + E3-T1 persistence utan ellenorizze a persisted acceptance outcome-ot,
- csak `accepted_for_import` esetben menjen tovabb geometry importra,
- `preflight_rejected` / `preflight_review_required` eseten explicit skip/log legyen,
- import fail eseten logger warning legyen, de ne torje el a `complete_upload` HTTP valaszt.

Fontos boundary:
- a T3 nem teszi workflow engine-ne a runtime-ot,
- nincs retry/polling,
- nincs uj DB lifecycle state.

### 3. A gate a persisted `normalized_dxf` artifact ref-bol dolgozzon
A geometry importhoz a runtime ne local temp pathot es ne a nyers source DXF-et
hasznalja, hanem az E3-T1 persisted artifact truth-ot.

Minimum elvart shape:
- artifact kind = `normalized_dxf`
- explicit `storage_bucket`
- explicit `storage_path`

Ha ez hianyzik accepted outcome mellett, az logger warning + skip legyen,
ne csendes siker es ne nyers source fallback.

### 4. Minimalis geometry-import helper boundary nyithato
Ha a jelenlegi `api/services/dxf_geometry_import.py` helpernevei vagy parameter
szerzodesei tulzottan `source`-kozpontuak, akkor current-scope kompatibilis
minimalis helper nyitas megengedett.

Javasolt irany:
- legyen egy generic storage-backed import helper, amely tetszoleges DXF storage ref-bol
  futtatja a meglevo import pipeline-t,
- az eddigi `import_source_dxf_geometry_revision(...)` delegalhat erre,
- a gateelt runtime pedig ugyanennek a helpernek a normalized artifact ref-et adja.

Anti-scope:
- ne epits uj canonical geometry pipeline-t,
- ne masold at a validator/derivative logikat mas service-be.

### 5. A T3 ne nyisson uj persistence domaint
Az E3-T3-ben ne keszuljon:
- uj migration csak `imported` bridge statuszhoz,
- uj `preflight_run` oszlop,
- kulon import bridge tabla,
- artifact url/download API.

Ha kell helyi summary truth a runtime-ban, az legyen csak logger vagy in-memory
return shape, ne schema-bovites.

### 6. A tesztek kulon bizonyitsak a gate szemantikat
Minimum deterministic coverage:

#### Unit teszt
- accepted outcome + normalized artifact ref -> geometry import helper hivodik egyszer
- rejected outcome -> geometry import helper nem hivodik
- review_required outcome -> geometry import helper nem hivodik
- accepted, de nincs normalized artifact ref -> skip + no import
- geometry import helper exception -> logger warning / swallowed error
- route mar nem regisztral kozvetlen geometry import background taskot

#### Smoke
- a route source DXF-re mar csak 2 background taskot rak fel
  (legacy validation + preflight runtime)
- a runtime gate helper scenario-kon vegigmegy:
  accepted/import, rejected/skip, review/skip, missing artifact/skip

### 7. Mi marad kesobbi scope-ban
- **E3-T4**: replace file es rerun flow
- **E3-T5**: feature flag / rollout gate
- kesobbi explicit preflight routes:
  - list/detail/artifact URL/download
  - review-decision persistence
  - rules-profile domain formal implementacio
- kesobbi lifecycle/polling/UI truth az `imported` bridge allapotrol

## DoD
- [ ] A `complete_upload` route source DXF eseten mar nem indit kozvetlen geometry import background taskot.
- [ ] A preflight runtime csak `accepted_for_import` eseten triggerel geometry importot.
- [ ] A trigger a persisted `normalized_dxf` artifact storage truth-ot hasznalja, nem a nyers source DXF-et.
- [ ] A legacy `validate_dxf_file_async(...)` task bent marad secondary signalkent.
- [ ] A geometry import pipeline nincs duplikalva; csak minimalis helper/gate integration keszul.
- [ ] Determinisztikus unit teszt es smoke bizonyitja a gate szemantikat.
- [ ] A standard repo gate wrapperrel fut es a report evidence alapon frissul.
