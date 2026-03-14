PASS

## 1) Meta
- Task slug: `h0_e6_t1_storage_bucket_strategia_es_path_policy`
- Kapcsolodo canvas: `canvases/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml`
- Futas datuma: `2026-03-14`
- Branch / commit: `main @ d03b8df (dirty working tree)`
- Fokusz terulet: `Docs`

## 2) Scope

### 2.1 Cel
- Kesz legyen a H0 storage source-of-truth bucket/path policy dokumentum.
- Rogzitve legyen a kanonikus H0 bucket inventory es entitas -> bucket mapping.
- Rogzitve legyenek a bucketenkenti path naming mintak es az immutabilitas/overwrite alapelvek.
- Minimal docs szinkron tortenjen a fo architecture es roadmap dokumentumban.

### 2.2 Nem-cel
- Uj Supabase migracio letrehozasa.
- Storage provisioning script vagy seed script letrehozasa.
- RLS/storage policy SQL implementacio.
- Upload/export API vagy worker implementacio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml`
- `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- `codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`

### 3.2 Miert valtoztak?
- A H0-E5-T3 utan kellett a storage bucket/path szerzodes explicit source-of-truth lezarasa.
- A szinkron celja a storage truth (file_objects/run_artifacts) es a DB-truth derivative reteg (`geometry_derivatives`) hataranak tisztazasa.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) Vegleges storage policy inventory (H0-E6-T1)

### 5.1 Kanonikus bucket inventory
- `source-files`
- `geometry-artifacts`
- `run-artifacts`

### 5.2 Entitas -> bucket mapping
- `app.file_objects` -> `source-files`
- `app.run_artifacts` -> `run-artifacts`
- `geometry-artifacts` -> reserved/canonical bucket jovobeli file-backed geometry artifactokhoz
- `app.geometry_derivatives` -> DB-ben tarolt derivalt truth (nem storage bucket/path truth)

### 5.3 Bucketenkenti path mintak
- `source-files`: `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`
- `geometry-artifacts`: `projects/{project_id}/geometry/{geometry_revision_id}/{artifact_kind}/{content_hash}.{ext}`
- `run-artifacts`: `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`

### 5.4 Immutabilitas / overwrite elvek
- Generalt artifact ne overwrite-olodjon in-place, ha hash/verzio adheto.
- Uj artifact uj pathra keruljon.
- Source file identity ne pusztan az eredeti fajlnev legyen.

### 5.5 Miert nem storage-truth a `geometry_derivatives`
- A `geometry_derivatives` rekordok DB-ben tarolt, ujraeloallithato derivalt reteget kepviselnek.
- A storage bucket/path policy a file-backed artifactokra vonatkozik, nem a canonical DB-derivative truth-ra.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md` fajl. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:1` | A dedikalt storage source-of-truth dokumentum letrejott. | Kezi ellenorzes |
| A dokumentum rogzitese a kanonikus H0 bucket inventoryt. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:14` | A 3 bucketes inventory explicit rogzitve van. | Kezi ellenorzes |
| A dokumentum rogzitese az entitas -> bucket mappinget. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:27` | `app.file_objects` es `app.run_artifacts` mapping explicit. | Kezi ellenorzes |
| A dokumentum rogzitese legalabb egy kanonikus path mintat minden H0 buckethez. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:51`; `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:60`; `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:69` | Mindharom buckethez kulon kanonikus path minta szerepel. | Kezi ellenorzes |
| A dokumentum explicit kimondja, hogy az `app.geometry_derivatives` nem storage-truth. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:39` | A DB-truth vs storage-truth hatar explicit mondattal rogzitett. | Kezi ellenorzes |
| A dokumentum rogzitese az immutabilitas / overwrite alapelveket. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:77` | Kulon szakasz rogzit in-place overwrite tiltast es hash/verzio szemantikat. | Kezi ellenorzes |
| A dokumentum elokesziti a H0-E6-T2 RLS/storage policy taskot, de nem implemental policyt. | PASS | `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:91`; `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:12` | Kulon kezeli a kovetkezo taskot es explicit docs-only scope-ot tart. | Kezi ellenorzes |
| A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md` es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md` minimalisan szinkronba kerul a konkret H0-E6-T1 irannyal. | PASS | `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:1183`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:903` | Mindket doksiban megjelent a T1 bucket inventory + mapping + hatar definicio. | Kezi ellenorzes |
| A task nem hoz letre migraciot. | PASS | `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:23`; `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:45`; `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml:1` | A task scope explicit tiltja, es az outputs listaban nincs migracio. | `./scripts/verify.sh --report ...` |
| A task nem hoz letre storage provisioning scriptet. | PASS | `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:24`; `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:46`; `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:12` | Provisioning script kulon tiltott, es a docs-only scope ezt rogzitette. | `./scripts/verify.sh --report ...` |
| A task nem hoz letre RLS policyt. | PASS | `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:25`; `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md:47`; `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md:12` | RLS policy implementation out-of-scope maradt. | `./scripts/verify.sh --report ...` |
| A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott. | PASS | `codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md:76` | A matrix 1:1-ben lefedi a canvas DoD pontokat. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md` PASS. | PASS | `codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.verify.log:1` | A kotelezo gate PASS loggal igazolt. | `./scripts/verify.sh --report ...` |

## 7) Advisory notes
- A bucket/path naming policy most docs szintu source-of-truth, enforcement nelkul; a policy SQL/Storage ACL implementacio kulon task marad.
- A `geometry-artifacts` bucket H0-ban reserved, a konkret file-backed geometry artifact bevezeteshez kesobbi implementation task szukseges.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-15T00:04:27+01:00 → 2026-03-15T00:08:00+01:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.verify.log`
- git: `main@d03b8df`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../dxf_nesting_platform_architektura_es_supabase_schema.md    | 10 ++++++++++
 docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md | 10 ++++++++++
 2 files changed, 20 insertions(+)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md
?? codex/codex_checklist/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml
?? codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/
?? codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md
?? codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.verify.log
?? docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
```

<!-- AUTO_VERIFY_END -->
