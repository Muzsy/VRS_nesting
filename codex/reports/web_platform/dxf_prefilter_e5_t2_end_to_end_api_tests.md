PASS_WITH_NOTES

## 1) Meta
- Task slug: `dxf_prefilter_e5_t2_end_to_end_api_tests`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t2_end_to_end_api_tests.yaml`
- Futás dátuma: `2026-04-23`
- Branch / commit: `main@b72fca9`
- Fókusz terület: `Tests`

## 2) Scope

### 2.1 Cél
- Új, önálló route-level API E2E pytest pack a jelenlegi preflight láncra.
- A jelenlegi current-code entrypoint bizonyítása: `complete_upload` finalize után induló `BackgroundTasks` runtime.
- Persisted preflight truth és file-list summary/diagnostics projection együtt-ellenőrzése ugyanazon flow-ban.
- Accepted vs non-accepted geometry import gate különbség bizonyítása.
- `rules_profile_snapshot_jsonb` bridge bizonyítása ugyanebben az API-flow-ban.

### 2.2 Nem-cél (explicit)
- Új `/preflight` vagy historical `/preflight-runs/{id}` endpoint.
- ASGI/TestClient full-stack teszt.
- UI/Playwright/browser scope.
- Meglévő E3/E4 szelet-tesztek átírása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok
- Teszt:
  - `tests/test_dxf_preflight_api_end_to_end.py`
- Smoke:
  - `scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`
  - `codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`

### 3.2 Miért változtak?
- A repo-ban voltak szeletelt route/runtime/projection tesztek, de nem volt egyetlen olyan pack, ami ugyanabban a helper-láncban bizonyítja a `complete_upload -> BackgroundTasks -> runtime -> list_project_files` teljes API-flow-t.
- Az új E2E pack ezt pótolja, additive módon, production kód módosítása nélkül.

## 4) Verifikáció

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md` (a futás eredménye az AUTO_VERIFY blokkban)

### 4.2 run.md szerinti célzott futtatások
- `python3 -m py_compile tests/test_dxf_preflight_api_end_to_end.py scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py` -> OK
- `python3 -m pytest -q tests/test_dxf_preflight_api_end_to_end.py` -> `3 passed in 1.20s`
- `python3 scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py` -> All checks passed

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat |
| --- | --- | --- | --- |
| Új, dedikált API E2E pytest file | PASS | `tests/test_dxf_preflight_api_end_to_end.py:1-514` | Önálló pack, saját fake Supabase/storage helperrel. |
| A pack a helyes route-level láncot futtatja (`complete_upload -> BackgroundTasks -> run_preflight_for_upload -> list_project_files`) | PASS | `tests/test_dxf_preflight_api_end_to_end.py:347-384` | A helper explicit route-callable flow-t futtat, nem TestClient/ASGI stacket. |
| Minimum scenario matrix (accepted, lenient review_required, strict rejected) | PASS | `tests/test_dxf_preflight_api_end_to_end.py:441-514` | Három külön test fedi a három kimenetet. |
| `ezdxf` dependency explicit vállalása | PASS | `tests/test_dxf_preflight_api_end_to_end.py:29` | Modul-szintű `pytest.importorskip("ezdxf")` guard. |
| Core pipeline nincs szétmockolva; csak I/O seam patch | PASS | `tests/test_dxf_preflight_api_end_to_end.py:326-345` | Csak `load_file_ingest_metadata`, `download_storage_object_blob`, geometry import side-effect patch; runtime core valósan fut. |
| Fake Supabase world + signed upload payload capture | PASS | `tests/test_dxf_preflight_api_end_to_end.py:57-225,416-423` | Fedi az elvárt táblákat és artifact upload payload capturét. |
| Geometry import gate accepted vs non-accepted különbség bizonyított | PASS | `tests/test_dxf_preflight_api_end_to_end.py:460-463,466-514` | Accepted esetben import call történik, review_required/rejected esetben 0 call. |
| Task-specifikus structural smoke elkészült | PASS | `scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py:1-97` | Kötelező lánctokenek, ezdxf guard, 3 scenario és scope-tiltás ellenőrzése. |

## 6) Miért ez a helyes E2E API truth

- A jelenlegi repo current-code truth szerint a preflight nem külön endpointon indul, hanem `complete_upload(...)` finalize után, `BackgroundTasks`-ban.
- Emiatt a helyes API E2E belépési pont a route callable `complete_upload`, nem egy új `/preflight` route.
- Ugyanezen flow vége a `list_project_files(...include_preflight_summary=True, include_preflight_diagnostics=True)`, ahol a persisted `preflight_runs.summary_jsonb` projection jelenik meg.
- Az E2E pack ezért ugyanazon scenario-n belül egyszerre bizonyítja: trigger, runtime, persistence truth, projection truth.

## 7) Scenario lefedettség és gate-bizonyítás

- Accepted scenario: `accepted_for_import`, summary recommended action `ready_for_next_step`, geometry import trigger 1x.
- Lenient scenario: `preflight_review_required`, summary recommended action `review_required_wait_for_diagnostics`, geometry import trigger 0x.
- Strict scenario: `preflight_rejected`, summary recommended action `rejected_fix_and_reupload`, geometry import trigger 0x.
- Mindhárom scenario-ban a diagnostics projection jelen van ugyanazon file-list válaszban.

## 8) ezdxf dependency vállalás indoklása

- A runtime core T5/T6 lánca valós normalized DXF artifactot ír és azt acceptance gate import/validator probe olvassa.
- Ez közvetlenül `ezdxf`-függő jelenlegi kódban, ezért a modul-szintű `pytest.importorskip("ezdxf")` guard explicit és helyes.

## 9) Advisory notes

- A route helper a source fixture-t `.json` storage pathon adja a runtime-nak, hogy a core inspect lánc deterministic JSON fixture backenden fusson; a route triggerelést ettől függetlenül valódi `source_dxf` finalize flow indítja (`load_file_ingest_metadata.file_name="source.dxf"`).
- A végső repo-gate eredményt a verify AUTO_VERIFY blokk mutatja; ha ott FAIL lesz, az okot külön kell értelmezni task relevancia szerint.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-23T20:03:58+02:00 → 2026-04-23T20:06:44+02:00 (166s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.verify.log`
- git: `main@b72fca9`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? canvases/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t2_end_to_end_api_tests.yaml
?? codex/prompts/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests/
?? codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md
?? codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.verify.log
?? scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py
?? tests/test_dxf_preflight_api_end_to_end.py
```

<!-- AUTO_VERIFY_END -->
