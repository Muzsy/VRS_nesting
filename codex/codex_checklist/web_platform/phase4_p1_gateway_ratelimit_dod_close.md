# Checklist — phase4_p1_gateway_ratelimit_dod_close

## DoD pontok

- [x] `docs/qa/phase4_gateway_ratelimit_decision.md` létrejött és tartalmazza:
  - [x] a gateway/app felelősségmegosztás döntését (P4.0/a alapján)
  - [x] az app-oldali 429 + `Retry-After` implementáció hivatkozásait
  - [x] a gateway aktiválás feltételeit és lépéseit (mikor, hogyan, ki felel érte)
- [x] Master checklist P4.1/a és P4.1/c pontjai `[x]` státuszba kerülnek
- [x] Phase 4 DoD checkpoint `Gateway + app split rate limit aktív` lezárva
- [x] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p1_gateway_ratelimit_dod_close.md` PASS

## Érintett fájlok

- `docs/qa/phase4_gateway_ratelimit_decision.md` — új fájl, döntésdokumentum
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md` — P4.1/a, P4.1/c, DoD checkpoint [x]-re állítva
- `codex/codex_checklist/web_platform/phase4_p1_gateway_ratelimit_dod_close.md` — ez a fájl
- `codex/reports/web_platform/phase4_p1_gateway_ratelimit_dod_close.md` — report
