PASS

## 1) Meta
- Task slug: `dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration`
- Kapcsolodo canvas: `canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.yaml`
- Futas datuma: `2026-04-21`
- Branch / commit: `main@bd85189` (folytatva)
- Fokusz terulet: `Backend (persistence + artifact storage only)`

## 2) Scope

### 2.1 Cel
- Minimalis migration: `app.preflight_runs`, `app.preflight_diagnostics`, `app.preflight_artifacts` tablak RLS-szel.
- Kulon backend persistence service a local T1→T7 truth canonical DB + storage truth-va forditasara.
- A T7 summary snapshot tartosan megmarad `summary_jsonb`-ban; nem kell kesobbi taskoknak ujraszamolni.
- A T7 `issue_summary.normalized_issues`-bol `preflight_diagnostics` row-ok keletkeznek.
- A T5 normalized DXF local artifact a `geometry-artifacts` bucketbe kerul canonical content-addressed storage path-ra.
- A `preflight_artifacts` tabla explicit storage truth-ot tartalmaz.
- Task-specifikus unit teszt + smoke script deterministic, fake gateway alapon.

### 2.2 Nem-cel (explicit)
- FastAPI route / request model / OpenAPI frissites.
- Upload utani automatikus trigger (E3-T2 scope).
- Geometry import gate (E3-T3 scope).
- Full rules-profile persistence domain (`dxf_rules_profiles` / `dxf_rules_profile_versions`).
- `preflight_review_decisions` implementacio.
- Signed download URL API vagy artifact-listazo route.
- Globalis multi-bucket config refactor.
- Frontend / polling / diagnostics drawer / review modal.
- Worker queue / heartbeat / polling lifecycle.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok
- Migration:
  - `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql`
- Backend persistence service:
  - `api/services/dxf_preflight_persistence.py`
- Tesztek / smoke:
  - `tests/test_dxf_preflight_persistence.py`
  - `scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`
- Codex artefaktok:
  - `canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
  - `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.yaml`
  - `codex/prompts/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration/run.md`
  - `codex/codex_checklist/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
  - `codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`

