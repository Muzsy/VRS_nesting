# DXF Prefilter State Machine and Lifecycle Model (E1-T4)

## 1. Cel
Ez a dokumentum docs-only modban lefagyasztja a DXF prefilter V1 state machine
es lifecycle modell szerzodeset. A cel az, hogy a kovetkezo taskok (data model,
API contract, UI ingest/review flow) ugyanarra a lifecycle nyelvre epuljenek.

## 2. Scope boundary
- Ez architecture-level state-machine freeze.
- Nem implementacio, nem migration, nem enum bovites, nem route/service/UI kod.
- Nem vegleges persistence schema es nem vegleges endpoint payload.

## 3. Current-code baseline (repo-grounded truth)

### 3.1 Enum truth (meglevo DB lifecycle vilag)
- `app.project_lifecycle`: `draft | active | archived`
- `app.revision_lifecycle`: `draft | approved | deprecated`
- `app.geometry_validation_status`: `uploaded | parsed | validated | approved | rejected`

### 3.2 File/object truth
- `app.file_objects` tartalmaz `file_kind` metadata-t, de nincs dedikalt
  preflight lifecycle mezo.
- Upload route a legacy `stock_dxf` / `part_dxf` inputot `source_dxf`-re
  normalizalja.

### 3.3 Geometry revision truth
- `app.geometry_revisions.status` az `app.geometry_validation_status` enumra ul,
  default `uploaded`.
- Geometry import service sikeres parse utan `status='parsed'` revision rekordot hoz letre.

### 3.4 Validation/report truth
- `app.geometry_validation_reports.status` ugyanarra az enumra ul.
- Validation service az issue-k alapjan `validated` vagy `rejected` statuszt allit,
  es ezt visszairja a `geometry_revisions.status` mezobe.

### 3.5 Review action truth
- `app.geometry_review_actions` action-log tabla (`approve/reject/request_changes/comment`),
  de nem kulon lifecycle source-of-truth enum.

## 4. Lifecycle retegek explicit szetvalasztasa
A T4 freeze negy lifecycle reteget kulonit el:

1. File ingest lifecycle:
- upload metadata es object-level allapot (file szintu vilag).

2. Prefilter run lifecycle:
- jovobeli inspect/repair/acceptance futas allapotai (run szintu vilag).

3. Acceptance outcome lifecycle:
- gate dontesi kimenet (`accepted`, `rejected`, `review_required`) jellegu vilag.

4. Geometry revision lifecycle/status:
- meglevo `app.geometry_validation_status`-ra ulo revision/report allapotvilag.

Szabaly:
- ezek nem ekvivalensek;
- egyik reteget sem szabad masik reteg helyett truth-kent hasznalni.

## 5. Future canonical prefilter state machine (V1 docs-level)

### 5.1 V1 minimum node-ok (future canonical, nem SQL enum)
- `uploaded`
- `preflight_pending`
- `preflight_running`
- `preflight_review_required`
- `preflight_rejected`
- `accepted_for_import`
- `imported`
- `validated`

### 5.2 Later extension (V1.1+)
- `quarantined`
- `archived`

Fontos:
- a fenti node-ok ebben a taskban docs-level canonical node-ok;
- nem current-code enum truth es nem migration DDL.

## 6. Mapping: current geometry status truth vs future prefilter world

| Fogalom | Szint | Statusz | Megjegyzes |
| --- | --- | --- | --- |
| `uploaded` (`app.geometry_validation_status`) | geometry revision | current-code truth | ma revision status default; future prefilterben file-level trigger is lehet |
| `parsed` (`app.geometry_validation_status`) | geometry revision | current-code truth | import service parse utan allitja; nem file ingest state |
| `validated` (`app.geometry_validation_status`) | geometry revision/report | current-code truth | validator success kimenet |
| `rejected` (`app.geometry_validation_status`) | geometry revision/report | current-code truth | validator error kimenet |
| `approved` (`app.geometry_validation_status`) | geometry revision | current-code truth | enum resze, de nem azonos a prefilter acceptance modellel |
| `preflight_pending` | prefilter run | future canonical | jelenleg nincs DB enum/mezo |
| `preflight_running` | prefilter run | future canonical | jelenleg nincs DB enum/mezo |
| `preflight_review_required` | acceptance outcome | future canonical | jelenleg nincs DB enum/mezo |
| `preflight_rejected` | acceptance outcome | future canonical | jelenleg nincs DB enum/mezo |
| `accepted_for_import` | acceptance outcome | future canonical | csak gate pass utan import trigger jellegu node |
| `imported` | prefilter->import bridge | future canonical | jelzi, hogy import lepes megtortent |

## 7. State machine vs persistence modell szetvalasztasa
- A state machine a fogalmi node-ok es atmenetek szerzodese.
- A persistence modell kulon taskban dont:
  - melyik node melyik tablaban/mezo-ben jelenik meg;
  - kell-e uj status mezo vagy kulon run tabla;
  - hogyan lesz owner/project/revision szintu tarolas.

Ebben a taskban nincs:
- migration,
- enum bovites,
- uj status oszlop,
- CRUD vagy route implementacio.

## 8. High-level transition tabla (trigger/event -> next state)

| Aktualis allapot | Trigger / esemeny | Kovetkezo allapot | Notes |
| --- | --- | --- | --- |
| `uploaded` | upload finalize | `preflight_pending` | docs-level canonical; current codeban meg kozvetlen import trigger van |
| `preflight_pending` | preflight start | `preflight_running` | worker/queue orchestration nincs itt fagyasztva |
| `preflight_running` | inspect success | `accepted_for_import` | egyertelmu policy pass |
| `preflight_running` | inspect ambiguous | `preflight_review_required` | manual review igeny |
| `preflight_running` | acceptance fail | `preflight_rejected` | fail-fast elv |
| `preflight_running` | repair success | `accepted_for_import` | csak explicit engedett auto-repair eset |
| `preflight_running` | repair fail | `preflight_rejected` | fail-fast reject |
| `accepted_for_import` | geometry import success | `imported` | import bridge allapot |
| `imported` | geometry validator pass | `validated` | current-code `validated` statuszhoz kapcsolhato |
| `imported` | geometry validator fail | `preflight_rejected` | prefilter acceptance szemantikaban reject kimenet |

## 9. Tiltott atmenetek es anti-pattern lista
- `file_kind` -> lifecycle status direkt lekepzes.
- `geometry_revisions.status` file ingest lifecycle-kent kezelese.
- `geometry_review_actions` automatikus lifecycle truth-kent kezelese.
- Future prefilter node-ok SQL enum truth-kent kezelese migration nelkul.
- State machine taskban retry/lease/job scheduling veglegesitese.
- `project_lifecycle` vagy `revision_lifecycle` enumokkal prefilter run allapotok helyettesitese.

## 10. Anti-scope lista (T4 docs-only)
- Nincs SQL enum/migration bevezetes a future prefilter state-ekre.
- Nincs endpoint response schema veglegesites.
- Nincs UI komponensszintu review flow specifikacio.
- Nincs worker/background scheduling modell lefagyasztasa.
- Nincs API/service implementacio.

## 11. Bizonyitek forrasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `api/routes/files.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
