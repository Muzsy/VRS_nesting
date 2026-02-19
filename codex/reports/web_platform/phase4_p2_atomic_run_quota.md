DONE

## 1) Meta
- Task slug: `phase4_p2_atomic_run_quota`
- Kapcsolodo canvas: `canvases/web_platform/phase4_p2_atomic_run_quota.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_phase4_p2_atomic_run_quota.yaml`
- Fokusz terulet: `Phase 4 P2 atomic run quota`

## 2) Scope

### 2.1 Cel
- Havi kvota atomikus check+increment es a `POST /runs` tranzakcios enqueue vedelme.

### 2.2 Nem-cel
- Gateway rate limit, E2E/load/security egyeb Phase 4 blokkok.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `api/sql/phase4_run_quota_atomic.sql`
- `api/supabase_client.py`
- `api/routes/runs.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
- `canvases/web_platform/phase4_p2_atomic_run_quota.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p2_atomic_run_quota.yaml`
- `codex/codex_checklist/web_platform/phase4_p2_atomic_run_quota.md`
- `codex/reports/web_platform/phase4_p2_atomic_run_quota.md`

### 3.2 Miert valtoztak?
- A soft quota tulfutasok elkerulesere lockolt, DB-centrikus check+increment kerult bevezetesre.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/phase4_p2_atomic_run_quota.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat |
| --- | --- | --- | --- |
| `quota_runs_per_month` default 50/honap | PASS | `api/sql/phase1_schema.sql` | A `users` tabla default kvotaja 50, ez valtozatlan. |
| Atomic kvota check+increment lockkal | PASS | `api/sql/phase4_run_quota_atomic.sql` | `enqueue_run_with_quota` function `FOR UPDATE` lockokkal vegzi a havi kvota checket es noveli a szamlalot. |
| `POST /runs` csak sikeres quota commit utan enqueue-ol | PASS | `api/routes/runs.py`, `api/sql/phase4_run_quota_atomic.sql` | A route az RPC funkciot hivja, amely egy tranzakcioban noveli a kvotat es letrehozza a `runs` + `run_queue` rekordot. |
| Kvota tullepes 429 + userbarat hiba | PASS | `api/routes/runs.py` | `quota_exceeded` eseten a route `429`-et ad vissza `monthly_run_quota_exceeded` kodu hibatesttel. |
| Verify gate PASS | PASS | `codex/reports/web_platform/phase4_p2_atomic_run_quota.verify.log` | A kotelezo wrapper futas PASS. |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-19T20:01:39+01:00 → 2026-02-19T20:03:46+01:00 (127s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/phase4_p2_atomic_run_quota.verify.log`
- git: `main@741838b`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 api/config.py                                      | 28 ++++++++
 api/routes/files.py                                | 15 +++++
 api/routes/runs.py                                 | 77 +++++++++++++++++++++-
 api/supabase_client.py                             | 14 ++++
 .../implementacios_terv_master_checklist.md        | 18 ++---
 5 files changed, 141 insertions(+), 11 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/config.py
 M api/routes/files.py
 M api/routes/runs.py
 M api/supabase_client.py
 M codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md
?? api/rate_limit.py
?? api/sql/phase4_run_quota_atomic.sql
?? canvases/web_platform/phase4_p1_app_rate_limit_minimal.md
?? canvases/web_platform/phase4_p2_atomic_run_quota.md
?? codex/codex_checklist/web_platform/phase4_p1_app_rate_limit_minimal.md
?? codex/codex_checklist/web_platform/phase4_p2_atomic_run_quota.md
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p1_app_rate_limit_minimal.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p2_atomic_run_quota.yaml
?? codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md
?? codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.verify.log
?? codex/reports/web_platform/phase4_p2_atomic_run_quota.md
?? codex/reports/web_platform/phase4_p2_atomic_run_quota.verify.log
```

<!-- AUTO_VERIFY_END -->
