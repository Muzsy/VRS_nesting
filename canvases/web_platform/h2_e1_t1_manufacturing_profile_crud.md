# H2-E1-T1 Manufacturing profile CRUD (retroaktiv scope-rendezes)

## Funkcio
Ez a retroaktiv task rendezi a H2-E1-T1 es H2-E1-T2 kozti scope-elcsuszast.
A cel, hogy auditálhatoan kimondjuk: a manufacturing profile domain schema-alapja mar
leszallitva lett a `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
migracioban, mig a projekt-szintu selection API flow a H2-E1-T2 scope-ban marad.

Ez a task nem uj backend feature-bevezetes, hanem task-tree konzisztencia-helyreallitas.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - H2-E1-T1 artefaktlanc (canvas/yaml/run/checklist/report) retroaktiv letrehozasa;
  - dokumentalt bizonyitas, hogy a manufacturing profile es version schema/policy alap
    mar bekerult;
  - H2-E1-T2 report korrekcio, hogy a scope-szeparacio egyertelmu legyen.
- Nincs benne:
  - uj SQL migration;
  - uj manufacturing profile CRUD route/service;
  - selection endpoint attervezese;
  - snapshot/manufacturing plan/postprocess implementacio.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H2-E1-T1/H2-E1-T2 sorrend es fuggoseg.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - a mar leszallitott manufacturing profile/version es selection schema/policy.
- `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`
  - T2 report, ahol a scope driftet korrigalni kell.

### Konkret elvarasok
1. Keszuljon kulon H2-E1-T1 artefaktlanc.
2. A T1 report evidence-alapon mapelje, hogy mely migration-reszek T1-domain scope-osak.
3. A T1 report explicit nevezze meg, hogy dedikalt manufacturing profile CRUD API meg nem
   keszult ebben a futasban (korlat/follow-up).
4. A T2 report jelezze a scope-korrekciot: T1 = domain schema alap, T2 = project selection API.

### DoD
- [ ] Letrejott a teljes H2-E1-T1 artefaktlanc.
- [ ] A T1 report evidence-alapon hivatkozza a leszallitott schema/policy reszeket.
- [ ] A T1 report explicit dokumentalja a nyitott CRUD API follow-upot.
- [ ] A T2 report scope-korrekcioja dokumentalt.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t1_manufacturing_profile_crud.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a T1/T2 hatar tovabbra is ketertelmu marad;
  - a report allitasok nincsenek osszhangban a kodallapottal.
- Mitigacio:
  - explicit, line-level evidence a migrationrol;
  - T2 report korrekcio T1 referenciaval.
- Rollback:
  - tisztan dokumentacios commit, egyben visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t1_manufacturing_profile_crud.md`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`
