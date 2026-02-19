# Phase 4 Gateway Rate Limit — Döntésdokumentum

**Státusz:** LEZÁRVA
**Vonatkozó blokkok:** P4.1/a, P4.1/c
**Döntés alapja:** P4.0/a keretdöntés (phase4_p0_decision_freeze_and_dod_rebaseline)

---

## 1. Döntés összefoglalója

A gateway (Supabase/reverse proxy) szintű rate limit konfiguráció **infra-oldali felelősség**, a P4.0/a keretdöntés alapján:

- **Gateway = általános védőháló** (repo-n kívül): globális IP-alapú és route-csoportos sebességkorlát, Supabase dashboard vagy reverse proxy szinten konfigurálva.
- **App = kritikus mutációk védelme** (repo-ban implementálva): a legfontosabb write-műveletek védve `api/rate_limit.py` helperrel.

Ez a szétválasztás tudatos architektúrális döntés: a gateway-konfiguráció projekt-specifikus infrastruktúra-beállítás, amelynek lifecycle-ja elválik a repo kódbázisától.

---

## 2. App-oldali implementáció bizonyítékai

Az app-oldali 429 + `Retry-After` válasz implementált és bizonyított:

| Fájl | Szerepe |
|---|---|
| `api/rate_limit.py` | 429 + `Retry-After` helper modul |
| `api/routes/runs.py` | `POST /projects/{id}/runs` — kritikus mutáció védve |
| `api/routes/files.py` | `POST /projects/{id}/files/upload-url` — feltöltési URL limit |
| `codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md` | DONE report — P4.1/b, P4.1/d lezárva |

Az app-oldali implementáció lefedi a `POST /runs` és `POST /files/upload-url` végpontokat, amelyek a legkritikusabb write-műveletek a rendszerben.

---

## 3. Gateway aktiválás feltételei és lépései

A gateway-oldali rate limit konfiguráció az alábbi feltételek teljesülésekor aktiválandó:

### Mikor
- Éles Supabase projekt beállításakor, **production deploy előtt**.
- Nem szükséges fejlesztési/staging környezetben (ahol a forgalom korlátozott).

### Hol
- **Supabase Dashboard** → API Settings → Rate Limiting
- Vagy: saját reverse proxy (nginx, Caddy, Cloudflare Workers) route-szintű policy

### Mit konfigurálni
Ajánlott limit értékek (szükség szerint igazítandó):

| Route-csoport | Limit | Indoklás |
|---|---|---|
| Általános (`/v1/*`) | 200 req/perc/IP | Alap védelem bot/scanner ellen |
| Projektek (`/v1/projects/*`) | 100 req/perc/user | Read-heavy, de korlátozott |
| Futások (`/v1/projects/*/runs`) | 10 req/perc/user | Write-heavy, kvóta-érzékeny |
| Fájlok (`/v1/projects/*/files/*`) | 20 req/perc/user | Upload rate korlát |

### Ki felel érte
- **Infra/DevOps felelős** — nem automatizált a repóból.
- A Supabase project owner vagy az üzemeltetési team végzi el production deploy előtt.
- A repo-ból nem konfigurálható, mivel a Supabase gateway nem IaC-vezérelt ebben a projektben.

---

## 4. Következtetés — DoD checkpoint lezárása

A **P4.1/a** és **P4.1/c** DoD checkpointok lezárhatók az alábbi indokkal:

- **P4.1/a** (Gateway oldali általános rate limit konfiguráció): dokumentált döntéssel lezárva. A gateway konfiguráció infra-oldali felelősség; a feltételek és lépések rögzítve ebben a dokumentumban.
- **P4.1/c** (Egységes 429 + `Retry-After` + konzisztens hibakód): az app-oldali implementáció (`api/rate_limit.py`) DONE és bizonyított. A gateway-oldal egységes 429 választ ad alapértelmezetten, ha a Supabase rate limit konfigurálva lesz.

A **Phase 4 DoD checkpoint** — _"Gateway + app split rate limit aktív, konzisztens 429 + Retry-After válasszal"_ — dokumentált döntéssel lezárható: az app-oldal implementált, a gateway-oldal infra-felelősség, amelynek aktiválási feltételei rögzítve vannak.
