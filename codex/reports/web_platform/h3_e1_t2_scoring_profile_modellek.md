# Report — h3_e1_t2_scoring_profile_modellek

**Status:** PASS

## 1) Meta

* **Task slug:** `h3_e1_t2_scoring_profile_modellek`
* **Kapcsolodo canvas:** `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t2_scoring_profile_modellek.yaml`
* **Futtas datuma:** 2026-03-25
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- Scoring profile domain bevezetese owner-scoped, verziozott truth-retegkent.
- Owner-scoped CRUD service + route a scoring profile es nested version domainhez.
- Route regisztralasa az `api/main.py`-ban.
- Task-specifikus smoke script az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- `project_scoring_selection` vagy barmilyen persisted project-level selection tabla.
- `run_evaluations`, ranking engine, comparison projection.
- Batch orchestration.
- Frontend preference UI.
- Business metrics, total_score szamitas, batch ranking.
- H2 manufacturing truth tabla modositasa.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
* **Service:**
  * `api/services/scoring_profiles.py`
* **Route:**
  * `api/routes/scoring_profiles.py`
* **App registration:**
  * `api/main.py`
* **Scripts:**
  * `scripts/smoke_h3_e1_t2_scoring_profile_modellek.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t2_scoring_profile_modellek.yaml`
  * `codex/prompts/web_platform/h3_e1_t2_scoring_profile_modellek/run.md`
  * `codex/codex_checklist/web_platform/h3_e1_t2_scoring_profile_modellek.md`
  * `codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti az `app.scoring_profiles` es `app.scoring_profile_versions` owner-scoped truth tablakat, composite owner-konzisztenciaval, RLS policykal es `updated_at` triggerekkel. A version tabla tartalmazza a `weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb`, `is_active` mezoket.
* **Service + Route:** Owner-scoped CRUD a scoring profile es nested version domainhez, a H3-E1-T1 run_strategy_profiles mintakat kovetve (10 service fuggveny + 10 route endpoint, owner_user_id szures mindenhol).
* **Smoke:** 9 test csoport, 72/72 PASS. Lefedi: CRUD / owner-boundary / versioning / JSON payloads / no-selection / no-evaluation / no-H2-write / migration-structure / route-structure / validation.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md` -> PASS

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/scoring_profiles.py api/routes/scoring_profiles.py scripts/smoke_h3_e1_t2_scoring_profile_modellek.py` -> PASS
* `python3 scripts/smoke_h3_e1_t2_scoring_profile_modellek.py` -> PASS (72/72)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 scoring_profiles truth reteg | PASS | `supabase/migrations/20260324110000_...sql:L13` | `create table if not exists app.scoring_profiles` | smoke 7: migration structure (20 assert) |
| #2 scoring_profile_versions truth reteg | PASS | `supabase/migrations/20260324110000_...sql:L38` | `create table if not exists app.scoring_profile_versions` | smoke 7: migration structure |
| #3 owner-scoped, verziozott | PASS | `supabase/migrations/20260324110000_...sql:L24,L55,L60` | `unique(owner_user_id, name)`, `unique(scoring_profile_id, version_no)`, composite FK `fk_scoring_profile_versions_profile_owner` | smoke 1+2+3 (27 assert) |
| #4 weights/tie_breaker/threshold/is_active | PASS | `supabase/migrations/20260324110000_...sql:L45-L48` | `weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb`, `is_active` | smoke 2: JSON payloads (6 assert) |
| #5 dedikalt service | PASS | `api/services/scoring_profiles.py` | 10 service fuggveny: create/list/get/update/delete profile + create/list/get/update/delete version | smoke 1+2 (21 assert) |
| #6 dedikalt route | PASS | `api/routes/scoring_profiles.py` | 10 endpoint, prefix `/scoring-profiles` | smoke 8: prefix check |
| #7 main.py regisztracio | PASS | `api/main.py:L26,L122` | `from api.routes.scoring_profiles import router` + `app.include_router(scoring_profiles_router, prefix="/v1")` | py_compile PASS |
| #8 nincs project_scoring_selection | PASS | source + migration scan | `project_scoring_selection` nem jelenik meg DDL-ben, sem service/route forrasban | smoke 4: 4 assert + smoke 7: 1 DDL assert |
| #9 nincs run_evaluations/ranking/comparison | PASS | source + migration scan | `run_evaluations`, `run_ranking`, `run_batches`, `total_score` nem jelenik meg a service-ben | smoke 5: 8 assert + smoke 7: 2 DDL assert |
| #10 nincs H2 manufacturing write | PASS | source scan | `run_manufacturing`, `manufacturing_profiles` nem jelenik meg a service-ben | smoke 6: 7 assert + smoke 7: 1 DDL assert |
| #11 smoke script | PASS | `scripts/smoke_h3_e1_t2_scoring_profile_modellek.py` | 9 test csoport, 72/72 PASS | smoke futtas output |
| #12 checklist + report | PASS | `codex/codex_checklist/.../h3_e1_t2_...md`, `codex/reports/.../h3_e1_t2_...md` | Minden DoD pont evidence-cel kitoltve | jelen report |
| #13 verify.sh PASS | PASS | `codex/reports/.../h3_e1_t2_...verify.log` | verify.sh PASS, check.sh exit 0, 206s | `./scripts/verify.sh --report ...` |

## 8) Advisory notes

- A scoring domain minimalis truth-reteg: profil + verzio + owner-scoped CRUD. A harom scoring config jsonb mezo (`weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb`) pontosan a H3 reszletes doksi specifikaciot koveti.
- A `weights_jsonb` a H3 peldaihoz igazodott kulcsokkal tesztelve (utilization_weight, unplaced_penalty, sheet_count_penalty, remnant_value_weight, process_time_penalty, priority_fulfilment_weight, inventory_consumption_penalty).
- A scoring domain kulon truth-reteg, nem az evaluation engine resze es nem a project-level selection vilag resze. A kesobbi evaluation engine majd erre a verziozott truthra epul.
- A migration a H3-E1-T1 run_strategy_profiles domain mintajat koveti: tabla + index + composite FK + RLS + updated_at trigger.
- Ez a task szandekosan nem vezet be score-szamitast, batch rankinget, objective projectiont. A scoring profil itt a kesobbi evaluation engine konfiguracios truth-ja.

## 9) Follow-ups

- H3-E1-T3: `project_run_strategy_selection` es `project_scoring_selection` persisted selection tablak.
- H3-E3+: evaluation engine, amely a scoring profilra hivatkozva ertekel futasokat.
- A H2 manufacturing metrics csak kesobbi inputja lesz a H3-E3 evaluation enginenek, de itt meg nem hasznaljuk score-szamitasra.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-26T00:29:22+01:00 → 2026-03-26T00:32:48+01:00 (206s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.verify.log`
- git: `main@edb1bd9`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/scoring_profiles.py
?? api/services/scoring_profiles.py
?? canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md
?? codex/codex_checklist/web_platform/h3_e1_t2_scoring_profile_modellek.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_e1_t2_scoring_profile_modellek.yaml
?? codex/prompts/web_platform/h3_e1_t2_scoring_profile_modellek/
?? codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md
?? codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.verify.log
?? scripts/smoke_h3_e1_t2_scoring_profile_modellek.py
?? supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql
```

<!-- AUTO_VERIFY_END -->
