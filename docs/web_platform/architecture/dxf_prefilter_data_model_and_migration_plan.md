# DXF Prefilter Data Model and Migration Plan (E1-T5)

## 1. Cel
Ez a dokumentum docs-only modban lefagyasztja a DXF prefilter V1 persistence
szerzodeset es a migration slicing tervet. A cel nem SQL implementacio, hanem a
jovobeli migration taskokhoz egy kozos, repo-grounded adatmodell-keret adasa.

## 2. Scope boundary
- Ez architecture-level data-model es migration-plan freeze.
- Nem SQL DDL, nem migration file, nem API payload, nem route/service kod.
- Nem RLS policy implementacio es nem UI state modell.

## 3. Current-code truth (repo-grounded)

### 3.1 Meglevo tablakh es enumok
- `app.file_objects` a file/object ingest truth (`project_id`, storage lineage,
  `file_kind`, hash metadata).
- `app.geometry_revisions` a canonical geometry revision truth (`source_file_object_id`,
  `geometry_role`, `revision_no`, `status`, canonical payload/hash).
- `app.geometry_validation_reports` a geometry validator audit truth (`validation_seq`,
  `status`, report payload).
- `app.geometry_review_actions` a human review action-log truth.
- `app.geometry_validation_status` enum jelenleg a geometry revision/report statusz vilag.

### 3.2 Profile/version domain mintak
A repoban mar letezik owner-scoped + versioned profile minta:
- `app.run_strategy_profiles` + `app.run_strategy_profile_versions`
- `app.scoring_profiles` + `app.scoring_profile_versions`

Kozos mintak:
- profile tabla owner (`owner_user_id`) alatt egyedi kod/nevvel,
- version tabla `version_no`-val,
- owner-konzisztencia kompozit FK-val (`(profile_id, owner_user_id)`),
- `lifecycle`, `is_active`, `metadata_jsonb`, audit timestamp mezok.

### 3.3 Mi NEM letezik ma
A repoban jelenleg nincs implementalt DXF prefilter persistence domain, tehat nincs:
- `app.dxf_rules_profiles`
- `app.dxf_rules_profile_versions`
- `app.preflight_runs`
- `app.preflight_diagnostics`
- `app.preflight_artifacts`
- `app.preflight_review_decisions`

## 4. Future canonical prefilter persistence contract (V1, docs-level)

### 4.1 Alapelv
A future prefilter persistence kulon truth reteg legyen:
- nem olvad ossze a geometry revision truth-tal,
- de explicit lineage/FK kapcsolattal uljon a meglevo `file_objects` ->
  `geometry_revisions` lancra,
- es kovesse a repoban mar bizonyitott owner-scoped profile/version mintat.

### 4.2 Table-by-table javaslat (docs-level, nem DDL)

#### 4.2.1 `dxf_rules_profiles` (future canonical)
Fogalmi szerep:
- owner-szintu profile csoport a DXF prefilter policy keszletekhez.

Javasolt oszlopirany:
- `id` (PK uuid)
- `owner_user_id` (FK -> `app.profiles.id`)
- `profile_code` (owner alatt egyedi)
- `display_name`, `description`
- `lifecycle`, `is_active`
- `metadata_jsonb`
- `created_at`, `updated_at`

#### 4.2.2 `dxf_rules_profile_versions` (future canonical)
Fogalmi szerep:
- profile-on beluli policy truth verziozasa.

Javasolt oszlopirany:
- `id` (PK uuid)
- `dxf_rules_profile_id` (FK -> `dxf_rules_profiles.id`)
- `owner_user_id` (owner-konzisztencia FK komponens)
- `version_no` (profile-on belul szekvencialis egyedi)
- `lifecycle`, `is_active`
- `rules_config_jsonb` (T3 policy schema alapjan)
- `notes`, `metadata_jsonb`
- `created_at`, `updated_at`

#### 4.2.3 `preflight_runs` (future canonical)
Fogalmi szerep:
- file-level prefilter futas truth (ingest -> preflight acceptance reteg),
  kulon a geometry revision statusztol.

Javasolt oszlopirany:
- `id` (PK uuid)
- `project_id` (FK -> `app.projects.id`)
- `source_file_object_id` (FK -> `app.file_objects.id`)
- `rules_profile_version_id` (FK -> `dxf_rules_profile_versions.id`)
- `run_seq` (file-on beluli futas-szam)
- `run_status` (docs-level lifecycle kod; T4 lifecycle-hez igazodva)
- `acceptance_outcome` (`accepted` / `rejected` / `review_required` jelleg)
- `engine_version`, `normalizer_version`
- `source_hash_sha256`, `normalized_hash_sha256`
- `started_at`, `finished_at`, `created_at`

#### 4.2.4 `preflight_diagnostics` (future canonical)
Fogalmi szerep:
- run-szintu issue/diagnostic truth; nem geometry validator report replacement.

Javasolt oszlopirany:
- `id` (PK uuid)
- `preflight_run_id` (FK -> `preflight_runs.id`)
- `diagnostic_seq` (run-on beluli sorrend)
- `severity`, `code`, `message`, `path`
- `details_jsonb`
- `created_at`

