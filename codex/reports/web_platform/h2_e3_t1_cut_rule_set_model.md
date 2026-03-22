PASS

## 1) Meta
- Task slug: `h2_e3_t1_cut_rule_set_model`
- Kapcsolodo canvas: `canvases/web_platform/h2_e3_t1_cut_rule_set_model.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t1_cut_rule_set_model.yaml`
- Futas datuma: `2026-03-22`
- Branch / commit: `main`
- Fokusz terulet: `Mixed (cut rule set truth + owner-scoped CRUD + smoke)`

## 2) Scope

### 2.1 Cel
- Az `app.cut_rule_sets` tabla bevezetese a minimalis H2 schema szerint.
- Owner-scoped CRUD backend a cut rule set rekordokhoz (POST/GET/PATCH/DELETE).
- Verziozhatosag ugyanazon logikai rule set nev alatt (determinisztikus `version_no` emeles).
- `machine_code` / `material_code` / `thickness_mm` meta kezeles a jelenlegi repo truth-hoz igazitva (text + numeric, nem catalog FK).
- Aktiv/inaktiv allapot kezeles (`is_active`).
- Task-specifikus smoke a sikeres es hibas agakra (24 teszt).

### 2.2 Nem-cel (explicit)
- `app.cut_contour_rules` tabla.
- Contour-level lead-in/lead-out vagy entry side policy.
- Contour classification -> rule matching engine.
- Manufacturing profile version FK-bovites (rule set binding).
- Snapshot manufacturing bovites, plan builder, preview, postprocess vagy export.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- Task artefaktok:
  - `canvases/web_platform/h2_e3_t1_cut_rule_set_model.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t1_cut_rule_set_model.yaml`
  - `codex/prompts/web_platform/h2_e3_t1_cut_rule_set_model/run.md`
  - `codex/codex_checklist/web_platform/h2_e3_t1_cut_rule_set_model.md`
  - `codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md`
- DB migration:
  - `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- Backend:
  - `api/services/cut_rule_sets.py` (uj)
  - `api/routes/cut_rule_sets.py` (uj)
  - `api/main.py` (modositott — cut_rule_sets router bekotese)
- Smoke:
  - `scripts/smoke_h2_e3_t1_cut_rule_set_model.py`

### 3.2 Mi valtozott es miert
- **Migration SQL**: `app.cut_rule_sets` tabla letrehozasa a canvas/H2 docs szerinti mezoivel (`id`, `owner_user_id`, `name`, `machine_code`, `material_code`, `thickness_mm`, `version_no`, `is_active`, `notes`, `metadata_jsonb`, `created_at`, `updated_at`) + unique constraint `(owner_user_id, name, version_no)` + check constraintek (name non-empty, machine/material optional non-empty, thickness positive, version positive) + owner indexek + RLS policyk (select/insert/update/delete owner scope) + updated_at trigger.
- **api/services/cut_rule_sets.py**: uj service reteg — `create_cut_rule_set` (auto version_no emeles), `list_cut_rule_sets`, `get_cut_rule_set`, `update_cut_rule_set` (partial update), `delete_cut_rule_set`. Mintakovetes a meglevo H2-E1-T2 project_manufacturing_selection service validacios stilusabol.
- **api/routes/cut_rule_sets.py**: minimalis FastAPI route-ok — POST /cut-rule-sets, GET /cut-rule-sets, GET /cut-rule-sets/{id}, PATCH /cut-rule-sets/{id}, DELETE /cut-rule-sets/{id}. Owner-scoped, StrictRequestModel, CutRuleSetResponse.
- **api/main.py**: a `cut_rule_sets_router` bekotese a `/v1` prefix ala.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md` -> **PASS**

