# DXF Prefilter E1-T4 State machine es lifecycle modell

## Funkcio
Ez a task a DXF prefilter lane negyedik, **docs-only state-machine freeze** lepese.
A cel most nem migration, nem enum-implementacio, nem route, nem service es nem UI state-kod,
hanem annak rogzitese, hogy a jovobeli DXF prefilter V1 milyen **state machine** es milyen
**lifecycle modell** menten fog mukodni a meglevo upload -> geometry import -> validation lancra raulve.

A task kozvetlenul az E1-T1 / E1-T2 / E1-T3 utan jon:
- a T1 rogzitette a V1 scope es integration boundary keretet;
- a T2 lefagyasztotta a fogalmi szinteket es a canonical role-vilagot;
- a T3 rogziti a policy matrix es rules profile schema fogalmi szerzodeset;
- ez a T4 ezekre epitve lefagyasztja a **lifecycle retegeket**, a **fogalmi allapotokat** es a
  **megengedett atmeneteket**.

A tasknak a jelenlegi repora kell raulnie:
- ma letezik `app.project_lifecycle`, `app.revision_lifecycle`, `app.geometry_validation_status`;
- a `geometry_revisions.status` ma `uploaded` / `parsed` / `validated` / `approved` / `rejected`
  enumra ul;
- a file upload route ma nem tart fenn dedikalt preflight lifecycle-t;
- a geometry import service sikeres parse utan `parsed` statuszu geometry revision rekordot hoz letre;
- a geometry validation report ma `validated` vagy `rejected` statuszra allit;
- a `geometry_review_actions` ma audit/review action log, nem explicit prefilter lifecycle enum.

Ez a task azert kell, hogy a kesobbi data model, API contract es UI ingest/review flow ne keverje
ossze:
- a file/object szintu ingest allapotot,
- a jovobeli preflight run allapotot,
- az acceptance gate kimeneti allapotat,
- es a meglevo geometry revision statuszvilagot.

## Scope
- Benne van:
  - a DXF prefilter V1 lifecycle retegek kulonvalasztasa;
  - a future canonical prefilter state machine dokumentacios definicioja;
  - current-code truth vs future canonical lifecycle model szetvalasztasa;
  - a file-level, preflight-run-level, acceptance-outcome-level es geometry-revision-level allapotok kulon kezelese;
  - a minimum V1 allapotok es atmenetek rogzitese;
  - a tiltott atmenetek es anti-pattern lifecycle keveresek dokumentalasa;
  - egy dedikalt architecture dokumentum letrehozasa a state machine-rol es lifecycle modellrol.
- Nincs benne:
  - SQL migration vagy uj enum letrehozasa;
  - uj DB status mezo implementacio;
  - FastAPI route vagy service kod;
  - UI component state implementacio;
  - worker/background orchestration implementacio;
  - geometry import pipeline tenyleges preflight gate atkotese;
  - retry policy vagy job-lease mechanika reszletes tervezese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
  - current-code truth: `app.project_lifecycle`, `app.revision_lifecycle`, `app.geometry_validation_status` enumok;
  - bizonyitja, hogy a repo mar hasznal lifecycle/status enumokat, de kulon domainenkent.
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
  - current-code truth: `app.file_objects` metadata + `file_kind`, de nincs benne preflight lifecycle.
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
  - current-code truth: `app.geometry_revisions.status app.geometry_validation_status not null default 'uploaded'`.
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
  - current-code truth: `app.geometry_validation_reports.status` ugyanarra az enumra ul;
  - `geometry_review_actions` letezik, de review action log, nem kulon lifecycle enum.
- `api/routes/files.py`
  - current-code truth: upload finalize utan async geometry import es legacy DXF readability check indul;
  - nincs preflight-pending / review-required route-level status.
- `api/services/dxf_geometry_import.py`
  - current-code truth: sikeres parse utan `geometry_revisions` payload `status='parsed'`.
- `api/services/geometry_validation_report.py`
  - current-code truth: validation utan `status='validated'` vagy `status='rejected'`.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - T1 output; rogziti, hogy a prefilter a file upload utan, de a geometry import elott lep be.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - T2 output; rogziti a lifecycle-szintekhez is szukseges fogalmi retegeket.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - T3 output; rogziti a default / override / review-required policy nyelvet, amelyre a T4 state machine raul.

## Jelenlegi repo-grounded helyzetkep
A repoban ma nincs dedikalt DXF prefilter state machine es nincs preflight-specific lifecycle modell.
A jelenlegi truth-kep:
- file ingest oldalon `file_kind` van, lifecycle nincs;
- geometry revision oldalon `status=uploaded/parsed/validated/approved/rejected` van;
- geometry validation report ugyanazt az enumot tukrozi;
- review action log letezik, de nem hajt vegre explicit state transition-t;
- upload route kozvetlen geometry import triggerre ul.

Ezert a T4-ben nem szabad ugy tenni, mintha a repo mar tartalmazna pl.
`preflight_pending`, `preflight_running`, `accepted_for_import`, `quarantined` allapotokat
implementalt enumkent vagy DB mezokent.
A helyes output most egy **architecture-level state machine freeze**, amelyre a kesobbi
E1-T5/E1-T6/E2/E3 taskok ra tudnak ulni.

## Konkret elvarasok

