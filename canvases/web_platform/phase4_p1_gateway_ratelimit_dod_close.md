# canvases/web_platform/phase4_p1_gateway_ratelimit_dod_close.md

# Phase 4 P1/c Gateway rate limit — döntésdokumentáció + DoD lezárás

## 🎯 Funkció

A P4.1 blokk app-oldali védelme (P4.1/b, P4.1/d) már DONE. Az egyetlen nyitott pont:

- **P4.1/a** — Gateway oldali általános rate limit konfiguráció route-csoportokra  
- **P4.1/c** — Egységes 429 + `Retry-After` + konzisztens hibakód biztosítás **gateway ÉS app** oldalon

A gateway Supabase/infra szinten él (repo-n kívül), ezért a feladat **nem implementáció**, hanem:
1. A gateway rate limit döntés és állapot formális dokumentálása (`docs/` alatt)
2. A master checklist P4.1/a és P4.1/c pontjainak igazolt lezárása
3. Report + checklist + verify lezárása

## 🧠 Fejlesztési részletek

### Scope
- **Benne van:**
  - `docs/qa/phase4_gateway_ratelimit_decision.md` létrehozása: dokumentálja a döntést (gateway=infra felelősség, app=repo felelősség), az app-oldali 429+Retry-After implementáció bizonyítékát, és azt, hogy a gateway konfiguráció mikor és hogyan aktiválandó
  - Master checklist P4.1/a és P4.1/c pontjainak frissítése: `[x]` státuszba kerülnek a döntésdokumentum alapján
  - Codex checklist + report + verify futtatás

- **Nincs benne:**
  - Tényleges Supabase gateway konfiguráció (infra, repo-n kívül)
  - Kódbeli változtatás (`api/` vagy `worker/` alatt)

### Döntés igazolása

Az app-oldali 429 + `Retry-After` már implementált és bizonyított:
- `api/rate_limit.py` — helper modul
- `api/routes/runs.py`, `api/routes/files.py` — kritikus mutációk védve
- `codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md` — DONE report

A gateway szintű konfiguráció (Supabase rate limiting / reverse proxy policy) **infra-oldali döntés**, amelyet a P4.0 keretdöntés már rögzített: `gateway általános védőháló, repo-n kívül`. A P4.1/a checkpoint ezért dokumentált döntéssel zárható, nem kódbeli implementációval.

### Érintett fájlok
- `canvases/web_platform/phase4_p1_gateway_ratelimit_dod_close.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p1_gateway_ratelimit_dod_close.yaml`
- `codex/codex_checklist/web_platform/phase4_p1_gateway_ratelimit_dod_close.md`
- `codex/reports/web_platform/phase4_p1_gateway_ratelimit_dod_close.md`
- `docs/qa/phase4_gateway_ratelimit_decision.md` *(új)*
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] `docs/qa/phase4_gateway_ratelimit_decision.md` létrejött és tartalmazza:
  - a gateway/app felelősségmegosztás döntését (P4.0/a alapján)
  - az app-oldali 429 + `Retry-After` implementáció hivatkozásait
  - a gateway aktiválás feltételeit és lépéseit (mikor, hogyan, ki felel érte)
- [ ] Master checklist P4.1/a és P4.1/c pontjai `[x]` státuszba kerülnek
- [ ] Phase 4 DoD checkpoint `Gateway + app split rate limit aktív` lezárva
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p1_gateway_ratelimit_dod_close.md` PASS

### Kockázat + rollback
- Kockázat: a P4.1/a lezárása döntésdokumentummal félreérthető lehet (nincs tényleges gateway konfig).
  - Mitigáció: a doc egyértelműen rögzíti, hogy a gateway konfig infra-oldali felelősség, és megnevezi az aktiválás feltételeit.
- Rollback: csak dokumentációs fájlok érintettek, visszaállítás kockázatmentes.

## 🧪 Tesztállapot

- Kötelező gate: `./scripts/verify.sh --report codex/reports/web_platform/phase4_p1_gateway_ratelimit_dod_close.md`
- Feladat-specifikus ellenőrzés: a `docs/qa/phase4_gateway_ratelimit_decision.md` fájl létezik és nem üres

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `docs/codex/overview.md`
- `codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md` — előző DONE report
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md` — P4.1 blokk
- `docs/qa/phase4_security_hardening_notes.md` — meglévő security notes