### 4.2 Opcionalis, feladatfuggo parancsok
- `python3 -m py_compile api/services/cut_rule_sets.py api/routes/cut_rule_sets.py api/main.py scripts/smoke_h2_e3_t1_cut_rule_set_model.py` -> **PASS**
- `python3 scripts/smoke_h2_e3_t1_cut_rule_set_model.py` -> **PASS** (24/24 test)

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T00:05:46+01:00 → 2026-03-22T00:09:20+01:00 (214s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.verify.log`
- git: `main@69d969a`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? .claude/
?? api/routes/cut_rule_sets.py
?? api/services/cut_rule_sets.py
?? canvases/web_platform/h2_e3_t1_cut_rule_set_model.md
?? codex/codex_checklist/web_platform/h2_e3_t1_cut_rule_set_model.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e3_t1_cut_rule_set_model.yaml
?? codex/prompts/web_platform/h2_e3_t1_cut_rule_set_model/
?? codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md
?? codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.verify.log
?? scripts/smoke_h2_e3_t1_cut_rule_set_model.py
?? supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Letrejon az `app.cut_rule_sets` tabla a minimalis H2 schema szerint | PASS | `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql:L5-L23` | Tabla letrehozva: id, owner_user_id, name, machine_code, material_code, thickness_mm, version_no, is_active, notes, metadata_jsonb, created_at, updated_at + unique + check constraintek | code review |
| #2 A tabla a jelenlegi repo truth-hoz igazodva `machine_code`/`material_code`/`thickness_mm` mezoket hasznal | PASS | `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql:L8-L10` | text + numeric(10,3) mezok, nem catalog FK-k — igazodik a manufacturing_profile_versions mintahoz | smoke Test 8 |
| #3 A rule setek owner-scope-ban CRUD-olhatok | PASS | `api/services/cut_rule_sets.py` + `api/routes/cut_rule_sets.py` | POST/GET/PATCH/DELETE owner-scoped; RLS policyk + service-szintu owner filter | smoke Test 1-7 |
| #4 A rule setek tenylegesen verziozhatok ugyanazon logical name alatt | PASS | `api/services/cut_rule_sets.py:L55-L67` (`_next_version_no`) | Determinisztikus version_no emeles: max(version_no)+1 az owner+name csoportban | smoke Test 2 |
| #5 Az `is_active` allapot kezelheto | PASS | `api/routes/cut_rule_sets.py` PATCH endpoint + `api/services/cut_rule_sets.py:L149` | PATCH-csel updatelheto; create default true | smoke Test 5 |
| #6 A task nem nyitja ki a contour rule, matching, snapshot vagy plan scope-ot | PASS | code review | Nincs `cut_contour_rules`, rule matching, snapshot bovites vagy plan builder — kizarolag cut_rule_sets domain | code review |
| #7 Keszul task-specifikus smoke script | PASS | `scripts/smoke_h2_e3_t1_cut_rule_set_model.py` (24 teszt) | create + versioning + owner-scope list + GET + PATCH + DELETE + foreign owner isolation + meta stability | smoke PASS |
| #8 Checklist es report evidence-alapon ki van toltve | PASS | jelen report + checklist | Evidence matrix es AUTO_VERIFY blokk kitoltve | verify.sh |
| #9 `verify.sh --report ...` PASS | PASS | AUTO_VERIFY blokk lentebb | check.sh exit code 0, teljes smoke suite zold | verify.sh |

## 6) Advisory notes (nem blokkolo)
- A `machine_code` es `material_code` mezok nullable text tipusuak, ahogy a manufacturing_profile_versions tablaban is. Kesobbi H2/H3 taskokban catalog FK-kra valthatnak, ha a machine_catalog/material_catalog tablak letrejonnek.
- A `name` es `version_no` mezok nem updatelehetok PATCH-csel — ezek immutable identifierek. Uj verziohoz uj POST szukseges.
- A PATCH update request `StrictRequestModel`-t hasznal (extra="forbid"), igy a nem engedett mezok (name, version_no, owner_user_id) elutasitasra kerulnek.
- A service `_next_version_no` a max(version_no)+1 logikara epit, ami race condition eseten a DB unique constraint vedekezik.

## 7) Follow-ups (opcionalis)
- H2-E3-T2: cut_contour_rules tabla es CRUD bevezetese, amely a cut_rule_sets-re epit.
- H2-E3-T3: contour class -> rule matching engine, amely a geometry_contour_classes es cut_contour_rules alapjan dontest hoz.
- Kesobbi H2: manufacturing profile version FK-bovites (`default_cut_rule_set_id`, `outer_cut_rule_set_id`, `inner_cut_rule_set_id`).
- Kesobbi: machine_catalog / material_catalog FK-ra valtast, ha a catalog domain letrejon.
