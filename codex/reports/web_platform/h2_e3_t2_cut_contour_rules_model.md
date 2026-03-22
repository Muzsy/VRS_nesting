# Report — H2-E3-T2 cut contour rules model

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e3_t2_cut_contour_rules_model`
* **Canvas:** `canvases/web_platform/h2_e3_t2_cut_contour_rules_model.md`
* **Goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t2_cut_contour_rules_model.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Mixed (Migration + Service + Route + Smoke)

## 2) Scope

### 2.1 Cel
- `app.cut_contour_rules` tabla bevezetese `cut_rule_set_id` FK-val.
- Owner-scoped CRUD backend a contour rule rekordokhoz.
- Outer/inner kulon szabalyok tarolhatosaga.
- Mezo-invariansok validacioja (contour_kind, lead type, pozitiv numeric, min/max tartomany).
- Task-specifikus smoke script.

### 2.2 Nem-cel (explicit)
- Rule matching engine (H2-E3-T3 scope).
- `geometry_contour_classes` rekordok konkret rule-ra kotese.
- Manufacturing profile binding / version FK bovites.
- Snapshot / plan / preview / export scope.
- Gep-/anyag-katalogus FK-k kitalalasa.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
* **Service:**
  * `api/services/cut_contour_rules.py`
* **Route:**
  * `api/routes/cut_contour_rules.py`
  * `api/main.py`
* **Smoke:**
  * `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
* **Docs:**
  * `canvases/web_platform/h2_e3_t2_cut_contour_rules_model.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t2_cut_contour_rules_model.yaml`
  * `codex/prompts/web_platform/h2_e3_t2_cut_contour_rules_model/run.md`
  * `codex/codex_checklist/web_platform/h2_e3_t2_cut_contour_rules_model.md`
  * `codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md`

### 3.2 Miert valtoztak?
- A H2-E3-T2 task bevezeti a contour-szintu szabalyok truth retegjet a cut_rule_sets ala.
- A migration, service, route es smoke a canvas specifikacioja szerint keszultek.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md` -> PASS

### 4.2 Feladat-specifikus parancsok
* `python3 -m py_compile api/services/cut_contour_rules.py api/routes/cut_contour_rules.py api/main.py scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` -> PASS
* `python3 scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` -> PASS (42/42)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T12:20:04+01:00 → 2026-03-22T12:23:38+01:00 (214s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.verify.log`
- git: `main@86f4764`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/cut_contour_rules.py
?? api/services/cut_contour_rules.py
?? canvases/web_platform/h2_e3_t2_cut_contour_rules_model.md
?? codex/codex_checklist/web_platform/h2_e3_t2_cut_contour_rules_model.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e3_t2_cut_contour_rules_model.yaml
?? codex/prompts/web_platform/h2_e3_t2_cut_contour_rules_model/
?? codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md
?? codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.verify.log
?? scripts/smoke_h2_e3_t2_cut_contour_rules_model.py
?? supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Letrejon az `app.cut_contour_rules` tabla | PASS | `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql:L6-L28` | Tabla letrehozva az osszes canvas-ban elirt mezoval: id, cut_rule_set_id, contour_kind, feature_class, lead_in/out, entry_side, min/max length, pierce, direction, sort, enabled, metadata, timestamps. | `python3 -m py_compile` + smoke |
| #2 A tabla `cut_rule_set_id` FK-val epul | PASS | `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql:L8` | `cut_rule_set_id uuid not null references app.cut_rule_sets(id) on delete cascade` | smoke Test 1: rule set ala hoz letre contour rule-t |
| #3 Owner-scoped CRUD mukodik | PASS | `api/services/cut_contour_rules.py:L99-L112`, `api/routes/cut_contour_rules.py:L103-L193` | A service `_load_owner_rule_set`-tel ellenorzi az owner_user_id-t minden CRUD muvelet elott. A route a rule set ala szervezve: `POST/GET/PATCH/DELETE /cut-rule-sets/{id}/rules[/{rule_id}]` | smoke Test 1,3,4,5,6,7 |
| #4 Outer/inner kulon tarolhato | PASS | smoke Test 1 + Test 2 | outer rule (Test 1) es inner rule (Test 2) kulon-kulon letrehozva es tarolva ugyanazon rule set alatt | smoke 42/42 PASS |
| #5 Mezo-invariansok validalva | PASS | `api/services/cut_contour_rules.py:L26-L87` | `contour_kind` check (`outer\|inner`), `lead_in/out_type` check (`none\|line\|arc`), pozitiv numeric, min<=max cross-check | smoke Test 8,9,10,11 |
| #6 Nem nyitja ki matching/snapshot/plan scope-ot | PASS | a teljes service es route | Semelyik fajl nem hivatkozik `geometry_contour_classes`-ra, manufacturing profile-ra, snapshot-ra, plan-ra vagy export-ra | kod audit |
| #7 Task-specifikus smoke script keszul | PASS | `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` | 42/42 teszt PASS: CRUD, owner-scope, validation, outer/inner, min/max | `python3 scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` |
| #8 Checklist es report evidence-alapon kitoltve | PASS | `codex/codex_checklist/web_platform/h2_e3_t2_cut_contour_rules_model.md` | Minden pont evidence-cel kitoltve | jelen report |
| #9 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.verify.log` | verify.sh PASS, check.sh exit 0, 214s futasido, pytest 56/56, mypy 0 issue | `./scripts/verify.sh --report ...` |

## 8) Advisory notes

- A `contour_kind` check jelenleg `outer|inner`; kesobbi H2-E3-T3 bovites eseten uj kind-ok felvetele migration + service valtoztatast igenyel.
- Az `entry_side_policy` es `cut_direction` mezok jelenleg free-text (nem DB enum); a canvas specifikacio szerint ez szandekos.
- A RLS policy-k a `cut_rule_sets.owner_user_id` join-on keresztul ervenyesulnek, ahogy a `geometry_contour_classes` minta mutatja.

## 9) Follow-ups

- H2-E3-T3: contour class -> rule matching engine.
- Kesobbi task: `entry_side_policy` es `cut_direction` enum szukites, ha az igeny felmerul.
