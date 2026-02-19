# canvases/web_platform/phase2_dod_acceptance_checkpoints.md

# Phase 2 DoD acceptance checkpoints

## Funkcio
A feladat celja a Phase 2 DoD checkpointok tenyleges acceptance verifikacioja es
pipalasa. A hangsuly nem uj feature fejlesztesen, hanem a teljes Phase 2
(Worker + run pipeline) vegponttol-vegpontig bizonyitasan van.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - dedikalt Phase 2 DoD smoke script keszitese;
  - Docker image build + konteneres worker futas ellenorzese;
  - runs API -> queue -> worker -> DB/storage/log acceptance lepesek;
  - FAILED run es rerun determinizmus ellenorzes;
  - master checklist Phase 2 DoD checkpointok pipalasa PASS bizonyitek utan.
- Nincs benne:
  - Phase 3 implementacio;
  - uj business endpoint (viewer-data/bundle) fejlesztes.

### Erintett fajlok
- `canvases/web_platform/phase2_dod_acceptance_checkpoints.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_dod_acceptance_checkpoints.yaml`
- `codex/codex_checklist/web_platform/phase2_dod_acceptance_checkpoints.md`
- `codex/reports/web_platform/phase2_dod_acceptance_checkpoints.md`
- `scripts/smoke_phase2_dod_acceptance.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
- `worker/Dockerfile`
- `worker/main.py`
- `requirements.in`
- `requirements.txt`

### DoD
- [ ] A dedikalt Phase 2 DoD smoke script PASS.
- [ ] A master checklist `Phase 2 DoD checkpointok` blokkja teljesen `[x]` allapot.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_dod_acceptance_checkpoints.md` PASS.

### Kockazat + rollback
- Kockazat: kulso (Supabase + Docker) infrastruktura idoszakos hiba miatt flaky acceptance.
- Mitigacio: explicit ellenorzo hibalepesek + tisztitas + egyertelmu hibaok a smoke scriptben.
- Rollback: uj smoke/task artefaktok es checklist pipa visszavonhato egy commitban.
