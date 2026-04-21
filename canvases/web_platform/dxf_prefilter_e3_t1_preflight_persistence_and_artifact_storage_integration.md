# DXF Prefilter E3-T1 — Preflight persistence és artifact storage bekötés

## Cel
A DXF prefilter lane-ben az E2-T1→T7 utan mar letezik a teljes **local preflight truth**:
- T1 inspect
- T2 role resolver
- T3 gap repair
- T4 duplicate dedupe
- T5 normalized DXF writer
- T6 acceptance gate
- T7 diagnostics/repair summary renderer

A gap jelenleg az, hogy ez a truth meg **csak process-local service kimenet**:
- nincs `preflight_runs` persistence truth,
- nincs normalizalt diagnostics row truth,
- nincs canonical `preflight_artifacts` metadata,
- a T5 `normalized_dxf.output_path` csak local temp artifact,
- a T7 summary nem marad meg tartosan a kovetkezo E3/E4 retegeknek.

A T1 feladata ezert egy olyan **persistence + artifact storage integration** reteg bevezetese, amely:
- a local T1→T7 truth-bol letrehozza a canonical `preflight_runs` / `preflight_diagnostics` / `preflight_artifacts` adatot,
- a local normalized DXF-et feltolja a canonical artifact bucketbe,
- es visszaad egy mar persistent-azonositokkal rendelkezo backend truth-ot,
- mindezt route/API/upload-trigger/UI megnyitasa nelkul.

## Miert most?
A jelenlegi repo-grounded helyzet:
- a `files.py` finalize utan ma kozvetlen geometry import trigger fut; nincs preflight persistence bridge;
- a T7 mar ad egy stabil renderer-outputot, de ez meg nincs sem DB-ben, sem artifact storage-ban megkotve;
- a H0 storage policy mar lezarta a canonical bucket inventoryt (`source-files`, `geometry-artifacts`, `run-artifacts`);
- az E1-T5 data-model docs leirta a jovobeli `preflight_runs` / `preflight_diagnostics` / `preflight_artifacts` vilagot,
  de ez meg nincs implementalva.

Ha ezt most nem vezetjuk be, akkor a kovetkezo taskok vagy:
- ad hoc payloadban fogjak cipelni a T1→T7 truth-ot,
- vagy a route/UI retegek fogjak kitalalni, hogyan legyen belole persistence.

A helyes sorrend ezert:
1. E3-T1: persistence + artifact storage truth,
2. E3-T2: upload utani trigger / explicit preflight inditas,
3. E3-T3: geometry import gate,
4. kesobb API/UI integration.

## Scope boundary

### In-scope
- `preflight_runs`, `preflight_diagnostics`, `preflight_artifacts` implementacios migrationje.
- Kulon backend persistence service, amely a T1→T7 outputokat canonical persisted truth-va forditja.
- A T7 summary snapshot tartos mentese a preflight run truth mellett.
- A T7 normalized issue lista alapjan `preflight_diagnostics` row-k generalasa.
- A T5 `normalized_dxf.output_path` local artifact canonical storage feltoltese.
- Canonical preflight artifact storage-path policy bevezetese.
- `preflight_artifacts` metadata row-k letrehozasa.
- Task-specifikus unit teszt es smoke a persistence + artifact storage bridge-re.

### Out-of-scope
- Upload utani automatikus trigger vagy explicit route bekotes.
- Geometry import gate bekotes.
- Barmilyen uj FastAPI route / request model / OpenAPI frissites.
- Frontend / polling / diagnostics drawer / review modal.
- Full rules-profile persistence domain (`dxf_rules_profiles`, `dxf_rules_profile_versions`) implementacioja.
- `preflight_review_decisions` implementacio.
- Signed download URL API vagy artifact-listazo route.
- Globalis multi-bucket config refactor.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
  - docs-only future canonical data-model; leirja a `preflight_runs`, `preflight_diagnostics`, `preflight_artifacts` tablakat,
    de current-code szinten ezek meg nem leteznek.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - canonical bucket truth: `geometry-artifacts` reserved/canonical bucket a jovobeli file-backed geometry artifactokhoz.
- `api/services/dxf_preflight_normalized_dxf_writer.py`
  - current-code truth: local `normalized_dxf.output_path` artifactot ad, de ez meg nem persistent storage truth.
- `api/services/dxf_preflight_acceptance_gate.py`
  - current-code truth: canonical acceptance outcome, importer probe, validator probe, blocking/review reasons.
- `api/services/dxf_preflight_diagnostics_renderer.py`
  - current-code truth: stabil T7 summary object, amit az E3/E4 retegeknek egyetlen truthkent erdemes tovabbvinni.
