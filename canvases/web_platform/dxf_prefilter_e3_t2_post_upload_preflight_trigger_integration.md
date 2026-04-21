# DXF Prefilter E3-T2 — Upload utani preflight trigger bekotes

## Cel
A DXF prefilter lane-ben az E3-T1-ben mar perzisztalhato local T1->T7 truth most
kapjon vegre **valodi upload utani trigger bekotest** a meglevo `complete_upload`
flow-ba ugy, hogy egy sikeres `source_dxf` finalize utan a rendszer automatikusan
elinditsa a teljes preflight lancot:
- T1 inspect
- T2 role resolver
- T3 gap repair
- T4 duplicate dedupe
- T5 normalized DXF writer
- T6 acceptance gate
- T7 diagnostics renderer
- E3-T1 persistence

A task celja **nem** uj API surface, nem explicit manual start endpoint es nem
geometry import gate, hanem az, hogy a mai `files.py` finalize flow-bol mar
letezo background-task mintaval elinduljon a preflight futas, es annak eredmenye
persistalt truth-va valjon.

## Miert most?
A jelenlegi repo-grounded helyzet:
- `api/routes/files.py` ma `complete_upload` utan source DXF-re ket background taskot indit:
  - `import_source_dxf_geometry_revision_async(...)`
  - `validate_dxf_file_async(...)`
- az E2-T1..T7 lane mar megadja a teljes local preflight truth-ot es renderer summary-t;
- az E3-T1 mar megadja a minimalis persistence + artifact storage bridge-et;
- de jelenleg nincs olyan service vagy trigger, amely a feltoltott forrasfajlt
  tenylegesen vegigvinné a preflight lancon es a vegen perzisztalna az eredmenyt.

Ha ezt most nem kotjuk be, akkor az E3-T1 persistence domain tovabbra is csak
helyi helper marad, es a preflight lane nem lep be a valos upload flow-ba.

A helyes sorrend ezert:
1. E3-T1: persistence + artifact storage truth
2. **E3-T2: upload utani trigger + orchestration**
3. E3-T3: geometry import gate
4. kesobb API/UI/polling/review/action retegek

## Scope boundary

### In-scope
- Kulon backend runtime/orchestration service a teljes T1->T7 + E3-T1 lanc
  vegigfuttatasara egy uploaded source DXF-bol.
- A runtime service a source DXF-et a storage-bol tolti le temp path-ra, majd
  futtatja a meglevo E2 service-eket es az E3-T1 persistence bridge-et.
- A `complete_upload` route bekotese ugy, hogy `source_dxf` + `.dxf` finalize utan
  automatikusan kapjon egy uj preflight background taskot.
- Determinisztikus `run_seq` eloallitas a mar letezo `app.preflight_runs` truth-bol.
- Minimalis hibaturo trigger viselkedes: a background preflight hiba ne torje el a
  `complete_upload` HTTP valaszt, hanem logolodjon es ahol lehet, persisted failed truth-va valjon.
- Task-specifikus unit teszt es smoke a runtime/orchestration + route trigger integraciora.

