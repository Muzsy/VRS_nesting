PASS

## 1) Meta
- Task slug: `h1_e4_t3_queue_lease_mechanika_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ 91ab5d6 (dirty working tree)`
- Fokusz terulet: `Worker queue lease helper + worker realignment + smoke + codex artefaktok`

## 2) Scope

### 2.1 Cel
- H1 minimum queue lease helper bevezetese a worker oldalon.
- Atomikus claim + tokenhez kotott heartbeat + explicit lease TTL biztositas.
- Minimalis expired-lease reclaim szemantika bevezetese.
- `worker/main.py` claim/heartbeat aganak helperre allitasa.

### 2.2 Nem-cel (explicit)
- Solver start/process orchestration ujratervezese.
- Result normalizer, projection vagy artifact pipeline scope-bovites.
- Terminalis queue lifecycle teljes policy redesign.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum/run.md`
- `worker/queue_lease.py`
- `worker/main.py`
- `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`
- `codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`

### 3.2 Mit szallit le a task (H1 minimum lease scope)
- Kulon `worker/queue_lease.py` helper modult claim + heartbeat funkcionalitassal.
- Atomikus claim logikat `FOR UPDATE SKIP LOCKED` mintaval.
- Claimnel canonical lease mezo frissites:
  - `leased_by`, `lease_token`, `leased_at`, `heartbeat_at`, `lease_expires_at`
  - `queue_state='leased'`
  - `attempt_no` noveles + `attempt_status='leased'`
- Heartbeat logikat tokenhez kotott ownership checkkel (`run_id + leased_by + lease_token`).
- Expired lease reclaim minimalis szemantikaval (`lease_expires_at <= now()` eseten uj worker claimelhet).
- `worker/main.py` helperre kotese + explicit lost-lease kezeles (kontrollalt process stop/hiba).

### 3.3 Mit NEM szallit le meg
- Solver start/result/artifact workflow redesign.
- Full terminal retry/backoff policy formalizalasa.
- H1-E5 scope (engine adapter / solver execution / result normalizer).

### 3.4 Kompromisszumok / legacy maradvany
- A worker tobb helyen tovabbra is management SQL-t hasznal; ebben a taskban csak a claim/heartbeat lease truth kerult explicit helperbe.
- Lost-lease eseten a worker kontrollaltan leall es hibaval kilep a feldolgozasbol; run terminalis policy nem lett ebben a taskban ujratervezve.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/queue_lease.py worker/main.py scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit worker-side lease helper. | PASS | `worker/queue_lease.py:52`; `worker/queue_lease.py:146` | A helper kulon modulban ad explicit claim + heartbeat API-t. | `py_compile` + smoke |
| A helper canonical queue truth-ra epul. | PASS | `worker/queue_lease.py:69`; `worker/queue_lease.py:92`; `worker/queue_lease.py:167` | A logika `app.run_queue` + `app.nesting_runs` tablakra es canonical lease mezokre epul. | Kodellenorzes |
| A claim logika atomikus es duplafutas ellen vedett. | PASS | `worker/queue_lease.py:88`; `worker/queue_lease.py:103` | `FOR UPDATE SKIP LOCKED` + single-row update CTE atomikus claimet ad. | Smoke dupla-claim branch |
| Sikeres claim `queue_state='leased'` + lease mezoket allit. | PASS | `worker/queue_lease.py:93`; `worker/queue_lease.py:98` | `leased_by`, `lease_token`, `leased_at`, `heartbeat_at`, `lease_expires_at` claimnel beall. | Smoke success claim |
| `attempt_no` / `attempt_status` H1 minimum szinten frissul. | PASS | `worker/queue_lease.py:99`; `worker/queue_lease.py:100`; `worker/main.py:341` | Claimnel `attempt_no+1` + `attempt_status='leased'`, run startkor `attempt_status='running'`. | Smoke attempt_no assert |
| A lease TTL explicit, nem implicit magic value. | PASS | `worker/main.py:142`; `worker/main.py:149`; `worker/main.py:150`; `worker/main.py:230`; `worker/main.py:243` | `WORKER_QUEUE_LEASE_TTL_S` explicit beallitas/hatas claim es heartbeat agban. | `py_compile` + kodellenorzes |
| Heartbeat tokenhez kotott es lost-lease helyzetet kontrollaltan kezeli. | PASS | `worker/queue_lease.py:171`; `worker/queue_lease.py:174`; `worker/queue_lease.py:175`; `worker/main.py:1131`; `worker/main.py:1136`; `worker/main.py:1211` | Heartbeat ownership+token checkkel megy, miss eseten worker explicit lease-lost agra lep. | Smoke wrong-token/lost-lease |
| Van minimalis expired-lease reclaim szemantika. | PASS | `worker/queue_lease.py:77`; `worker/queue_lease.py:97`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:228`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:235` | Lejart lease ujra claimelheto, uj tokennel, novelt attempt szammal. | Smoke expired reclaim |
| A `worker/main.py` claim/heartbeat helperre realignalva. | PASS | `worker/main.py:23`; `worker/main.py:226`; `worker/main.py:237`; `worker/main.py:1131` | Inline claim/heartbeat SQL helyett helper hivasok futnak. | `py_compile` |
| A task nem csuszik at solver/result/artifact redesign scope-ba. | PASS | `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml:20`; `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml:21`; `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml:22` | A valtozasok worker lease helper + claim/heartbeat scope-on belul maradtak. | Diff ellenorzes |
| Keszult task-specifikus smoke script a fo lease agakra. | PASS | `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:179`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:192`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:200`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:218`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:228`; `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py:239` | Lefedi success claim, dupla-claim vedelem, token heartbeat, wrong-token/lost-lease, expired reclaim agakat. | Smoke |

## 6) Advisory notes
- A duplafutas elleni vedelem kulcsa tovabbra is az atomikus claim + tokenes heartbeat ownership check.
- A worker teljes terminalis lease lifecycle policy (pl. explicit lost-lease recovery strategy) kovetkezo task szinten reszletezendo.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T20:14:02+01:00 → 2026-03-19T20:17:32+01:00 (210s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.verify.log`
- git: `main@91ab5d6`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 worker/main.py | 129 ++++++++++++++++++++++++++++++++++++---------------------
 1 file changed, 81 insertions(+), 48 deletions(-)
```

**git status --porcelain (preview)**

```text
 M worker/main.py
?? canvases/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e4_t3_queue_lease_mechanika_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum/
?? codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md
?? codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.verify.log
?? scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py
?? worker/queue_lease.py
```

<!-- AUTO_VERIFY_END -->