### 3.2 Miert valtoztak?
A T7 utan mar letezik a teljes local preflight truth (T1→T7 output), de ez eddig csak process-local maradt — nem volt `preflight_runs` persistence, nem voltak `preflight_diagnostics` row-k, es a T5 normalized DXF csak local temp artifact volt. Az E3-T1 ezt a gapet zarja le: a service a mar eloallt truth-ot tolja canonical DB + storage truth-va, route/trigger/gate megnyitasa nelkul.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`

### 4.2 Opcionalis, feladatfuggo parancsok
- `python3 -m py_compile api/services/dxf_preflight_persistence.py tests/test_dxf_preflight_persistence.py scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`
- `python3 -m mypy --config-file mypy.ini api/services/dxf_preflight_persistence.py`
- `python3 -m pytest -q tests/test_dxf_preflight_persistence.py`
- `python3 scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes; a verify.sh futtatja a teljes repo gate-et.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a minimalis `preflight_runs` / `preflight_diagnostics` / `preflight_artifacts` migration. | PASS | `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql:14`; `:67`; `:117` | Harom tabla RLS-szel; `preflight_runs` a minimalis required mezokkel; `preflight_diagnostics` `diagnostic_seq` + severity + code + details_jsonb; `preflight_artifacts` explicit storage truth oszlopokkal. | SQL szintaxis ellenorzes; `./scripts/verify.sh` |
| A migration nem koveteli meg a meg nem letezo rules-profile domain azonnali implementaciojat. | PASS | `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql:36` | `rules_profile_snapshot_jsonb jsonb not null default '{}'::jsonb` — nincs FK a `dxf_rules_profiles` tablara; JSONB snapshot elegendo a V1 truth-hoz. | `tests/test_dxf_preflight_persistence.py::test_rules_profile_none_stores_empty_snapshot`; `::test_rules_profile_snapshot_stored_without_fk` |
| Letrejon kulon backend persistence service a local T1→T7 truth perzisztalasara. | PASS | `api/services/dxf_preflight_persistence.py:138` | A `persist_preflight_run(project_id, source_file_object_id, t7_summary, acceptance_gate_result, normalized_dxf_writer_result, ...)` entry point mapping-szintu bemenetre epul; a `DbGateway` / `StorageGateway` Protocol-ok mock-olhatoak. | `tests/test_dxf_preflight_persistence.py::test_persist_run_returns_required_keys` |
| A T7 summary snapshot persisted truth-kent mentodik. | PASS | `api/services/dxf_preflight_persistence.py:218`; `:222` | `summary_jsonb = _as_jsonable(dict(t7_summary))` — a teljes T7 renderer output a `preflight_runs.summary_jsonb`-ba kerul; nem uresiti ki es nem szamitja ujra. | `tests/test_dxf_preflight_persistence.py::test_summary_jsonb_snapshot_preserves_t7_structure`; `scripts/smoke...::_scenario_t7_summary_snapshot_in_run_row` |
| A T7 issue summary-bol `preflight_diagnostics` row-k szuletnek. | PASS | `api/services/dxf_preflight_persistence.py:289` | `_insert_diagnostics` a `t7_summary["issue_summary"]["normalized_issues"]` listajat iteralja; minden normalized issue → egy `preflight_diagnostics` row `diagnostic_seq`, `severity`, `code`, `source`, `family`, `details_jsonb` mezokkel. | `tests/test_dxf_preflight_persistence.py::test_diagnostics_rows_from_t7_issue_summary`; `::test_empty_issue_summary_produces_zero_diagnostics` |
| A T5 normalized DXF canonical `geometry-artifacts` storage pathra feltoltodik. | PASS | `api/services/dxf_preflight_persistence.py:320`; `:344` | `_upload_and_register_normalized_dxf` a local `output_path`-t beolvassa, SHA-256 hash-eli, es `storage.upload_bytes(bucket="geometry-artifacts", ...)` hivja a canonical path-ra. | `tests/test_dxf_preflight_persistence.py::test_accepted_flow_uploads_normalized_dxf_to_geometry_artifacts`; `scripts/smoke...::_scenario_accepted_flow` |
| A `preflight_artifacts` tabla explicit storage truth-ot tartalmaz. | PASS | `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql:122`; `api/services/dxf_preflight_persistence.py:355` | A migracion `storage_bucket text not null`, `storage_path text not null`, `artifact_hash_sha256 text not null`, `content_type text not null`, `size_bytes bigint not null` explicit oszlopok; ezeket a service kulon mezokkent toltj ki, nem csak `metadata_jsonb`-be temeti. | `tests/test_dxf_preflight_persistence.py::test_artifact_row_has_explicit_storage_truth` |
| Keszul task-specifikus unit teszt es smoke. | PASS | `tests/test_dxf_preflight_persistence.py:1`; `scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py:1` | 24 deterministic pytest unit teszt + 8 scenario smoke; mindketto fake DbGateway / FakeStorage gateway-jel (nincs valós Supabase-hivas). | `python3 -m pytest -q tests/test_dxf_preflight_persistence.py` (24 passed); `python3 scripts/smoke...` (OK) |
| A task nem nyit route / request-model / OpenAPI / UI / trigger / gate scope-ot. | PASS | `api/services/dxf_preflight_persistence.py:46`; `tests/test_dxf_preflight_persistence.py::test_no_route_or_request_model_in_service` | A service-ben nincs `fastapi`, `APIRouter`, `HTTPException`, `@app.post`, `@router.post` referencia; a teszt aktivan ellenorzi. | `scripts/smoke...::_scenario_no_route_or_request_model_in_service` |
| `./scripts/verify.sh --report ...` PASS. | PASS | `codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md` AUTO_VERIFY blokk; `.verify.log` | A repo gate PASS-szel zarult (check.sh exit 0, 184s, `main@32d36ad`); 175 pytest teszt zold. | `./scripts/verify.sh --report ...` |

## 6) Kulon kiemelesek (run.md kovetelmenyek)

- _Hogyan lesz a T7 summary persisted truth-va_: A `persist_preflight_run` `t7_summary` parameteret `_as_jsonable` hivas utan beemeli a `preflight_runs.summary_jsonb` oszlopba. A T7 renderer outputja stabil boundary — a kovetkezo retegek (`E3-T2` trigger, `E4` UI) nem kell ujra osszeallitsak T1→T7 output-bol a summary-t.

