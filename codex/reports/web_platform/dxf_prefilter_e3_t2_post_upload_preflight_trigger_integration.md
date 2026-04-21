PASS_WITH_NOTES

## 1) Meta
- Task slug: `dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration`
- Kapcsolodó canvas: `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- Kapcsolodó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.yaml`
- Futas datuma: `2026-04-21`
- Branch / commit: `main@3f49b58`
- Fokusz terulet: `Backend (upload trigger + orchestration only)`

## 2) Scope

### 2.1 Cel
- Kulon backend runtime/orchestration service a teljes T1→T7 + E3-T1 lanc vegigfuttatasara egy feltoltott source DXF-bol.
- `complete_upload` route bekotese ugy, hogy source DXF finalize utan uj preflight background task is regisztralodik.
- Determinisztikus `run_seq` eloallitas az `app.preflight_runs` truth-bol.
- Minimalis failure handling: strukturalt logger + minimalis failed run row.
- Task-specifikus unit teszt es smoke script deterministic, fake gateway alapon.

### 2.2 Nem-cel (explicit)
- Uj FastAPI endpoint explicit preflight inditasra.
- Geometry import gate vagy a meglevo geometry import trigger eltavolitasa/atkotese.
- Frontend, polling, diagnostics drawer, review modal.
- Feature flag / rollout gate (E3-T5 scope).
- Signed artifact list/url/download route.
- Full rules-profile domain.
- Worker queue / lease / polling orchestration.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok
- Uj runtime/orchestration service:
  - `api/services/dxf_preflight_runtime.py`
- Modositott route:
  - `api/routes/files.py`
- Bovitett persistence service:
  - `api/services/dxf_preflight_persistence.py`
- Tesztek / smoke:
  - `tests/test_dxf_preflight_runtime.py`
  - `scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
  - `codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`

### 3.2 Miert valtoztak?
Az E3-T1 utan mar letezik a persistence bridge, de nem volt olyan service, amely a feltoltott forrásbol vegigfuttatja a preflight lancot. Az E3-T2 ezt a gapet zarja le: a runtime service a meglevo E2/T7 + E3-T1 service-eket sorrendben hivja, a route pedig BackgroundTask-kent inditja el.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`

### 4.2 Opcionalis, feladatfuggo parancsok
- `python3 -m py_compile api/services/dxf_preflight_runtime.py tests/test_dxf_preflight_runtime.py scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py` → OK
- `python3 -m mypy --config-file mypy.ini api/services/dxf_preflight_runtime.py` → `Success: no issues found`
- `python3 -m pytest -q tests/test_dxf_preflight_runtime.py` → 11 passed
- `python3 scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py` → 9 scenario OK

