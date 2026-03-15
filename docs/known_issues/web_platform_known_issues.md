# docs/known_issues/web_platform_known_issues.md

> Elo dokumentum. Az auditok/futasok altal feltart, de meg nem vegleg lezart
> web platform problemak nyilvantartasa.
>
> Allapotok: OPEN | IN_PROGRESS (task slug) | RESOLVED (task slug, datum)
> Azonosito-konvencio: KI-NNN (Known Issue, sorszam)

---

## P1 - Magas prioritas

### KI-001 Hosted Supabase owner-limit miatt storage.objects policy DDL megbukik
**Allapot:** IN_PROGRESS (`h0_e6_t2_rls_policy_alapok_storage_policy_rollout_split`)  
**Forras:** Migration apply hiba, 2026-03-15  
**Terulet:** `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`, `storage.objects`

Hosted Supabase projektben a migracio futtato role (`postgres`) nem tulajdonosa
a `storage.objects` tablanak (`owner = supabase_storage_admin`), emiatt a
kovetkezo DDL-ek megbuknak:
- `alter table storage.objects enable row level security`
- `drop/create policy ... on storage.objects`

Tipikus hiba:
`ERROR: must be owner of table objects`

Kovetkezmeny:
- a H0 app-domain (`app.*`) RLS rollout nem szabad, hogy ezen elakadjon.
- a storage policy rolloutot kulon infra lepeskent kell kezelni.

Atmeneti workaround:
- backend/service-role alapu storage hozzaferes (signed URL + service path),
  user-facing storage.objects policy nelkul.

Javasolt vegleges DoD:
- storage policy rollout kulon, owner-kompatibilis modon vegrehajthato;
- legalabb a `source-files` bucketre definialt owner/project-bound policy
  tenylegesen deployolt;
- rollout utan regresszioellenorzes: upload/list/download authz smoke.

---