- _Hogyan keletkeznek a `preflight_diagnostics` row-k_: A `_insert_diagnostics` fuggveny a `t7_summary["issue_summary"]["normalized_issues"]` listat iteralja. Minden bejegyzes → egy `preflight_diagnostics` sor `diagnostic_seq` (0-tol soros), `severity`, `code`, `source`, `family`, `details_jsonb` mezokkel. A T7 mar normalizalt es sorba rendezett issue listajat hasznaljuk — nem jon letre uj diagnostics generator.

- _Hogyan epul a canonical storage path_: `canonical_preflight_storage_path(project_id, preflight_run_id, artifact_kind, content_hash_sha256, extension)` → `projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}`. A content hash biztositja az idempotens feltoltest; a path-ban a `preflight_run_id` garantalja az izolaciot mas runok artifactjaitol.

- _Miert a `geometry-artifacts` bucket a helyes_: A H0 storage policy lezarta a canonical bucket inventoryt; a `geometry-artifacts` bucket a file-backed geometry artifact-oknak van fenntartva. A normalized DXF egy geometry-prep artifact — nem a `source-files` bucket-et szennyezi, es nem kever run artifactot (az `run-artifacts` bucket-be kerul).

- _Miert nem implemental teljes rules-profile domaint a task_: A `dxf_rules_profiles` / `dxf_rules_profile_versions` tablak current-code szinten nem leteznek. Az E3-T1 nem epulhet hard FK-kent nem letezo tablakra. A V1 truth `rules_profile_snapshot_jsonb`-ot hasznal; a formal FK extension kesobbi task scope-ja.

- _Hogyan sharpenelja a task a `preflight_artifacts` storage-truth-ot_: Az E1-T5 docs-level modell a `preflight_artifacts` tablaba csak metadata-vilagot rogzitett. A T1 implementacio explicit `storage_bucket`, `storage_path`, `artifact_hash_sha256`, `content_type`, `size_bytes` oszlopokat hasznal, nem csak `metadata_jsonb`-be temeti a storage truth-ot. Ez biztositja, hogy a kovetkezo artifact list/url route taskok adatbazis-szinten tudjak querelni az artifact referenciakat JSON parse nelkul.

- _Hogyan bizonyitja a tesztcsomag a flow-kat_: 24 unit teszt + 8 smoke scenario lefedi: accepted / review-required / rejected flow-kat; artifact upload / no-upload agat; diagnostics row szamot es sorrendet; summary_jsonb struktura megorzeset; rules profile snapshot JSONB-et (FK nelkul); canonical storage path shape-et; service route-mentessegat.

- _Mi maradt kifejezetten a kovetkezo taskokra_: **E3-T2** upload utani trigger / explicit preflight inditas; **E3-T3** geometry import gate; kesobbi taskok: artifact list/url route, review-decision persistence, rules-profile domain formal implementacio, frontend/UI integration. A migration `preflight_review_decisions` tablat szandekosan nem tartalmaz.

## 7) Advisory notes

- A `persist_preflight_run` `run_seq` parametere jelenleg kuldorol jon (caller adja meg). Ha a kovetkezo trigger task automatizalni akarja a `run_seq` szamolast, ezt `select max(run_seq) + 1` DB-oldalon is meg lehet oldani a migracion belul egy sequence-szel.
- A `preflight_artifacts` tabla `uq_preflight_artifacts_run_kind` constraint-je per-run egy `artifact_kind`-ot enged. Ha egy preflight runhoz tobb `normalized_dxf` artifactot kell tarolni (pl. multi-sheet), a constraint bovitese szuksegesse valhat.
- A `normalized_hash_sha256` a `preflight_runs` row-ban jelenleg V1-ben nem kerül visszairva a runba az artifact feltoltes utan (a hash az artifact rowban van). Egy kesobbi extensionkent az `update_rows` PATCH hivas ezt visszatoltheti.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-21T02:07:04+02:00 → 2026-04-21T02:10:08+02:00 (184s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.verify.log`
- git: `main@32d36ad`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 .claude/settings.json | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M .claude/settings.json
?? api/services/dxf_preflight_persistence.py
?? canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.yaml
?? codex/prompts/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration/
?? codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md
?? codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.verify.log
?? samples/real_work_dxf/test_dxf/
?? scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py
?? supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql
?? tests/test_dxf_preflight_persistence.py
```

<!-- AUTO_VERIFY_END -->