### 4.3 Ha valami kimaradt
A verify.sh FAIL-t jelzett, de a hiba forrasa egy pre-existing nesting engine timeout-bound flakiness:
- `[NEST] Canonical JSON determinism smoke` — `time_limit_sec=1` timeout-keli fixture alatt a nesting engine kimenet nem determinisztikus (nem E3-T2 valtozas).
- A Python/mypy/DXF/Sparrow/vrs_solver retegek mind PASS-on zarultak.
- Lasd Advisory notes 1. pont.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Egy source DXF `complete_upload` utan a route mar tenylegesen regisztralja az uj preflight background taskot. | PASS | `api/routes/files.py:253-263` | `background_tasks.add_task(run_preflight_for_upload, ...)` hozzaadva a meglevo 2 task utan; `normalized_kind == "source_dxf"` + `.dxf` ext feltetelesiti. | `tests/test_dxf_preflight_runtime.py::test_pipeline_calls_all_steps_in_order`; smoke: `ROUTE TRIGGER COUNT` |
| A preflight runtime a meglevo E2/T7 + E3-T1 service-ekbol vegig tudja futtatni a local lancot. | PASS | `api/services/dxf_preflight_runtime.py:196-248` | `_execute_pipeline` sorrendi hivasa: inspect → roles → gap → dedupe → writer → gate → t7 → persist; a tmpdir garantalja, hogy a normalized DXF meg letezo, mikor persist hivodik. | `tests/test_dxf_preflight_runtime.py::test_pipeline_calls_all_steps_in_order`; smoke: `PIPELINE ORDER` |
| A `run_seq` deterministic service-side truth-bol jon. | PASS | `api/services/dxf_preflight_persistence.py:471`; `api/services/dxf_preflight_runtime.py:161` | `get_next_run_seq(source_file_object_id, db_query)` lekerdi `max(run_seq)` az `app.preflight_runs`-bol, +1-et ad vissza; a runtime ezt hivja es adja at `persist_preflight_run`-nak. | `tests/test_dxf_preflight_runtime.py::test_accepted_flow_persist_called_with_run_seq`; smoke: `RUN_SEQ FROM DB` |
| A route response shape nem valtozik. | PASS | `api/routes/files.py:276` | `return _as_file_response(row)` valtozatlan; csak a `background_tasks.add_task` blokk bovult. | `tests/test_dxf_preflight_runtime.py::test_pipeline_calls_all_steps_in_order` (smoke: `ROUTE TRIGGER COUNT` ellenorzi a response-shape-t nem ero modositast) |
| A geometry import trigger meg nem gate-elodik es nem tunik el. | PASS | `api/routes/files.py:252-263` | Az eredeti `import_source_dxf_geometry_revision_async` + `validate_dxf_file_async` background tasks valtozatlanul jelen vannak; az uj preflight task csak harmadiккant kovetkezett. | smoke: `ROUTE TRIGGER COUNT` (len(added)==3, geometry import es validate bent van) |
| Keszul deterministic unit teszt es smoke. | PASS | `tests/test_dxf_preflight_runtime.py:1`; `scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py:1` | 11 deterministic pytest unit teszt + 9 scenario smoke; mindketto fake gateway-jel (nincs valos Supabase-hivas). | `python3 -m pytest -q tests/test_dxf_preflight_runtime.py` (11 passed); `python3 scripts/smoke...` (9 OK) |
| A standard repo gate zoldre fut. | PASS_WITH_NOTES | `codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.verify.log` | Python/mypy/DXF/Sparrow/vrs_solver PASS; verify.sh FAIL-t jelzett pre-existing nesting engine timeout-bound canonical JSON determinism flakiness miatt (`time_limit_sec=1`), ami az E3-T2 valtozasoktol teljesen fuggetlenul fennall. | Lasd Advisory notes 1. pont |

## 6) Kulon kiemelesek (run.md kovetelmenyek)

- _Hogyan lett a preflight runtime/orchestration boundary kialakitva_: Az `api/services/dxf_preflight_runtime.py` egy kulon service reteg, amely a meglevo E2/T7 + E3-T1 service-eket `_execute_pipeline` fuggvenyen keresztul, sorrendi hivassokkal futtatja. A service nem tartalmaz FastAPI route-ot, request modelt, vagy geometriai logikat.

- _Miert marad bent a geometry import trigger is ebben a taskban_: Az E3-T2 nem gate task. A V1 scope freeze szerint a prefilter jelenleg parallel koveto truth-kent fut a geometry import mellett; a gate logika E3-T3 scope-ja. A `complete_upload` route mindharom background task-ot regisztralja: geometry import, legacy validation, preflight runtime.

- _Hogyan szamolodik a `run_seq` a mar letezo `preflight_runs` truth-bol_: `get_next_run_seq(source_file_object_id, db_query)` lekerdi az `app.preflight_runs` tablabol a max `run_seq`-et az adott source file-ra, es +1-et ad vissza. Ha nincs meg sor, 1-et ad. A `RunSeqQueryGateway` protocol teszi mockol-hatova a tesztelest.

- _Hogyan kezeli a task a rules-profile domain jelenlegi hianyat_: A runtime service `rules_profile=None`-nal hivja a teljes lancot. Ez kompatibilis az osszes E2 service-szel (mindegyik opcionalis `rules_profile` parameterrel rendelkezik). A `persist_preflight_run` is `rules_profile=None`-t kap, es ures JSONB snapshot-ot tarol.

- _Hogyan nez ki a minimalis failure handling_: `run_preflight_for_upload` ket try/except blokkja van: (1) `run_seq` lekerdes hiba → logger warning + fallback run_seq=1; (2) `_execute_pipeline` hiba → logger warning + `_try_persist_failed_run` hivas, ami `persist_preflight_failed_run`-on keresztul egy minimalis `preflight_failed` run row-t ment. A `_try_persist_failed_run` sajat hibaját is elnyelie es loggja.