- `api/supabase_client.py`
  - current-code truth: signed upload/download helper surfaces mar leteznek.
- `api/services/file_ingest_metadata.py`
  - current-code truth: API oldalon mar van storage helper minta signed object downloadra.
- `worker/raw_output_artifacts.py`
  - current-code truth: canonical storage-path + upload/register helper minta artifact domainre.
- `api/routes/files.py`
  - current-code truth: ma meg nincs preflight persistence hook, finalize utan geometry import trigger indul.

## Jelenlegi repo-grounded helyzetkep
A T1 kulcs-tenyei:

### 1. Nincs meg ma a preflight persistence domain
A repoban jelenleg nincs:
- `app.preflight_runs`
- `app.preflight_diagnostics`
- `app.preflight_artifacts`

### 2. A T7 utan mar van mit persistent truth-va tenni
A T7 summary object mar eleg stabil ahhoz, hogy a kovetkezo retegek ne 6 kulon service outputot pakolgassanak.
Ez a task most ezt a gapet zarja le.

### 3. A rules-profile domain tovabbra sincs implementalva
Az E1-T5 docs-level modellben szerepel `dxf_rules_profiles` / `dxf_rules_profile_versions`,
de ezek current-code szinten meg nem leteznek.
Ezert az E3-T1 **nem epulhet hard FK-kent** nem letezo rules-profile tablakhra.
A helyes V1 bridge:
- a preflight run persisted truth tartalmazzon **rules-profile snapshot JSON**-ot,
- es legfeljebb kesobbi extensionkent legyen bekotheto a formal rules-profile version FK.

### 4. A normalized DXF ma meg csak local temp artifact
A T5 writer `output_path`-ot ad, de ez meg nem storage truth.
A T1 helyes feladata, hogy ebbol canonical storage artifact legyen.

### 5. A task meg nem async lifecycle/orchestration task
Mivel az upload trigger es a background/preflight orchestration az E3-T2-ben jon,
az E3-T1 most meg **lezart, terminalis local preflight eredmenyt** persistent-el.
Nem kell worker/queue/polling state machine-et kitalalnia.

## Konkret elvarasok

### 1. Kulon migration szülessen a minimalis preflight persistence truth-hoz
A task hozzon letre uj migrationt, amely implementalja a minimalis V1 tablakat:
- `app.preflight_runs`
- `app.preflight_diagnostics`
- `app.preflight_artifacts`

Repo-grounded fontosites:
- a T1-ben **nem** kell meg `preflight_review_decisions`;
- a T1-ben **nem** kell meg a full rules-profile domain;
- a migration minimalis, de eleg legyen a local T1→T7 truth persistence-re.

### 2. A `preflight_runs` V1 truth ne koveteljen letezo rules-profile FK domaint
Mivel a rules-profile tablakh current-code szinten nincsenek, a T1-ben a preflight run
persistalt truth minimum tartalmazzon:
- `project_id`
- `source_file_object_id`
- `run_seq`
- `run_status`
- `acceptance_outcome`
- `rules_profile_snapshot_jsonb`
- `summary_jsonb`
- `source_hash_sha256`
- `normalized_hash_sha256`
- `created_at` / `started_at` / `finished_at`

Kritikus boundary:
- ne implementalj most kulon `dxf_rules_profiles` / versions tablakat csak azert,
  hogy a T1 tudjon egy FK-t kitolteni.

### 3. A `preflight_artifacts` tabla tudjon valodi storage referenciat
Az E1-T5 docs-level modell a `preflight_artifacts` tablaban metadata-vilagot rogzit,
de az implementacios T1 feladata most mar valodi artifact storage bekotes.
Ezert a T1-ben a `preflight_artifacts` migrationben legyen explicit storage truth is,
legalabb:
- `storage_bucket`
- `storage_path`
- `artifact_kind`
- `artifact_hash_sha256`
- `content_type`
- `size_bytes`
- `metadata_jsonb`

Indok:
ha ez most csak `metadata_jsonb` lenne, akkor a kovetkezo artifact list/url route taskoknak
JSON parse-olva kellene storage truth-ot kinyerniuk, ami gyenge contract lenne.

### 4. Kulon backend persistence service szülessen
A T1 hozzon letre kulon service reteget, peldaul:
- `api/services/dxf_preflight_persistence.py`

