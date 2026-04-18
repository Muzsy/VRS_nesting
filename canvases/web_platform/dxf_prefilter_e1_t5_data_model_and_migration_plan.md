# DXF Prefilter E1-T5 Data model es migration terv

## Funkcio
Ez a task a DXF prefilter lane otodik, **docs-only data-model es migration-plan freeze** lepese.
A cel most nem SQL migration implementacio, nem uj tabla letrehozasa, nem route/service kod,
nem RLS es nem UI allapotkezeles, hanem annak rogzitese, hogy a jovobeli DXF prefilter V1
milyen **adatmodellre** es milyen **migration-sorrendre** fog raulni a meglevo upload ->
geometry import -> validation truth-lancra.

A task kozvetlenul az E1-T1 / E1-T2 / E1-T3 / E1-T4 utan jon:
- a T1 rogzitette a V1 scope es integration boundary keretet;
- a T2 lefagyasztotta a glossaryt es role-szinteket;
- a T3 rogzitette a policy matrix es rules profile schema fogalmi szerzodeset;
- a T4 kulonvalasztotta a file ingest, preflight run, acceptance outcome es geometry status lifecycle retegeket;
- ez a T5 ezekre epitve lefagyasztja a **future canonical data-modelt** es a **migration slicing** iranyat.

A tasknak a jelenlegi repora kell raulnie:
- ma letezik `app.file_objects` mint raw storage-reference truth;
- ma letezik `app.geometry_revisions` mint canonical geometry revision truth;
- ma letezik `app.geometry_validation_reports` es `app.geometry_review_actions` mint audit/review layer;
- ma leteznek owner-scoped, versioned profile mintak (`run_strategy_profiles`, `run_strategy_profile_versions`, `scoring_profiles`, `scoring_profile_versions`);
- ma nincs dedikalt DXF prefilter profile/version domain, nincs preflight run tabla es nincs preflight artifact/diagnostics persistence.

Ez a task azert kell, hogy a kovetkezo E1-T6 API contract es E2/E3 implementacios taskok ne ad hoc modon talaljak ki:
- milyen uj tablakat kell bevezetni;
- melyik uj truth melyik meglevo truth-ra ul ra;
- hol legyen owner-scoped profile/version minta;
- mi az, ami file-level source lineage, es mi az, ami preflight-run-level audit;
- milyen migration-szeletekben erdemes ezt bevezetni.

## Scope
- Benne van:
  - a future canonical DXF prefilter data-model docs-level definicioja;
  - current-code truth vs future canonical tables/relations kulonvalasztasa;
  - a rules profile/version domain storage-irany rogzitese;
  - a preflight run / diagnostics / artifact / review-decision persistence fogalmi szetvalasztasa;
  - a minimalis FK/ownership/index integrity elvek docs-szintu rogzitese;
  - egy migration-plan dokumentum: milyen logikai szeletekben erdemes a jovobeli SQL-t bevezetni;
  - annak rogzitese, mi marad explicit kesobbi task (RLS, CRUD, routes, worker orchestration, UI binding).
- Nincs benne:
  - SQL migration file letrehozasa;
  - uj enum vagy tabla implementacio;
  - route/service vagy frontend kod;
  - RLS policy;
  - konkret API payload shape;
  - review UX komponensszerkezet;
  - background job/retry mechanika;
  - tenyleges geometry import gate implementation.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
  - current-code truth: `app.file_kind`, `app.geometry_role`, `app.geometry_validation_status`, `app.revision_lifecycle` enumok;
  - bizonyitja, hogy a repo mar kulon enum-truthokat hasznal domainenkent.
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
  - current-code truth: `app.file_objects` mint raw file/storage truth.
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
  - current-code truth: `app.geometry_revisions` mint source file-bol szarmaztatott geometry truth.
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
  - current-code truth: `app.geometry_validation_reports`, `app.geometry_review_actions` mint audit/review layer.
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
  - current-code truth: owner-scoped profile + version minta.
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
  - current-code truth: profile/version domain masodik bizonyitott mintaja.
- `api/routes/files.py`
  - current-code truth: upload finalize utan geometry import trigger indul, preflight persistence nincs.
- `api/services/dxf_geometry_import.py`
  - current-code truth: file-object -> geometry-revision kapcsolat, parse pipeline truth.
- `api/services/geometry_validation_report.py`
  - current-code truth: geometry validation audit/report truth.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - T1 output; rogziti, hogy a prefilter a file upload utan, de a geometry import elott lep be.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - T2 output; rogziti a role- es fogalmi szinteket.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - T3 output; rogziti a rules-profile mezo-szintu szerzodeset.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - T4 output; rogziti a lifecycle retegeket, amelyekre a persistence modell raul.

## Jelenlegi repo-grounded helyzetkep
A repoban ma nincs dedikalt DXF prefilter persistence domain.
A jelenlegi truth-kep:
- a raw upload truth az `app.file_objects`;
- a geometry parse truth az `app.geometry_revisions`;
- a validation/audit truth az `app.geometry_validation_reports`;
- a human review action log truth az `app.geometry_review_actions`;
- owner-scoped versioned profile minta letezik, de nem DXF prefilterre.

Ezert a T5-ben nem szabad ugy tenni, mintha ma mar letezne pl.
`app.dxf_rules_profiles`, `app.dxf_rules_profile_versions`, `app.preflight_runs`,
`app.preflight_artifacts`, `app.preflight_diagnostics` vagy `app.preflight_review_decisions`.
A helyes output most egy **architecture-level data-model es migration-plan freeze**,
amelyet a kesobbi SQL taskok konkret migrationokra bontanak.

## Konkret elvarasok

