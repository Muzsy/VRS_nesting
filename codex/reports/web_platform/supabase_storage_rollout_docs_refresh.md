# Supabase storage rollout docs refresh

## Modositott fajlok
- `docs/known_issues/web_platform_known_issues.md`
- `docs/web_platform/architecture/h0_security_rls_alapok.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md`

## Javitasok roviden
- KI-001 allapotat `RESOLVED`-ra allitottuk, es egyertelmusitettuk, hogy a hosted owner-limit valos, a migracio split pedig tovabbra is indokolt.
- Minden erintett dokumentumban kulonvalasztottuk a kovetkezoket:
  - source-of-truth szabalylogika,
  - repo migracios allapot,
  - hosted Supabase tenyleges rollout allapot.
- Eltavolitottuk/atirtuk azokat a megfogalmazasokat, amelyek azt sugalltak, hogy a `storage.objects` policy rollout SQL migraciobol teljesen lefutott.
- Rogzitettuk, hogy a 3 kanonikus bucket (`source-files`, `geometry-artifacts`, `run-artifacts`) hosted oldalon letrehozott es `private`.
- Rogzitettuk, hogy a H0 minimal storage policy matrix hosted oldalon funkcionalisan aktiv, de manualis Dashboard/Studio provisioninggel, nem migracios storage DDL-lel.
- Rogzitettuk, hogy policynev-egyezes helyett a funkcionalis szabaly-egyezes a mervado (Supabase nevhossz-limit caveat).

## Vegso allapotleiras (1 mondat)
A H0 security/storage minimum celallapot funkcionalisan teljesult a hosted Supabase projekten (`app.*` RLS migraciosan aktiv, bucketek private-k, `storage.objects` minimal policyk manualisan provisionaltak), mikozben a repo migracio szandekosan splitelt maradt a hosted owner-limit miatt.