A service felelossege:
- a local T1→T7 outputok validalasa;
- a preflight run row letrehozasa;
- a T7 normalized issue-k row-szintu `preflight_diagnostics` rekordokka alakitasa;
- a T5 normalized DXF artifact feltoltese storage-ba;
- a `preflight_artifacts` row letrehozasa;
- a persisted summary truth visszaadasa.

Kritikus boundary:
- a service ne legyen FastAPI route;
- ne legyen upload-trigger orchestration;
- ne legyen geometry import gate;
- ne vegezzen uj DXF parse/importer/validator probe-ot.

### 5. A canonical artifact bucket es path policy legyen explicit
A T1-ben a normalizalt DXF artifact canonical bucketje legyen:
- `geometry-artifacts`

A canonical storage path minimum ilyen mintat kovessen:
- `projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}`

Indok:
- a H0 storage policy mar lezarta a `geometry-artifacts` bucketet jovobeli file-backed geometry artifactokra;
- a normalizalt DXF egy ilyen file-backed geometry-prep artifact;
- ne a `source-files` bucketet szennyezze uj, generalt outputtal.

### 6. A T7 summary snapshot tartosan maradjon meg
A T1 service ne csak diagnostics row-kat irjon, hanem a teljes T7 renderer outputot is mentse el a run truth mellett,
legalabb `summary_jsonb`-ban.

Indok:
- a T7 summary mar stabil boundary;
- az E4 UI-nak es a kovetkezo E3 taskoknak jo lesz egyetlen persisted summary truth;
- ne kelljen kesobb a teljes T1→T7 local output shape-et DB-bol ujraosszefesulni.

### 7. A diagnostics row-k a T7 issue summary-bol szulessenek
A T1 ne talalja ujra a diagnostics truthot.
A helyes source:
- `t7_summary.issue_summary.items`

A `preflight_diagnostics` row-k innen keszuljenek,
legalabb ezekkel a mezokkel:
- `diagnostic_seq`
- `severity`
- `code`
- `message`
- `path` vagy `source`
- `details_jsonb`

### 8. A T1 terminal snapshot persistence legyen, ne orchestration engine
Mivel az E3-T2 trigger es a kesobbi lifecycle bridge meg nincs bent,
a T1 service a local futas vegallapotat tarolja.
Ezert a T1-ben rendben van, ha:
- `run_status` mar a terminalis preflight allapotot kapja,
- `started_at` / `finished_at` egyszerre vagy kozel egyszerre kerul kitoltesre,
- nincs kulon queue/polling/heartbeat.

### 9. A teszteles bizonyitsa a persistence + artifact storage bridge-et
Minimum deterministic coverage:
- accepted flow -> run row + diagnostics + normalized artifact row + geometry-artifacts upload;
- review-required flow -> `preflight_review_required` status/outcome + persisted summary + diagnostics row-k;
- rejected flow -> `preflight_rejected` status/outcome + diagnostics row-k + artifact upload csak ha local normalized DXF tenyleg letezik;
- canonical storage path shape helyes;
- a service nem igenyel route-ot vagy request modelt;
- a service nem igenyel letezo rules-profile FK domaint;
- a persisted summary JSON a T7 outputra epul.

### 10. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es a canvasban is legyen explicit:
- E3-T2: upload utani trigger / explicit preflight inditas,
- E3-T3: geometry import gate,
- kesobbi taskok: artifact list/url route, review-decision persistence, rules-profile domain.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration/run.md`
- `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql`
- `api/services/dxf_preflight_persistence.py`
- `tests/test_dxf_preflight_persistence.py`
- `scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.verify.log`

## DoD
- [ ] Letrejon a minimalis `preflight_runs` / `preflight_diagnostics` / `preflight_artifacts` migration.
- [ ] A migration nem koveteli meg a meg nem letezo rules-profile domain azonnali implementaciojat.
- [ ] Letrejon kulon backend persistence service a local T1→T7 truth perzisztalasara.
- [ ] A T7 summary snapshot persisted truth-kent mentodik.
- [ ] A T7 issue summary-bol `preflight_diagnostics` row-k szuletnek.
- [ ] A T5 normalized DXF canonical `geometry-artifacts` storage pathra feltoltodik.
- [ ] A `preflight_artifacts` tabla explicit storage truth-ot tartalmaz.
- [ ] Keszul task-specifikus unit teszt es smoke.
- [ ] A task nem nyit route / request-model / OpenAPI / UI / trigger / gate scope-ot.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md` PASS.

## Javasolt ellenorzesek
- `python3 -m py_compile api/services/dxf_preflight_persistence.py tests/test_dxf_preflight_persistence.py scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_dxf_preflight_persistence.py`
- `PYTHONPATH=. python3 scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