### Out-of-scope
- Uj FastAPI endpoint explicit preflight inditasra.
- Geometry import gate vagy a meglevo geometry import trigger eltavolitasa/atkotese.
- Frontend, polling, diagnostics drawer, review modal.
- Feature flag / rollout gate (`DXF_PREFLIGHT_REQUIRED`) — ez E3-T5 scope.
- Signed artifact list/url/download route.
- Full rules-profile domain (`dxf_rules_profiles`, `dxf_rules_profile_versions`).
- Worker queue / lease / polling orchestration; a trigger itt meg `BackgroundTasks`-ra ul.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/routes/files.py`
  - current-code truth: a `complete_upload` source DXF-re ma geometry import + legacy DXF validation
    background taskot ad hozza; a route response shape mar stabil.
- `api/services/file_ingest_metadata.py`
  - current-code truth: signed download helper mar letezik (`download_storage_object_blob`).
- `api/services/dxf_preflight_inspect.py`
  - T1 entrypoint: `inspect_dxf_source(source_path)`.
- `api/services/dxf_preflight_role_resolver.py`
  - T2 entrypoint: `resolve_dxf_roles(inspect_result, rules_profile=None)`.
- `api/services/dxf_preflight_gap_repair.py`
  - T3 entrypoint: `repair_dxf_gaps(inspect_result, role_resolution, rules_profile=None)`.
- `api/services/dxf_preflight_duplicate_dedupe.py`
  - T4 entrypoint: `dedupe_dxf_duplicate_contours(...)`.
- `api/services/dxf_preflight_normalized_dxf_writer.py`
  - T5 entrypoint: `write_normalized_dxf(..., output_path=..., rules_profile=None)`.
- `api/services/dxf_preflight_acceptance_gate.py`
  - T6 entrypoint: `evaluate_dxf_prefilter_acceptance_gate(...)`.
- `api/services/dxf_preflight_diagnostics_renderer.py`
  - T7 entrypoint: `render_dxf_preflight_diagnostics_summary(...)`.
- `api/services/dxf_preflight_persistence.py`
  - E3-T1 truth: `persist_preflight_run(...)` + canonical artifact storage path.
- `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql`
  - current-code truth: `app.preflight_runs` / diagnostics / artifacts mar leteznek.

## Jelenlegi repo-grounded helyzetkep

### 1. A trigger helye egyertelmu: `complete_upload`
A V1 scope freeze es a mai kod is ugyanarra mutat:
- a DXF prefilter a file upload finalize utan,
- de a geometry import elott lenne a vegso cel.

Current-code szinten viszont a geometry import mar ma is automatikus background task.
Az E3-T2 **nem** gate task, ezert most a helyes minimalis-invaziv irany:
- a geometry import es a legacy validation task maradjon bent,
- mellejuk jojjon be a preflight trigger,
- a gate csak E3-T3-ban koveti.

### 2. A teljes preflight lanc mar local service-ekbol osszerakhato
A T1->T7 E2 lane mar stabil service boundaryket ad.
Ezert a T2-ben **nem** uj parserre vagy uj validatorra van szukseg,
hanem egyetlen runtime service-re, amely a meglevo service-eket a megfelelo
sorrendben meghivja.

### 3. A rules-profile domain tovabbra sem letezik
Mivel current-code szinten nincs formal rules-profile domain es nincs project-level
active rules selection route sem, a T2-ben a runtime service V1 bridge-kent
`rules_profile=None` / `{}` alaptruth-tal fusson.
Ne talalj ki most dxf-rules selection API-t vagy FK domaint csak a trigger miatt.

### 4. A persistence bridge ma terminalis snapshot helper
Az E3-T1 `persist_preflight_run(...)` mar jo a vegallapot truth perzisztalasara.
A T2 feladata nem ennek atirasa teljes lifecycle engine-re, hanem az, hogy a
runtime service a futas vegen meghivja.
Ha a lanc a summary eloallitas elott szakad meg, akkor a T2 feladata legalabb egy
minimalis failed run truth vagy egyertelmu server log jel letrehozasa — de ettol
meg nem valik pollolhato workflow engine-ne.

### 5. A trigger itt meg FastAPI `BackgroundTasks`-ra ul
A repo current-code upload finalize flow mar ma is ezt a mintat hasznalja.
A T2 ne vezessen be worker queue-t, outboxot vagy kulon task buszt.

## Konkret elvarasok

### 1. Kulon runtime/orchestration service szülessen
Hozz letre kulon service reteget, peldaul:
- `api/services/dxf_preflight_runtime.py`

A service felelossege:
- a source DXF letoltese storage-bol temp file-ba;
- a teljes E2/T7 lanc sorrendi vegigfuttatasa a meglevo publikus service-ekkel;
- local normalized artifact path kijelolese temp diren belul;
- a T7 summary eloallitasa;
- az E3-T1 persistence meghivasa;
- determinisztikus eredmeny / log summary visszaadasa.

Kritikus boundary:
- ne legyen FastAPI route;
- ne csinaljon geometry import gate-et;
- ne implementaljon explicit artifact list/url API-t;
- ne duplikalja az E2/T7 logikat.

### 2. A route trigger a meglevo `complete_upload` mintara epuljon
A `api/routes/files.py` `complete_upload` route-ban source DXF finalize utan
kapjon uj `background_tasks.add_task(...)` hivast a preflight runtime service-re.

Fontos current-code elv:
- a route response shape ne valtozzon;
- a meglevo geometry import task ne tunjon el;
- a meglevo legacy readability check se tunjon el.

A minimalis-invaziv default sorrend:
1. geometry import task (meglevo)
2. legacy readability check (meglevo)
3. uj preflight runtime trigger

Indok:
- igy a T2 nem valtoztatja meg a mai geometry import viselkedeset;
- a preflight trigger parallel koveto truth-kent jon be;
- a valodi gate logika kulon taskban nyilik meg.

### 3. A runtime a forrasfajlt a storage truth-bol dolgozza fel
A trigger ne kliens payloadra es ne local fajlrendszerre epitkezzen.
A runtime minimum ezeket a canonical truthokat kapja:
- `project_id`
- `source_file_object_id`
- `storage_bucket`
- `storage_path`
- `source_hash_sha256`
- `created_by`
- `signed_url_ttl_s`

A source DXF-et a mar letezo `download_storage_object_blob(...)` helperrel toltsd le.

### 4. A `run_seq` deterministic legyen es ne kliens inputbol jojjon
Az E3-T1 report kulon kiemelte, hogy a `run_seq` ma meg caller-driven.
A T2-ben ezt a runtime/orchestration layernek kell elvallalnia.

Minimum elvart logika:
- `app.preflight_runs`-bol az adott `source_file_object_id`-ra kerje le a legnagyobb `run_seq`-et,
- es a kovetkezo run a `max + 1` legyen.

Boundary:
- most meg nem kell DB sequence vagy trigger;
- eleg deterministic service-side lekero logika.

### 5. A T2 ne talaljon ki uj project-level rules selection domaint
Mivel current-code szinten nincs rules-profile CRUD/selection implementacio,
T2-ben a runtime service V1 bridge-kent fusson `rules_profile=None`-nal,
vagy explicit ures snapshotot adjon tovabb a persistence-nek.

A task ne modositson:
- `api/routes/project_*selection.py`
- `api/routes/*rules*`
- `api/request_models.py`

### 6. Minimalis failure handling legyen, de ne nyisson polling/workflow scope-ot
A background preflight barmely ponton elhasalhat:
- source download hiba,
- inspect/runtime exception,
- persistence/storage hiba.

A T2-ben minimum legyen:
- egy kulon runtime exception boundary,
- strukturalt logger output `project_id`, `source_file_object_id`, `storage_path` kontextussal,
- ahol lehet, egy minimalis `preflight_failed` run truth.

De explicit anti-scope:
- nincs retry queue,
- nincs heartbeat,
- nincs progress polling,
- nincs `preflight_pending` / `preflight_running` teljes lifecycle UI.

### 7. A teszteles kulon bizonyitsa a route trigger es a runtime lancot
Minimum deterministic coverage:

#### Runtime unit teszt
- a runtime a meglevo E2/T7 service-eket sorrendben hivja;
- accepted flow -> persistence meghivodik;
- runtime hiba -> failure logika aktiv;
- `run_seq` a DB truth-bol jon;
- rules profile default current-code kompatibilis (`None` vagy `{}`).

#### Route integration smoke / test
- `complete_upload` source DXF eseten 3 background taskot regisztral:
  geometry import + legacy validate + preflight runtime;
- nem-source_dxf vagy nem `.dxf` finalize nem kap preflight taskot;
- a route response ugyanaz marad, mint korabban.

### 8. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- **E3-T3**: geometry import gate, vagyis rejectelt/review-required fajl ne mehessen tovabb geometry importba;
- **E3-T4**: replace file es rerun flow;
- **E3-T5**: feature flag / rollout gate;
- kesobbi taskok: explicit preflight route-csalad, artifact list/url/download, review-decision persistence, UI.

## Javasolt implementacios szelet

### Uj vagy modositando kodfajlok
- `api/services/dxf_preflight_runtime.py`  **(uj)**
- `api/routes/files.py` **(modositando)**
- opcionálisan minimalis helper-bovites ugyanebben a taskban, ha a runtime-nak kell:
  - `api/services/dxf_preflight_persistence.py`

### Tesztek / smoke
- `tests/test_dxf_preflight_runtime.py` **(uj)**
- `scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py` **(uj)**

## DoD
- Egy source DXF `complete_upload` utan a route mar tenylegesen regisztralja az uj preflight background taskot.
- A preflight runtime a meglevo E2/T7 + E3-T1 service-ekbol vegig tudja futtatni a local lancot.
- A `run_seq` deterministic service-side truth-bol jon.
- A route response shape nem valtozik.
- A geometry import trigger meg nem gate-elodik es nem tunik el.
- Keszul deterministic unit teszt es smoke.
- A standard repo gate zoldre fut.

## Kotelezo ellenorzesek
- `python3 -m py_compile api/services/dxf_preflight_runtime.py tests/test_dxf_preflight_runtime.py scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_dxf_preflight_runtime.py`
- `python3 scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
