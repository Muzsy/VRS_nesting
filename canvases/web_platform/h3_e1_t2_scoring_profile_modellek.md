# H3-E1-T2 Scoring profile modellek

## Funkcio
A feladat a H3 strategy/scoring domain masodik alaplepese.
A cel, hogy a scoring es tie-breaker vilag explicit, owner-scoped,
verziozott truth-retegkent megjelenjen a repoban, kulon a H2 manufacturing
metrikaktol, kulon a H3 kesobbi run evaluation engine-tol, es kulon a
projekt-szintu persisted selection vilagtol.

A jelenlegi repoban mar megvan:
- a H1 stabil run/artifact/project gerinc;
- a H2 manufacturing metrics truth (`run_manufacturing_metrics`), amelyre a
  kesobbi evaluation engine majd tamaszkodhat;
- a H3 roadmapben a strategy/scoring domain kulon backlog-epickent van kezelve.

Ez a task ezekre epulve a scoring preferenciakat emeli kulon domainne.
A fokusz most nem score-szamitas, hanem a score-szamitas kesobbi inputjanak
persistalt, verziozott, auditálhato definialasa.

Ez a task szandekosan nem run evaluation engine, nem ranking engine, nem
project-level selection task, nem batch orchestration, es nem frontend-only
beallitasoldal. A scope kifejezetten az, hogy a scoring profilok es azok
verzioi kulon persisted truth-retegkent letezzenek, owner-scoped CRUD/list
szolgaltatassal es ellenorizheto smoke-kal.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.scoring_profiles` tabla owner-scoped alapprofilhoz;
  - `app.scoring_profile_versions` tabla verziozott scoring truthhoz;
  - a minimum H3 dokumentumban szereplo mezok:
    - `weights_jsonb`
    - `tie_breaker_jsonb`
    - `threshold_jsonb`
    - `is_active`
  - owner-scoped CRUD/list/get/update/delete service reteg a profilokra;
  - owner-scoped version create/list/get/update/delete service reteg;
  - dedikalt API route a scoring profile domainhoz;
  - `api/main.py` route-bekotes;
  - task-specifikus smoke a fo invariansokra.
- Nincs benne:
  - `project_scoring_selection` vagy barmilyen persisted project-level selection;
  - run snapshot vagy run create flow frissitese;
  - evaluation engine (`run_evaluations`);
  - ranking engine vagy best-by-objective projection;
  - frontend preference UI;
  - business metrics vagy remnant scoring logika.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H3-E1-T2 task: scoring profile modellek.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - itt szerepel a javasolt `scoring_profiles` / `scoring_profile_versions`
    tablaforma, valamint a scoring profile domain boundary-ja.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-A2 szekcio leirja, hogy a scoring explicit es verziozhato kell legyen.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a decision layer ne csusszon vissza manufacturing,
    preview vagy export scope-ba.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a runtime futasok kesobbi snapshotolhatosaga miatt a scoring truthnak
    kulon, visszakeresheto persisted retegnek kell lennie.
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
  - minta owner-scoped, verziozott profile-domain migraciora.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - minta project-level selection kulon truth-retegkent valo kezelesere;
    fontos ellenpelda, mert ez a task meg nem selection.
- `api/services/project_manufacturing_selection.py`
  - minta owner/project konzisztencia-validaciora, de itt csak a profile
    domain owner-konzisztencia a relevans.
- `api/services/manufacturing_metrics_calculator.py`
  - peldaja annak, hogy a H3 kesobbi evaluation engine majd persisted metrics
    truthra epul; ez a task meg csak a scoring truthot hozza letre.
- `api/main.py`
  - ide kell majd a route-bekotes.

### Konkret elvarasok

#### 1. Kulon scoring profile truth-reteg kell
A task vezesse be a H3 reszletes doksiban javasolt kulon domain tablat:
- `app.scoring_profiles`
- `app.scoring_profile_versions`

Minimum elvart profile mezok:
- `id`
- `owner_user_id`
- `name`
- `description`
- `created_at`

Minimum elvart version mezok:
- `id`
- `scoring_profile_id`
- `version_no`
- `weights_jsonb`
- `tie_breaker_jsonb`
- `threshold_jsonb`
- `is_active`
- `created_at`

A version tabla legalabb a `(scoring_profile_id, version_no)` egyediseget
biztositsa.

#### 2. A scoring domain maradjon kulon az evaluation engine-tol
Ez a task meg nem szamol score-t.
Nem szabad ebben a taskban bevezetni:
- `run_evaluations` tablakat;
- `total_score` logikat;
- batch rankinget;
- objective projection queryket.

A scoring profile itt csak a kesobbi evaluation engine konfiguracios truth-ja.

#### 3. A scoring JSON-ok explicit, de nem tulokoskodott szerzodesek legyenek
A `weights_jsonb` legalabb a H3 doksi peldaihoz igazodjon, peldaul:
- `utilization_weight`
- `unplaced_penalty`
- `sheet_count_penalty`
- `remnant_value_weight`
- `process_time_penalty`
- `priority_fulfilment_weight`
- `inventory_consumption_penalty`

A `tie_breaker_jsonb` a tie-break sorrendet vagy szabalyokat tarolhatja.
A `threshold_jsonb` minimum elfogadasi / kizarasi vagy normalizacios kuszobok
helye.

Fontos: ebben a taskban nem kell vegleges matematikai sulyformula-motor.
A cel a verziozott, auditálhato persisted truth.

#### 4. Owner-scoped CRUD/list/get/update/delete kell
A scoring profile domain csak owner-scoped legyen.
Minimum elvart service-szint:
- profile create
- profile list
- profile get
- profile update
- profile delete
- version create
- version list
- version get
- version update
- version delete

A service validalja, hogy:
- a profile es a hozza tartozo version owner-konzisztensek;
- egy user csak a sajat scoring profile-jait es verzioit eri el;
- egy version nem hozhato letre idegen owner profile-ja ala.

#### 5. A task ne vezessen be project-level persisted selectiont
A H3 doksi kulon taskkent kezeli:
- `project_run_strategy_selection`
- `project_scoring_selection`

Ez a task ezeket meg nem hozza letre.
Nincs benne:
- `project_scoring_selection` tabla;
- project route vagy project service modositas;
- run create flow `active_scoring_profile_version_id` bekotese.

#### 6. Route legyen, de csak a profile domainhez
Keszuljon dedikalt route, peldaul `api/routes/scoring_profiles.py`, amely
owner-scoped profile es version muveleteket ad.

A task ne nyisson ki:
- batch API-t;
- evaluation API-t;
- ranking API-t;
- viewer/comparison API-t.

#### 7. A smoke bizonyitsa a fo H3-E1-T2 invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- owner-scoped scoring profile letrehozhato;
- scoring profile version letrehozhato es `version_no` konzisztens;
- a `weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb` persisted modon
  visszaolvashato;
- idegen owner nem fer hozza mas scoring profile-jahoz;
- version profile-owner mismatch hibat ad;
- a task nem hoz letre `project_scoring_selection` truthot;
- a task nem hoz letre `run_evaluations` vagy ranking artefaktokat;
- a task nem ir vissza H2 metrics vagy run truth tablaba.

### DoD
- [ ] Letezik kulon `app.scoring_profiles` persisted truth reteg.
- [ ] Letezik kulon `app.scoring_profile_versions` persisted truth reteg.
- [ ] A scoring profile domain owner-scoped es verziozott.
- [ ] A version rekordok legalabb `weights_jsonb`, `tie_breaker_jsonb`,
      `threshold_jsonb`, `is_active` mezoket hordoznak.
- [ ] Keszul dedikalt scoring profile service reteg.
- [ ] Keszul dedikalt scoring profile API route.
- [ ] A route be van kotve az `api/main.py`-ba.
- [ ] A task nem vezet be `project_scoring_selection` persisted selectiont.
- [ ] A task nem vezet be `run_evaluations`, ranking vagy comparison scope-ot.
- [ ] A task nem ir vissza H2 manufacturing truth tablaba.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a scoring profile task egybol evaluation engine-be csuszik at;
  - a selection logicat idokolatlanul elorehozza;
  - a scoring JSON szerzodes ad hoc frontend-configgá valik;
  - az owner-scoping hiányos marad, es idegen user profilja is olvashato;
  - a task visszanyul H2 metrics vagy run tablaba.
- Mitigacio:
  - explicit out-of-scope lista;
  - kulon profile/version truth reteg;
  - owner-konzisztencia validacio;
  - task-specifikus smoke a no-selection / no-evaluation / no-H2-write
    invariansokra.
- Rollback:
  - a migration + service + route + smoke egy task-commitban visszavonhato;
  - a H2 manufacturing truth reteg erintetlen marad, mert ez a task csak uj,
    kulon H3 truth-ot vezet be.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/scoring_profiles.py api/routes/scoring_profiles.py scripts/smoke_h3_e1_t2_scoring_profile_modellek.py`
  - `python3 scripts/smoke_h3_e1_t2_scoring_profile_modellek.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `api/services/project_manufacturing_selection.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/main.py`
