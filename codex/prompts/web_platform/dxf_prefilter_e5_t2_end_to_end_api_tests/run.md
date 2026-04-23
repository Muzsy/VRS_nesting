Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj `/preflight` vagy historical `preflight-runs` endpointot; a
  jelenlegi current-code truth szerint a preflight a `complete_upload(...)`
  finalize route utan indul background taskkent.
- Ne epits teljes ASGI/TestClient stack tesztet, ha a route-callable + fake deps
  repo-minta eleg; ez most a helyes stilus.
- A pack ne patch-elje szet a core T1→T7 pipeline-t. I/O seam patch megengedett:
  `load_file_ingest_metadata`, `download_storage_object_blob`, geometry import
  side-effect recorder. A runtime core hivas maradjon valodi.
- Ne torold vagy irjad ujra a meglevo E3/E4 route/runtime/projection teszteket;
  az uj pack plusz, osszegzo regresszio legyen.
- A route import-lanc es a T5/T6 writer/gate `ezdxf` dependency truthjat vallald
  explicit modon (pl. `pytest.importorskip("ezdxf")`).
- Ne nyiss UI/Playwright/browser scope-ot.

Modellezesi elvek:
- Javasolt uj tesztfile: `tests/test_dxf_preflight_api_end_to_end.py`.
- Javasolt helper-lanc:
  1) `complete_upload(...)`
  2) `BackgroundTasks` ellenorzes es a `run_preflight_for_upload(...)` task
     explicit lefuttatasa
  3) `list_project_files(..., include_preflight_summary=True, include_preflight_diagnostics=True)`
  4) persisted rows + artifact refs + geometry import trigger + route response
     egyuttes ellenorzese
- Minimum scenario-k:
  - accepted flow
  - lenient review_required flow
  - strict rejected flow
- A fake Supabase/storage truth kezelje legalabb ezeket:
  - `app.projects`
  - `app.file_objects`
  - `app.preflight_runs`
  - `app.preflight_diagnostics`
  - `app.preflight_artifacts`
  - signed upload url + uploaded artifact payload capture
- A geometry importot ne kelljen valosan DB-be irni; eleg recorder/mock hivas,
  de csak a runtime vegi import-trigger seam-en.

Kulon figyelj:
- a pack current-code truth szerint route-level E2E legyen, ne UI smoke;
- a `rules_profile_snapshot_jsonb` bridge ugyanebben az E2E flow-ban legyen
  bizonyitva;
- a summary + diagnostics projectiont ugyanazon file-list route valaszban ellenorizd;
- az accepted vs non-accepted geometry import kulonbseget kulon nevezd meg es
  allitsd a tesztben;
- a reportban kulon emeld ki, hogy ez miert tobb a meglevo E3/E4 szelet-teszteknel.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile tests/test_dxf_preflight_api_end_to_end.py scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`
- `python3 -m pytest -q tests/test_dxf_preflight_api_end_to_end.py`
- `python3 scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`

A reportban kulon terj ki erre:
- miert a `complete_upload -> BackgroundTasks -> runtime -> list_project_files`
  a helyes current-code E2E API truth;
- pontosan mely scenario-kat fedi le a pack;
- hogyan bizonyitja a geometry import gate accepted vs non-accepted kulonbseget;
- miert explicit es helyes az `ezdxf` dependency vallalasa.