### 1. A lifecycle retegek legyenek explicit kulonvalasztva
A dokumentumnak kulon kell kezelnie legalabb ezt a 4 reteget:
- **file/object ingest lifecycle** (upload oldali vilag)
- **preflight run lifecycle** (jovobeli inspect/repair/acceptance futas)
- **acceptance outcome lifecycle** (accepted / rejected / review-required jellegu dontes)
- **geometry revision lifecycle/status** (meglevo `app.geometry_validation_status` truth)

Rogzitve legyen, hogy ezek nem ugyanazok, es nem cserelhetok fel egymassal.

### 2. A future canonical prefilter state machine legyen V1-minimal es fail-fast
A dokumentum rogzitse a V1 fogalmi prefilter allapotokat, de docs-szinten, nem enumkent.
Minimum javasolt allapotok:
- `uploaded`
- `preflight_pending`
- `preflight_running`
- `preflight_review_required`
- `preflight_rejected`
- `accepted_for_import`
- `imported`
- `validated`
- opcionális kesobbi: `quarantined`, `archived`

Kulon legyen jelezve, melyek current-code truth allapotok es melyek future canonical lifecycle node-ok.

### 3. Rogzitve legyen a mapping a meglevo geometry statuszvilag es a future prefilter world kozott
A dokumentumnak ki kell mondania, hogy:
- `uploaded` jelenleg meglevo geometry status, de a future prefilterben mast is jelenthet file-levelen;
- `parsed` ma geometry revision-level current-code truth, nem file ingest state;
- `validated` / `rejected` ma geometry validation truth, nem teljes prefilter run truth;
- `approved` a geometry enum resze, de a V1 prefilter acceptance gate nem kell hogy review approval workflowkent viselkedjen.

### 4. Kulon legyen a state machine es a persistence modell
A dokumentumnak ki kell mondania, hogy:
- a **state machine** a fogalmi allapotok es atmenetek szerzodese;
- a **data model** majd kesobb donti el, hogy ezek kozul melyik milyen tablakban/mezokben lesz tarolva.

Ez azert fontos, mert a kovetkezo taskok kozul:
- a data model task fog donteni uj tablakkal / mezokkel;
- az API contract task fog endpoint-level payloadot fagyasztani.

### 5. Legyen explicit trigger-es atmeneti tabla
A dokumentumban szerepeljen legalabb magas szintu transition tabla:
- allapot
- trigger/esemeny
- kovetkezo allapot
- notes

Peldak:
- upload finalize
- preflight start
- inspect success
- inspect ambiguous
- repair success
- repair fail
- acceptance pass
- acceptance fail
- geometry import success
- geometry validation pass/fail

### 6. Legyen explicit tiltott atmenet / anti-pattern lista
Kulon legyen kimondva, hogy tilos:
- a `file_kind`-bol kozvetlen lifecycle allapotot kovetkeztetni;
- a geometry revision statuszt file-level ingest statuszkent kezelni;
- a review action logot automatikus lifecycle source-of-truthnak tekinteni;
- a V1 docs taskban retry/lease/job orchestration mechanikat veglegesiteni;
- a project/revision lifecycle enumokat a prefilter state machine helyett hasznalni.

### 7. A dokumentum kapcsolodjon a meglevo repo enum- es lifecycle mintakhoz, de ne implementalja oket
A dokumentumban kulon legyen kimondva, hogy a future prefilter lifecycle domain szerkezetileg
illeszkedhet a repo meglevo lifecycle/status szemleletehez, de ebben a taskban nincs:
- migration,
- enum bovites,
- uj status mezo,
- CRUD,
- route implementation.

### 8. Legyen explicit anti-scope lista
A dokumentum kulon nevezze meg, hogy ebben a taskban nem szabad:
- SQL enum vagy migration igazsagkent bevezetni a future prefilter allapotokat;
- API endpoint response shape-et veglegesiteni;
- review UI flow komponensszintig lemenni;
- worker/background scheduling modellt lefagyasztani.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model/run.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a file ingest, preflight run, acceptance outcome es geometry revision lifecycle retegeket.
- [ ] Rogziti a V1 minimum future canonical prefilter allapotokat docs-szinten.
- [ ] Rogziti a mappinget a meglevo `app.geometry_validation_status` truth es a future prefilter state machine kozott.
- [ ] Rogziti, hogy a state machine es a persistence modell kulon feladat.
- [ ] Tartalmaz magas szintu transition tablat trigger/event -> next state szerkezettel.
- [ ] Tartalmaz tiltott atmenet / anti-pattern listat.
- [ ] Kulon jeloli a current-code truth, a future canonical contract es a later extension reszeket.
- [ ] Repo-grounded hivatkozasokat ad az enum migrationokra, file object / geometry revision / validation report / files route / geometry import service kodhelyekre.
- [ ] Nem vezet be sem SQL migrationt, sem route/service implementaciot.
- [ ] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz.
- [ ] A runner prompt egyertelmuen tiltja a state-machine implementacios scope creep-et.

## Kockazat + mitigacio + rollback
- Kockazat:
  - a task osszecsuszna a data model vagy API contract taskkal;
  - a future prefilter allapotok tul koran enum-truthkent lennenek kezelve;
  - a meglevo geometry statuszvilag es a future prefilter lifecycle osszemosodna.
- Mitigacio:
  - kulon current-code truth / future canonical contract / later extension szekcio;
  - docs-only scope;
  - kotelezo hivatkozas az enum migrationokra, geometry statuszvilagra, files route-ra es geometry import/validation service-re.
- Rollback:
  - docs-only task; a letrehozott dokumentumok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`
- Feladat-specifikus extra teszt nincs; docs-only state-machine freeze task.
