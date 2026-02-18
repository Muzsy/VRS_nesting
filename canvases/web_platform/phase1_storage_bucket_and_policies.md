# canvases/web_platform/phase1_storage_bucket_and_policies.md

# Phase 1 storage bucket and policy provisioning

## Funkcio
A feladat a Phase 1 P1.4 pontok teljesitese: private `vrs-nesting` bucket
beallitasa, storage key mintak rogzitese policy szinten, es owner-scope
auth szabalyok alkalmazasa upload/download/delete muveletekre.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs-nesting` private bucket idempotens letrehozasa SQL-bol;
  - `storage.objects` policy-k letrehozasa a ket engedett key strukturara:
    - `users/{user_id}/projects/{project_id}/files/{file_id}/{filename}`
    - `runs/{run_id}/artifacts/...`
  - owner-scope ellenorzes (`auth.uid`) user/project/run alapon;
  - bucket+policy smoke check script es master checklist frissites.
- Nincs benne:
  - frontend upload UI;
  - worker artifact write flow teljes implementacioja (Phase 2);
  - storage lifecycle housekeeping (Phase 4).

### Erintett fajlok
- `canvases/web_platform/phase1_storage_bucket_and_policies.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_storage_bucket_and_policies.yaml`
- `codex/codex_checklist/web_platform/phase1_storage_bucket_and_policies.md`
- `codex/reports/web_platform/phase1_storage_bucket_and_policies.md`
- `api/sql/phase1_storage_bucket_policies.sql`
- `scripts/smoke_phase1_storage_bucket_policies.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] A `vrs-nesting` bucket letezik es private.
- [ ] A P1.4-ben elvart ket storage key struktura policy szinten enforce-olt.
- [ ] Upload/download/delete policy csak a sajat eroforrasokra engedelyezett.
- [ ] Van smoke script a bucket + policy allapot ellenorzesere.
- [ ] A master checklist P1.4 pontok frissitettek.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase1_storage_bucket_and_policies.md` PASS.

### Kockazat + rollback
- Kockazat: storage policy tul szigoru/tul laza lehet.
- Mitigacio: idempotens SQL, policy nevek stabilak, smoke allapotellenorzes.
- Rollback: uj SQL-lepesben policy drop + ujradef; bucket torles kulon
  kezelt, ha mar van benne adat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase1_storage_bucket_and_policies.md`
- Feladat-specifikus:
  - `python3 scripts/smoke_phase1_storage_bucket_policies.py`

## Kapcsolodasok
- `api/sql/phase1_schema.sql`
- `api/sql/phase1_rls.sql`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
