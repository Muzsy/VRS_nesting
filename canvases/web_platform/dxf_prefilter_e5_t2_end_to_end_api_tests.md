# DXF Prefilter E5-T2 — End-to-end API tesztek

## Cel
Az E3-T1→T3 es E4-T1→T4 utan a repo current-code truth mar ez:
- a DXF preflight a `complete_upload(...)` finalize route utan indul background taskkent;
- a runtime a teljes T1→T7 + E3-T1→T3 lancot lefuttatja;
- a geometry import mar gate-elt, es csak `accepted_for_import` kimenetnel indul tovabb;
- a file list route optional summary/diagnostics projectiont tud visszaadni a persisted `preflight_runs.summary_jsonb` alapjan;
- a `DxfIntakePage` ezt a file-list projectiont fogyasztja.

Az E5-T2 celja nem uj product logika, hanem annak bizonyitasa, hogy a **feltoltes finalize-tol az acceptance gate-ig, illetve a file-list API projectionig** a lanc API-szinten ismetelhetoen vegigmegy.

Ez a task tehat egy **uj, onallo end-to-end API teszt pack**, amely a jelenlegi route + background runtime + persistence + projection vilagot egyben ellenorzi.

## Miert most?
A repo-grounded helyzet jelenleg:
- E5-T1 mar rogzitette a T1→T6 core pipeline truthot fixture-driven unit packkent;
- az E3/E4 taskok kulon-kulon mar tesztelik a route hidat, a persistence reget, a trigger bekotest, a geometry import gate-et, a summary/diagnostics projectiont es az intake oldali fogyasztast;
- viszont nincs egyetlen olyan tesztpack, amely ugyanazon helperrel bizonyitja, hogy a **`complete_upload -> BackgroundTasks -> run_preflight_for_upload -> persist -> optional geometry import -> list_project_files`** API-lanc egyben is mukodik.

A helyes E5-T2 scope ezert:
**uj, additive end-to-end API pack a jelenlegi finalize + runtime + list projection lancra, uj endpoint vagy UI scope nyitasa nelkul.**

## Scope boundary

### In-scope
- Uj, dedikalt pytest file az API-level E2E preflight lancra.
- Route-level current-code truth szerinti teszteles:
  - `complete_upload(...)`
  - `BackgroundTasks`
  - `run_preflight_for_upload(...)`
  - `list_project_files(...)`
- Fake Supabase / fake storage boundary a route + runtime + persistence + projection egyben tesztelesehez.
- Minimum scenario-k:
  - accepted flow,
  - lenient review_required flow,
  - strict rejected flow.
- Rules-profile snapshot bridge bizonyitasa ugyanebben az E2E lancban.
- Geometry import gate bizonyitasa az accepted vs non-accepted kimeneteknel.
- Summary + diagnostics projection bizonyitasa ugyanazon API-flow vegpontjan.
- Task-specifikus structural smoke.
- Checklist + report evidence frissitese.

### Out-of-scope
- Uj dedikalt `POST /projects/{project_id}/files/{file_id}/preflight` endpoint.
- Uj historical `GET /preflight-runs/{id}` vagy artifact download endpoint.
- FastAPI `TestClient` / ASGI full-stack teszt, ha a jelenlegi route-callable stilus eleg.
- UI / Playwright / browser scope.
- E3-T4 replace-file, E3-T5 feature flag, E4-T5/T6/T7 scope.
- Production service refaktor csak a teszt kenyelme miatt.

## Talalt relevans fajlok (meglevo kodhelyzet)
- Route entry es projection:
  - `api/routes/files.py`
- Runtime/orchestration:
  - `api/services/dxf_preflight_runtime.py`
- Persistence:
  - `api/services/dxf_preflight_persistence.py`
- Geometry import gate (runtime vegi trigger):
  - `api/services/dxf_geometry_import.py`
  - `api/services/dxf_preflight_runtime.py`
- Meglevo route/runtime/projection tesztek:
  - `tests/test_dxf_preflight_runtime.py`
  - `tests/test_dxf_preflight_geometry_import_gate.py`
  - `tests/test_project_file_complete_preflight_settings.py`
  - `tests/test_project_files_preflight_summary.py`
  - `tests/test_project_files_preflight_diagnostics.py`
- E5-T1 core regression pack:
  - `tests/test_dxf_preflight_core_unit_pack.py`
- UI oldali fogyasztas current-code truthkent:
  - `frontend/src/pages/DxfIntakePage.tsx`

## Jelenlegi repo-grounded helyzetkep

### 1. Nincs kulon manualis preflight API entrypoint
A mai repo-ban a preflight nem kulon route-on indul, hanem a `complete_upload(...)` finalize utan background taskkent. Ezert az E5-T2 helyes belépési pontja **nem** egy kitalalt `/preflight` endpoint, hanem a jelenlegi finalize route.

### 2. A repo route-teszt mintaja direct callable + fake deps
A jelenlegi preflight route-level tesztek nem `TestClient`-re, hanem direct route hivásra, fake `AuthenticatedUser`-re, fake Supabase-re es `BackgroundTasks`-ra epulnek. Az E5-T2 current-code truth szerint ezt a mintat kell kovetnie, nem teljes ASGI stack-et kitalalnia.

