# H3-E1-T1 Run strategy profile modellek

## Funkcio
Ez a task nyitja meg a H3 decision-layer fo vonalat a H2 lezart manufacturing
mainline utan.
A cel, hogy a futtatasi strategia kulon, owner-scoped, verziozott domainne
valjon, es ne ad hoc `run_config` vagy frontend-hardcode szinten legyen tarolva.

A jelenlegi repoban mar megvan:
- a stabil H1 run/snapshot/result gerinc;
- a H2 manufacturing es postprocess mainline truth reteg;
- a H2 -> H3 entry gate dokumentacio;
- owner-scoped, profile + version mintat ad a manufacturing es a
  postprocessor domain.

Ez a task ezekre epitve bevezeti a run strategy domain minimalis, de valos
schema + CRUD alapjat.

Ez a task szandekosan nem scoring profile, nem project-level strategy
selection persistence, nem batch/orchestrator, nem run evaluation/ranking, nem
remnant domain, nem snapshot-builder integracio, es nem worker/solver
behaviour atdrotozas.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_strategy_profiles` tabla bevezetese owner-scoped logikai
    strategy profile csoportkent;
  - `app.run_strategy_profile_versions` tabla bevezetese owner-scoped,
    verziozott strategy truth-kent;
  - minimalis, repo-hu mezo-keszlet a strategy domainhez, peldaul:
    - profile szinten: `strategy_code`, `display_name`, `description`,
      `lifecycle`, `is_active`, `metadata_jsonb`;
    - version szinten: `version_no`, `lifecycle`, `is_active`,
      `solver_config_jsonb`, `placement_config_jsonb`,
      `manufacturing_bias_jsonb`, `notes`, `metadata_jsonb`;
  - owner-konzisztencia biztositas ugy, hogy a version csak a sajat owner
    profile-ja alatt johet letre es maradhat ervenyes;
  - owner-scoped CRUD service + route a strategy profile es nested version
    domainhez;
  - route regisztralasa az `api/main.py`-ban;
  - task-specifikus smoke a CRUD / owner-boundary / versioning invariansokra.
- Nincs benne:
  - `app.scoring_profiles` vagy barmilyen scoring/tie-breaker domain;
  - `app.project_run_strategy_selection` vagy barmilyen persisted
    project-level selection tabla;
  - `run_batches`, `run_batch_items`, evaluation vagy ranking reteg;
  - `run_snapshot_builder` vagy `run_creation` strategy-integracio;
  - worker/solver runtime atallitasa strategy alapjan;
  - `machine_catalog`, `material_catalog` vagy barmilyen manufacturing
    catalog/FK vilag kitalalasa;
  - `run_configs` nagy ujratervezese.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H3-E1-T1 task es a H3-E1 bontas.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - itt szerepel a run strategy profile domain javasolt schemaja es a
    strategy/scoring/project-selection szeparacio.
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
  - ez rogziti, hogy a H3 fo vonala nyithato.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: strategy/scoring domain kulon dontesi reteg, nem
    manufacturing truth es nem export artifact.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a strategy domain kesobb snapshotolhato lesz, de ebben a taskban meg nem
    szabad a snapshot buildert osszedrotozni vele.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - manufacturing profile/version domain minta owner-konzisztenciara,
    composite FK-ra, indexelesre es policy mintakra.
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
  - a legkozelebbi profile/version CRUD domain aktivacios minta.
- `api/services/postprocessor_profiles.py`
  - service-side owner-scoped profile + nested version CRUD minta.
- `api/routes/postprocessor_profiles.py`
  - route- es request/response modell minta a nested version API-hoz.
- `api/routes/run_configs.py`
  - fontos kontrollminta arra, hogy a strategy domain ne csusszon vissza a
    legacy run_config vilagba.
- `api/main.py`
  - az uj router regisztralasanak helye.

### Konkret elvarasok

#### 1. A strategy domain legyen kulon truth, ne legacy run_config alias
A task vezesse be a kulon strategy profile es strategy version truth reteget.
A strategy domain ne azonosuljon:
- a technology setup vilaggal;
- a manufacturing profile vilaggal;
- a scoring profile vilaggal;
- a `run_configs` tablaval vagy route-tal.

A strategy azt irja le, hogyan akarunk futtatni, peldaul:
- gyors / lightweight futas,
- aggressive fill,
- priority-first,
- manufacturing-biased,
- remnant-aware.

#### 2. A schema legyen minimalis, de valos es verziozott
Minimum elvart tablakkent:
- `app.run_strategy_profiles`
- `app.run_strategy_profile_versions`

Minimum elvart profile mezok:
- `id`
- `owner_user_id`
- `strategy_code`
- `display_name`
- `description`
- `lifecycle`
- `is_active`
- `metadata_jsonb`
- `created_at`
- `updated_at`

Minimum elvart version mezok:
- `id`
- `run_strategy_profile_id`
- `owner_user_id`
- `version_no`
- `lifecycle`
- `is_active`
- `solver_config_jsonb`
- `placement_config_jsonb`
- `manufacturing_bias_jsonb`
- `notes`
- `metadata_jsonb`
- `created_at`
- `updated_at`

Elvart integritas:
- `unique (owner_user_id, strategy_code)` profile szinten;
- `unique (run_strategy_profile_id, version_no)` version szinten;
- composite owner-konzisztencia a profile es version kozott;
- pozitiv version szam;
- non-empty `strategy_code` es `display_name`.

A migration igazodjon a H2 domain taskok mintajahoz: tabla + index + owner
policy + composite integritas, uj nem letezo enumvilag nelkul.

#### 3. Legyen owner-scoped CRUD route/service nested version kezelessel
Keszits dedikalt service-t es route-ot:
- `api/services/run_strategy_profiles.py`
- `api/routes/run_strategy_profiles.py`

Minimum API-scope:
- profile create/list/get/update/delete;
- version create/list/get/update/delete a profile ala rendezve;
- owner-scoped hozzaferes access tokennel;
- idegen owner strategy/profile/version ne legyen olvashato vagy modosithato;
- version csak a sajat profile alatt legyen kezelheto.

A route illeszkedjen a H2 postprocessor/cut-rule mintakhoz, ne vezessen be uj,
elteto API stilust.

#### 4. A "projectbol valaszthato" DoD ne csusszon at T3 scope-ba
A task tree rovid DoD-je ugy szol, hogy a strategy profil projektbol
valaszthato, mikozben a persisted project-level selection domain kulon
H3-E1-T3 task.

Ebben a taskban ezt ugy kell ertelmezni, hogy:
- a strategy domain mar valos, listazhato es owner-scoped modon kezelheto;
- a kesobbi project selection service mar tud mire hivatkozni;
- de `project_run_strategy_selection` tabla vagy barmilyen persisted selection
  meg nem jon letre.

Tehat a T1 DoD teljesitese itt: a strategy profil mar valid, visszakeresheto,
listazhato valasztasi jelolt; a projecthez mentes T3-ban jon.

#### 5. A task ne drotozza ra a strategy domaint a snapshotra vagy a runokra
A H3 tovabbi taskjai majd gondoskodnak a selectionrol, a batchrol es a score-rol.
Ebben a taskban ne tortenjen:
- `run_snapshot_builder` modositas;
- `run_creation` modositas;
- `nesting_runs` vagy `nesting_run_snapshots` schema bovites;
- strategy auto-alkalmazas a solver inputra;
- worker-side runtime valtozas.

#### 6. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- strategy profile owner-scoped CRUD mukodik;
- nested version CRUD mukodik;
- version szam novelodik (`1, 2, ...`);
- version nem hozhato letre idegen owner profile alatt;
- idegen owner nem latja/modositja a masik owner strategy domainjet;
- nincs scoring tabla vagy project selection tabla erintett write pathban;
- nincs snapshot/run/service side effect a smoke altal erintett write logban.

### DoD
- [ ] Letrejott a `run_strategy_profiles` es `run_strategy_profile_versions`
      truth reteg.
- [ ] A schema owner-scoped, verziozott es composite owner-konzisztens.
- [ ] Keszult dedikalt `api/services/run_strategy_profiles.py` service.
- [ ] Keszult dedikalt `api/routes/run_strategy_profiles.py` route.
- [ ] Az uj route regisztralva lett az `api/main.py`-ban.
- [ ] A strategy domain kulon marad a technology / manufacturing / scoring /
      `run_configs` vilagoktol.
- [ ] Nem jott letre `project_run_strategy_selection` tabla vagy mas T3-scope-u
      persisted selection.
- [ ] Nem tortent snapshot-builder vagy run-creation integracio.
- [ ] Keszult task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t1_run_strategy_profile_modellek.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a strategy domain osszemosodik a legacy `run_configs` vagy a kesobbi
    scoring domain fele;
  - a task tul koran T3-scope-u project selection tablakat hoz letre;
  - a version owner-konzisztencia nem lesz eleg eros;
  - a strategy config JSON vilag szetfolyik tobb parhuzamos mezore.
- Mitigacio:
  - explicit no-scoring / no-selection / no-batch / no-snapshot boundary;
  - owner-consistency migration + service + smoke szinten;
  - pontosan harom strategy config jsonb mezo a version szinten:
    `solver_config_jsonb`, `placement_config_jsonb`,
    `manufacturing_bias_jsonb`;
  - `run_configs` csak kontrollminta, nem celpont.
- Rollback:
  - a migration + route/service + smoke egy task-commitban visszavonhato;
  - H1/H2 run es manufacturing mainline erintetlen marad;
  - T3 project selection kesobb tisztan raepitheto vagy attervezheto.

### Ellenorzesi parancsok
- Kotelezo:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t1_run_strategy_profile_modellek.md`
- Ajanlott:
  - `python3 -m py_compile api/services/run_strategy_profiles.py api/routes/run_strategy_profiles.py scripts/smoke_h3_e1_t1_run_strategy_profile_modellek.py`
  - `python3 scripts/smoke_h3_e1_t1_run_strategy_profile_modellek.py`