### 1. Current-code truth es future canonical data-model legyen explicit kulonvalasztva
A dokumentumnak kulon kell kezelnie:
- mi letezik ma mar tablakkent/es enumkent;
- mi future canonical V1 prefilter domain tabla;
- mi marad kesobbi extension vagy optional slice.

### 2. A future canonical data-model legyen owner- es lineage-grounded
A dokumentumnak rogzitnie kell, hogy a prefilter domain nem valhat kulonallo,
source-lineage nelkuli fekete dobozza.
Minimum fogalmi kapcsolatok:
- profile/version domain owner-scoped legyen;
- a preflight run file object lineage-ra uljon;
- a normalized DXF es diagnostics artifact-szeru, de preflight truthhoz kotott legyen;
- a review decision domain ne keveredjen a meglevo geometry review action loggal.

### 3. A rules profile domain illeszkedjen a meglevo profile/version mintakhoz
A dokumentumnak ki kell mondania, hogy a future DXF rules profile domain szerkezetileg
kovesse a repoban mar bizonyitott owner-scoped + versioned mintat, de docs-szinten,
implementacio nelkul.
Minimum fogalmi entitasok:
- `dxf_rules_profiles`
- `dxf_rules_profile_versions`

Kulon legyen jelezve:
- mely mezok profile-level metadatak;
- mely mezok version-level policy truthok.

### 4. A preflight run persistence kulonuljon el a geometry revision truth-tol
A dokumentumnak rogzitenie kell, hogy a preflight futas kulon domain objektum,
nem irhato ra egy az egyben a `geometry_revisions` vagy `geometry_validation_reports` vilagra.
Minimum fogalmi entitasok:
- `preflight_runs`
- `preflight_diagnostics`
- `preflight_artifacts`
- opcionailag `preflight_review_decisions`

Kulon legyen jelezve, hogy:
- a geometry revision tovabbra is geometry truth marad;
- a preflight run csak gate / normalization / diagnostics domain truth.

### 5. Legyen explicit table-by-table javasolt oszlopirany docs-szinten
A dokumentumban legyen legalabb magas szintu oszlopirany a future canonical tablakhhoz:
- PK
- owner/file/project hivatkozasok
- version szam / lifecycle / is_active ahol relevans
- metadata_jsonb / config_jsonb jellegu mezok
- created_at / updated_at jellegu audit mezok

De ne valjon vegleges DDL-ve.

### 6. Legyen explicit FK / ownership / uniqueness / indexing elv
A dokumentumban szerepeljen, hogy a future domainnel hogyan kell gondolkodni:
- owner-konzisztencia a profile/version domainben;
- file lineage konzisztencia a preflight run domainben;
- uniqueness elvek (pl. profile code owner alatt, version_no profile alatt, sequence per run);
- alap index iranyok.

### 7. Legyen migration slicing terv
A dokumentumban szerepeljen logikai migration-sorrend, pl.:
- profile/version truth slice
- preflight run + diagnostics slice
- artifact/review decision slice
- opcionais rollout/compat slice

A cel, hogy a kesobbi SQL taskokat lehessen kicsi, biztonsagos migraciokra bontani.

### 8. Legyen explicit kulonvalasztva a data model es a lifecycle / API / UI szint
A dokumentum mondja ki, hogy:
- a lifecycle mar T4-ben rogzitve van;
- az API payload majd T6-ban jon;
- a UI settings/review flow majd E4-ben jon;
- ez a task csak persistence truth es migration slicing.

### 9. Legyen explicit anti-scope lista
Kulon legyen kimondva, hogy ebben a taskban nem szabad:
- konkret SQL migrationt vagy DDL-t veglegesiteni;
- RLS policyt tervezni reszletesen;
- route/service payloadot befagyasztani;
- UI tablat vagy review modalt tervezni;
- worker/background queue modellt tarolasi truthkent rogzitni.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t5_data_model_and_migration_plan.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan/run.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a current-code truth es a future canonical prefilter data-model reteget.
- [ ] Rogziti, hogy a future rules profile domain owner-scoped + versioned mintat kovessen a meglevo profile/version mintak alapjan.
- [ ] Rogziti, hogy a preflight run persistence domain kulon truth legyen a `geometry_revisions` es `geometry_validation_reports` vilagtol.
- [ ] Tartalmaz magas szintu, table-by-table adatmodell-javaslatot docs-szinten legalabb a profile/version, preflight run, diagnostics, artifact es review-decision retegre.
- [ ] Tartalmaz FK / ownership / uniqueness / indexing elveket docs-szinten.
- [ ] Tartalmaz migration slicing tervet logikai szeletekre bontva.
- [ ] Kulon jeloli a current-code truth, a future canonical contract es a later extension reszeket.
- [ ] Repo-grounded hivatkozasokat ad a meglevo file/geometry/validation/review tablakhhoz es a mar letezo profile/version migration mintakhoz.
- [ ] Nem vezet be sem SQL migrationt, sem route/service implementaciot, sem RLS policyt.
- [ ] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz.
- [ ] A runner prompt egyertelmuen tiltja a data-model implementacios scope creep-et.

## Kockazat + mitigacio + rollback
- Kockazat:
  - a task osszecsuszna a kovetkezo API contract vagy SQL migration taskkal;
  - a future prefilter tablakat current truthkent kezelnek;
  - a preflight truth osszemosodna a geometry revision truth-tal;
  - a docs tul koran RLS/CRUD/route reszletekbe csuszik.
- Mitigacio:
  - kulon current-code truth / future canonical contract / later extension szekcio;
  - docs-only scope;
  - kotelezo hivatkozas a meglevo migration patternokra es a jelenlegi file/geometry/validation/review tablakhhoz.
- Rollback:
  - docs-only task; a letrehozott dokumentumok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`
- Feladat-specifikus extra teszt nincs; docs-only data-model freeze task.