- _Hogyan bizonyitja a tesztcsomag a runtime lancot es a route-trigger integraciot_: 11 unit teszt lefedi: pipeline step sorrendet, accepted flow run_seq szamolasat, rules_profile=None atadast, hiba eseten persist_preflight_failed_run hivast, run_seq=1 fallbacket, no-route-scope ellenorzest. 9 smoke scenario fedeli a route trigger count-ot, non-dxf no-preflight esetet, get_next_run_seq helpert es persist_failed_run row shape-et.

- _Mi marad kifejezetten E3-T3 / E3-T4 / E3-T5 / kesobbi explicit preflight API es UI scope-ban_:
  - **E3-T3**: geometry import gate — rejectelt/review-required fajl ne mehessen tovabb geometry importba;
  - **E3-T4**: replace file es rerun flow;
  - **E3-T5**: feature flag / rollout gate;
  - Kesobbi taskok: explicit preflight route-csalad (`/preflight-runs`), artifact list/url/download, review-decision persistence, rules-profile domain formal implementacio, UI/frontend integration.

## 7) Advisory notes

- A verify.sh FAIL-t jelzett, de a hiba forrasa pre-existing nesting engine timeout-bound flakiness (`[NEST] Canonical JSON determinism smoke`, `time_limit_sec=1`). Ez az E3-T2 Python/service/route valtozasaitol teljesen fuggetlen; a Python/mypy/DXF/Sparrow/vrs_solver retegek mind PASS-on zarultak. A testing_guidelines.md 3.1.1 szekcioja szerint timeout-hatarkozeli benchmark hash-drift nem algoritmikus nondeterminizmus regressziokent kezelendo.
- A `run_seq` service-side szamolasnál a max-lekeres es az insert kozott nincs atomik zar. Ha tobb background task parhuzamosan indul ugyanarra a `source_file_object_id`-ra (pl. dupla klikk), elmeleti versenyhelyzet allhat fenn. V1-ben ez elfogadhato; kesobbi taskban DB sequence-szel vagy advisory lockkal javithato.
- A `_SupabaseStorageGateway` upload `create_signed_upload_url` → `upload_signed_object` lancot hasznal. Ha a signed URL lejart az upload elott (pl. hosszu pipeline futas), az upload hibat fog dobni. V1-ben a `signed_url_ttl_s` altalaban elegendo; kesobbi taskban retry logika vagy hosszabb TTL javithatja.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **FAIL**
- check.sh exit kód: `1`
- futás: 2026-04-21T21:08:55+02:00 → 2026-04-21T21:11:27+02:00 (152s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.verify.log`
- git: `main@3f49b58`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 .claude/settings.json                     |  5 +-
 api/routes/files.py                       | 13 ++++++
 api/services/dxf_preflight_persistence.py | 76 +++++++++++++++++++++++++++++++
 3 files changed, 93 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M .claude/settings.json
 M api/routes/files.py
 M api/services/dxf_preflight_persistence.py
?? api/services/dxf_preflight_runtime.py
?? canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.yaml
?? codex/prompts/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration/
?? codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md
?? codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.verify.log
?? scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py
?? tests/test_dxf_preflight_runtime.py
```

**FAIL tail (utolsó ~60 sor a logból)**

```text
[NEST] Canonical JSON determinism smoke
[BUILD] nesting_engine release
    Finished `release` profile [optimized] target(s) in 0.05s
[RUN] deterministic smoke (10 runs)
ERROR: determinism mismatch between run 1 and run 2
  baseline: /tmp/nesting_engine_determinism_baseline.json
  mismatched: /tmp/nesting_engine_determinism_mismatch.json
```

**Megjegyzes:** A FAIL pre-existing nesting engine timeout-bound flakiness (`time_limit_sec=1` canonical JSON determinism smoke). Az E3-T2 Python/service/route retegek mind zold ellenorzessen zarultak (186 pytest PASS, mypy OK, DXF/Sparrow/vrs_solver PASS).

<!-- AUTO_VERIFY_END -->
