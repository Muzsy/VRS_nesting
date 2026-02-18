PASS

## 1) Meta
- Task slug: `phase1_storage_bucket_and_policies`
- Kapcsolodo canvas: `canvases/web_platform/phase1_storage_bucket_and_policies.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_phase1_storage_bucket_and_policies.yaml`
- Fokusz terulet: `Supabase Storage | Bucket | Policy`

## 2) Scope

### 2.1 Cel
- Private `vrs-nesting` bucket beallitasa.
- P1.4 key-structura policy enforce.
- Owner-scope upload/download/delete szabalyok.

### 2.2 Nem-cel
- Frontend upload UI.
- Worker run artifact pipeline teljes implementacioja.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/phase1_storage_bucket_and_policies.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_storage_bucket_and_policies.yaml`
- `codex/codex_checklist/web_platform/phase1_storage_bucket_and_policies.md`
- `codex/reports/web_platform/phase1_storage_bucket_and_policies.md`
- `api/sql/phase1_storage_bucket_policies.sql`
- `scripts/smoke_phase1_storage_bucket_policies.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### 3.2 Miert valtoztak?
- A P1.4 bucket+storage policy blokkhoz kellett idempotens SQL, smoke check, es checkpoint sync.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/phase1_storage_bucket_and_policies.md` -> PASS

### 4.2 Opcionals
- Management API SQL futtatas (`POST /v1/projects/{project}/database/query`) a `public.exec_storage_admin_ddl(...)` wrapperrel, statementenkent.
- `python3 scripts/smoke_phase1_storage_bucket_policies.py` -> PASS.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | --- | --- | --- | --- |
| `vrs-nesting` private bucket letezik | PASS | `api/sql/phase1_storage_bucket_policies.sql:3`, `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md:50` | A bucket idempotens insert/update SQL futott, private allapottal (`public=false`, 50MB limit). | `python3 scripts/smoke_phase1_storage_bucket_policies.py` |
| Key struktura policy enforce | PASS | `api/sql/phase1_storage_bucket_policies.sql:26`, `api/sql/phase1_storage_bucket_policies.sql:40` | A `users/.../projects/.../files/...` es `runs/.../artifacts/...` strukturak policy szinten kikotve. | `python3 scripts/smoke_phase1_storage_bucket_policies.py` |
| Owner-scope upload/download/delete | PASS | `api/sql/phase1_storage_bucket_policies.sql:19`, `api/sql/phase1_storage_bucket_policies.sql:55`, `api/sql/phase1_storage_bucket_policies.sql:91`, `api/sql/phase1_storage_bucket_policies.sql:159` | Mind a 4 policy (SELECT/INSERT/UPDATE/DELETE) owner-scope feltetelekkel aktiv. | `python3 scripts/smoke_phase1_storage_bucket_policies.py` |
| Bucket/policy smoke script kesz | PASS | `scripts/smoke_phase1_storage_bucket_policies.py:99` | A smoke script bucket + policy allapotot es policy tartalmi tokeneket ellenoriz. | `python3 scripts/smoke_phase1_storage_bucket_policies.py` |
| Master checklist P1.4 frissitve | PASS | `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md:50`, `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md:51`, `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md:52`, `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md:53` | A P1.4/a-b-c-d checkpointok be vannak pipalva. | Checklist diff |
| Verify gate PASS | PASS | `codex/reports/web_platform/phase1_storage_bucket_and_policies.verify.log` | A kotelezo wrapperes repo gate PASS eredmennyel futott. | `./scripts/verify.sh --report codex/reports/web_platform/phase1_storage_bucket_and_policies.md` |

## 8) Advisory notes
- A `storage.objects` DDL kozvetlenul (`alter table ...`) tovabbra is owner-jogot igenyel; a policy apply a `public.exec_storage_admin_ddl` wrapperen keresztul lett vegrehajtva.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-18T20:49:05+01:00 → 2026-02-18T20:51:16+01:00 (131s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/phase1_storage_bucket_and_policies.verify.log`
- git: `fix/repo-gate-sparrow-fallback@27f5af2`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .gitignore                 | 5 +++++
 docs/error_code_catalog.md | 2 ++
 2 files changed, 7 insertions(+)
```

**git status --porcelain (preview)**

```text
 M .gitignore
 M docs/error_code_catalog.md
?? api/
?? canvases/web_platform/
?? codex/codex_checklist/web_platform/
?? codex/goals/canvases/web_platform/
?? codex/reports/web_platform/
?? scripts/smoke_phase1_storage_bucket_policies.py
?? scripts/smoke_phase1_supabase_schema_state.py
?? scripts/smoke_sparrow_determinism.py
```

<!-- AUTO_VERIFY_END -->
