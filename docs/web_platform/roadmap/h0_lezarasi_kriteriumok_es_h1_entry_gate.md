# H0 lezarasi kriteriumok es H1 entry gate

## 1. Cel es hasznalat

Ez a dokumentum a H0 zaro audit gate anyaga.
Feladata, hogy evidence-alapon kimondja:
- a H0 strukturális célrendszer teljesült-e;
- maradt-e blokkolo ellentmondás;
- milyen feltételekkel indítható a H1.

Ez a dokumentum nem feature-specifikáció, hanem döntési kapu.

## 2. H0 lezarasi kriteriumok

### 2.1 Strukturális kriteriumok
- A core schema + domain + run + output + security/storage alapok letezenek.
- A snapshot-first futasi modell es az artifact/projection szetvalasztas kovetkezetes legyen.

### 2.2 Dokumentacios kriteriumok
- A H0 source-of-truth dokumentumok ne mondjanak ellent a migracios valosagnak.
- A task tree es roadmap H0 allitasa osszhangban legyen a tenylegesen vegrehajtott taskokkal.

### 2.3 Migracios kriteriumok
- A H0 migracios lanc lefedje:
  - app schema + enumok,
  - core domain tablakat,
  - file/geometry/audit/review/derivative reteget,
  - run/snapshot/queue/log/output reteget,
  - baseline `app.*` RLS alapokat.
- A storage baseline security allapot hosted projekten funkcionalisan teljesuljon, akkor is,
  ha a rollout utja nem tisztan migracios (split/provisioning caveat).

### 2.4 Security/storage kriteriumok
- DB-RLS ownership/project-bound alapok aktivak legyenek.
- Storage policy funkcionalisan a kanonikus H0 bucket/path szerzodesre epuljon.
- Service-role boundary egyertelmu legyen.

## 3. H0 completion matrix

| H0 task | Statusz | Bizonyitek |
| --- | --- | --- |
| H0-E1-T1 | PASS | `codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.md`; `codex/reports/web_platform/h0_e1_t1_modulhatarok_veglegesitese.verify.log` |
| H0-E1-T2 | PASS | `codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.md`; `codex/reports/web_platform/h0_e1_t2_domain_entitasterkep_veglegesitese.verify.log` |
| H0-E1-T3 | PASS | `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`; `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.verify.log` |
| H0-E2-T1 | PASS | `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`; `codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md` |
| H0-E2-T2 | PASS | `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`; `codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md` |
| H0-E2-T3 | PASS | `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`; `codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md` |
| H0-E2-T4 | PASS | `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`; `codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md` |
| H0-E2-T5 | PASS | `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`; `codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md` |
| H0-E3-T1 | PASS | `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`; `codex/reports/web_platform/h0_e3_t1_file_object_modell.md` |
| H0-E3-T2 | PASS | `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`; `codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md` |
| H0-E3-T3 | PASS | `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`; `codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md` |
| H0-E3-T4 | PASS | `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`; `codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md` |
| H0-E5-T1 | PASS | `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`; `codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md` |
| H0-E5-T2 | PASS | `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`; `codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md` |
| H0-E5-T3 | PASS | `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`; `codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md` |
| H0-E6-T1 | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`; `codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md` |
| H0-E6-T2 | PASS (split rollout caveat) | `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`; `docs/web_platform/architecture/h0_security_rls_alapok.md`; `docs/known_issues/web_platform_known_issues.md` (KI-001 RESOLVED); `codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md` |

Megjegyzes:
- A korai H0 taskok namingje helyenkent rovidebb slugot hasznal (`*_veglegesitese`), de tartalmilag megfelel a H0-E1-T1/T2 celpontoknak.

## 4. Docs vs migracio vs task tree audit eredmeny

### 4.1 Osszhangban levo pontok
- A run/snapshot/queue/output tablavilag migraciosan letezik es docsban is explicit.
- Az artifact/projection szetvalasztas konzisztens (`run_artifacts` vs `run_layout_*` + `run_metrics`).
- A storage bucket/path source-of-truth es a baseline security allapot dokumentalt + funkcionalisan aktiv:
  `app.*` RLS migraciosan, `storage.objects` policy manualis hosted provisioninggel.
- A geometry derivative DB-truth hatar explicit maradt (nem storage-truth).

### 4.2 Minimalis tisztitas ebben a taskban
- A H0 roadmap dokumentumban a regi `docs/platform/*` kimeneti peldak frissitve lettek a jelenlegi `docs/web_platform/*` source-of-truth pathokra.
- A backlog task treeben jelezve lett a H0-E4 historikus bontas es annak H0-E2-T4/T5 megfeleltetese.
- A backlog task tree H0-E7 blokkja megkapta a konkret H0 zaro gate dokumentum hivatkozasat.

## 5. Blokkolo vs advisory elteresek

### 5.1 Blokkolo elteresek
- Nincs azonositott blokkolo strukturális elteres.

### 5.2 Advisory elteresek
- Az architecture dokumentumban vannak `public.*` peldak a kesobbi (nem H0 scope-os) manufacturing/retegben; ez H1 inditast nem blokkol, de H2 elott erdemes teljes namespace-normalizaciot futtatni.

## 6. H1 entry gate itelet

**Itelet: PASS WITH ADVISORIES**

Indoklas:
- A H0 strukturális build-up teljesult, a taskok evidence-alapon PASS allapotban vannak.
- A H1 indulashoz szukseges domain/run/security/storage alapok konzisztensen leteznek.
- A storage rollout utja eltert a sima migracios uttol (hosted owner-limit miatti split), de a
  celzott minimalis H0 security allapot funkcionalisan teljesult.
- Marado pontok advisory jelleguek, nem H1-blokkolok.

## 7. Mit jelent ez a gyakorlatban?

- A H1 indithato a jelenlegi H0 alapokon.
- H0-ban nem szukseges ujranyitni a core schema, run backbone, storage/RLS baseline retegeket.
- A storage provisioning caveat tortenetileg relevans marad, de nem csokkenti a H0 lezarhatósagat.
- A H1 soran figyelemben tartando advisory: H2 elott erdemes a nem-H0 docs SQL peldak namespace konzisztencia auditjat vegrehajtani.