### 3. A route import-lanc jelenleg `ezdxf`-fuggo
A `files.py` import-lanc behozza a legacy `dxf_validation.py`-t, amely `ezdxf`-et igenyel. Emellett a T5/T6 writer/gate is valos DXF iras/olvasas miatt `ezdxf`-fuggo. Ezert az E5-T2 packnak ezt a dependency truthot explicit modon vallalnia kell, nem szabad elrejtenie.

### 4. Az E5-T2 ne irja ujra a meglevo route/runtime/projection teszteket
A repo-ban mar vannak jo, keskeny route/runtime/projection tesztek. Az E5-T2 helyes formaban nem replacement, hanem egy **osszefogo API-flow pack**, amely ugyanazon scenario-n belul tobb reteg bizonyitekat egyesiti.

## Konkret elvarasok

### 1. Szülessen uj, dedikalt API E2E pytest file
Javasolt uj fajl:
- `tests/test_dxf_preflight_api_end_to_end.py`

A file legyen onallo, sajat fake Supabase / storage helperrel. Ne refaktoralja most kozosre a meglevo E3/E4 route teszteket.

### 2. A pack a valodi finalize -> runtime -> projection lancra epuljon
Legyen benne helper, amely current-code truth szerint ezt csinalja:
1. `complete_upload(...)` route hivas fake userrel es `BackgroundTasks`-szal;
2. a route altal felvett `run_preflight_for_upload` task explicit lefuttatasa;
3. `list_project_files(...)` route hivas `include_preflight_summary=True` es `include_preflight_diagnostics=True` kapcsolokkal;
4. az eredmeny ellenorzese ugyanazon scenario teljes API-flow szintjen.

A helper adja vissza a kovetkezo truthokat is:
- background task registry,
- fake supabase persisted rows,
- geometry import trigger hivasai,
- list route response.

### 3. Minimum scenario matrix (current-code truth szerint)

#### a) Accepted flow
- egyszeru zart CUT_OUTER forras;
- `complete_upload` felveszi a `validate_dxf_file_async` + `run_preflight_for_upload` taskokat;
- a preflight persisted run acceptance outcome-ja `accepted_for_import`;
- normalized artifact ref keletkezik;
- geometry import trigger egyszer lefut;
- a file-list summary `ready_for_next_step` / accepted iranyt mutat;
- a diagnostics projection nem ures.

#### b) Lenient review_required flow
- olyan bemenet, amely current-code truth szerint lenient modban review_required-ot ad (pl. repair utani megmarado upstream review signal vagy role konfliktus);
- geometry import trigger **nem** fut;
- summary `preflight_review_required`-ot es ertelmes recommended action-t ad;
- diagnostics projection tartalmaz issue / repair / acceptance blokkot.

#### c) Strict rejected flow
- ugyanazon vagy hasonlo bemenet strict modban `preflight_rejected` kimenetet ad;
- geometry import trigger **nem** fut;
- summary rejected allapotot ad;
- diagnostics projection blocking reasonokat tartalmaz.

### 4. A pack current-code truth szerint vallalja az `ezdxf` dependency-t
A test file module szinten vallalja explicit modon az `ezdxf` dependency-t, peldaul:
- `pytest.importorskip("ezdxf")`

Ez itt nem kiskapu, hanem helyes dokumentalt truth:
- a route import-lanc mar ma is `ezdxf`-fuggo;
- a T5/T6 valos normalized DXF writer/gate is az.

### 5. A pack ne patch-elje szet a core pipeline-t
Az E5-T2 nem akkor ertekes, ha a T1→T7 pipeline egeszet `MagicMock`-okra csereli.
A helyes current-code mintazat:
- I/O seam patch megengedett:
  - `load_file_ingest_metadata`
  - `download_storage_object_blob`
  - geometry import side-effect recorder
- de a core preflight runtime hivas maradjon valodi:
  - inspect
  - role
  - gap
  - dedupe
  - writer
  - acceptance
  - diagnostics renderer
  - persistence

### 6. A fake Supabase / storage truth legyen egyben tesztelheto
A teszt helper current-code truth szerint kezelje legalabb ezeket:
- `app.projects`
- `app.file_objects`
- `app.preflight_runs`
- `app.preflight_diagnostics`
- `app.preflight_artifacts`
- signed upload url + upload payload capture a normalized artifact storage-hoz

Ez azert kell, hogy az E5-T2 ne csak route-outputot, hanem a persisted truthot is bizonyitsa.

### 7. Keszuljon task-specifikus smoke
Javasolt uj fajl:
- `scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`

A smoke minimum bizonyitsa:
- az uj API E2E pack file letezik;
- a file `complete_upload`, `BackgroundTasks`, `run_preflight_for_upload`, `list_project_files` truthra epul;
- explicit `ezdxf` guard szerepel;
- accepted / review_required / rejected scenario-k jelen vannak;
- nincs UI / Playwright / TestClient / uj endpoint scope.

### 8. Verifikacio
Minimum futtasok:
- `python3 -m py_compile tests/test_dxf_preflight_api_end_to_end.py scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`
- `python3 -m pytest -q tests/test_dxf_preflight_api_end_to_end.py`
- `python3 scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`

A report kulon terjen ki erre:
- miert a `complete_upload -> BackgroundTasks -> runtime -> list_project_files` a helyes current-code E2E API truth;
- mely scenario-kat fedi le a pack;
- hogyan bizonyitja a geometry import gate accepted vs non-accepted kulonbseget;
- miert explicit es helyes az `ezdxf` dependency vallalasa.