#### 4.2.5 `preflight_artifacts` (future canonical)
Fogalmi szerep:
- prefilter futas altal eloallitott artifact metadata (pl. normalized dxf,
  diagnostics export), kulon a generic file ingest truth-tol.

Javasolt oszlopirany:
- `id` (PK uuid)
- `preflight_run_id` (FK -> `preflight_runs.id`)
- `artifact_seq` (run-on beluli sorrend)
- `file_object_id` (FK -> `app.file_objects.id`, ha object tarolt)
- `artifact_kind`
- `artifact_hash_sha256`
- `metadata_jsonb`
- `created_at`

#### 4.2.6 `preflight_review_decisions` (future extension candidate)
Fogalmi szerep:
- explicit prefilter gate review dontesek tarolasa,
- kulon tartva a meglevo `geometry_review_actions` action-log tablatol.

Javasolt oszlopirany:
- `id` (PK uuid)
- `preflight_run_id` (FK -> `preflight_runs.id`)
- `decision_seq` (run-on beluli sorrend)
- `decision_kind` (`approve` / `reject` / `request_changes`)
- `actor_user_id` (FK -> `app.profiles.id`)
- `note`, `metadata_jsonb`
- `created_at`

## 5. Ownership, FK, uniqueness es indexing elvek

### 5.1 Ownership
- Profile/version domain: owner-szintu izolacio (`owner_user_id`) kotelezo.
- Version owner mindig egyezzen a profile ownerrel (kompozit FK elv).
- Preflight run ownership project/file lineage-bol kovetkezzen,
  ne kulonallo owner mezo-bol.

### 5.2 FK / lineage konzisztencia
- `preflight_runs.project_id` + `source_file_object_id` konzisztens legyen a
  `file_objects` projekthez kotott rekordjaval.
- `preflight_runs` csak valos file-object lineage-re epulhet.
- `preflight_artifacts.file_object_id` opcionális, de ha kitoltott, az artifact
  ugyanahhoz a project lineage-hez tartozzon, mint a run.

### 5.3 Uniqueness
- Profile tabla: owner alatt egyedi `profile_code`.
- Version tabla: profile alatt egyedi `version_no`.
- Run tabla: `(source_file_object_id, run_seq)` egyedi.
- Diagnostics: `(preflight_run_id, diagnostic_seq)` egyedi.
- Artifacts: `(preflight_run_id, artifact_seq)` egyedi.
- Review decision: `(preflight_run_id, decision_seq)` egyedi.

### 5.4 Indexing irany (minimum)
- Profile tablakh: owner + lookup code index.
- Version tablakh: profile FK + owner index.
- Run tabla: source file FK, project FK, status/outcome index.
- Diagnostics/artifacts/review: run FK + seq index.

## 6. Miert kell kulon preflight truth a geometry truth mellett
- A `geometry_revisions` a canonical geometry allapot truth-ja az import utan.
- A prefilter futas a file ingest es acceptance gate retegben tortenik.
- Egy preflight runnak lehet olyan kimenete (review-required/rejected), amely
  nem hoz letre uj geometry revision truthot.
- Ezert a preflight run/domain nem irhato ra 1:1-ben a
  `geometry_revisions`/`geometry_validation_reports` tablakhra.

## 7. Migration slicing terv (logikai szeletek)

### Slice A - Rules profile/version truth
- `dxf_rules_profiles`
- `dxf_rules_profile_versions`
- owner + version konzisztencia es alap indexek

### Slice B - Preflight run + diagnostics truth
- `preflight_runs`
- `preflight_diagnostics`
- file lineage + run sequencia + status/outcome indexek

### Slice C - Artifact and review decision truth
- `preflight_artifacts`
- opcionais `preflight_review_decisions`
- run-hoz kotott artifact/review audit reteg

### Slice D - Rollout/compat bridge (kesobbi)
- adatvisszafele kompatibilitas a meglvo upload/import flow-val
- API es orchestration bekotes (T6 es kesobbi taskokban)
- potential migration backfill strategy, ha kell

## 8. Relation mas taskokhoz
- Lifecycle allapotmodell: mar T4 dokumentumban rogzitve.
- API payload/endpoint contract: T6 feladat hataskore.
- UI settings/review flow: kesobbi E4 scope.
- Ez a task csak persistence truth + migration slicing freeze.

## 9. Explicit anti-scope lista
- Nincs konkret SQL migration vagy DDL.
- Nincs uj enum bevezetes.
- Nincs RLS policy tervezes reszletesen.
- Nincs route/service payload freeze.
- Nincs UI tabla/modalkoncepcio fagyasztas.
- Nincs queue/worker retry modell persistence truthkent veglegesitve.

## 10. Later extension jeloltek (nem V1 minimum)
- `preflight_rule_waivers` jellegu exception domain.
- projekt-szintu profile selection cache/pinning.
- cross-run aggregate diagnostics summary/materialized projection.
- advanced artifact lineage snapshot (diff/patch based).

## 11. Bizonyitek forrasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/routes/files.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
