# Report — h2_e4_t2_manufacturing_plan_builder

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e4_t2_manufacturing_plan_builder`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e4_t2_manufacturing_plan_builder.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t2_manufacturing_plan_builder.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main / 9ac2d3b
* **Fokusz terulet:** Schema | Service | Scripts

## 2) Scope

### 2.1 Cel
- Persisted manufacturing plan truth reteg bevezetese (`run_manufacturing_plans`, `run_manufacturing_contours`).
- Dedikalt builder service, amely snapshot + projection + derivative + classification + explicit cut rule set alapjan plan-t epit.
- Task-specifikus smoke script az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- Manufacturing preview SVG.
- Postprocessor adapter / domain aktivacio.
- Machine-neutral vagy machine-specific export artifact.
- Cut rule set resolver logika (explicit `cut_rule_set_id` a helyes megoldas, mert a repoban nincs bizonyitott FK-lanc a snapshot manufacturing profile version es a cut rule set kozott).
- Korabbi truth tablak visszairasa.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
* **Service:**
  * `api/services/manufacturing_plan_builder.py`
* **Scripts:**
  * `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h2_e4_t2_manufacturing_plan_builder.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t2_manufacturing_plan_builder.yaml`
  * `codex/prompts/web_platform/h2_e4_t2_manufacturing_plan_builder/run.md`
  * `codex/codex_checklist/web_platform/h2_e4_t2_manufacturing_plan_builder.md`
  * `codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti a `run_manufacturing_plans` es `run_manufacturing_contours` persisted truth tablakat audit FK-lancokkal (`manufacturing_profile_version_id`, `cut_rule_set_id`, `geometry_derivative_id`, `contour_class_id`, `matched_rule_id`) + owner-scoped RLS.
* **Service:** Implementalja a manufacturing plan builder-t, amely snapshot-first elvvel dolgozik, explicit `cut_rule_set_id`-t var, a meglevo `cut_rule_matching.py` engine-t hasznalja, es idempotens (delete-then-insert).
* **Smoke:** 39 teszt bizonyitja a fo invariansokat (plan letrejon, contour matched, idempotens, nincs write korabbi truthba, nincs preview/export).

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md` -> PASS (206s, 56/56 pytest, mypy 0 issues)

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/manufacturing_plan_builder.py scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py` -> PASS
* `python3 scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py` -> PASS (39/39)

### 4.4 Automatikus blokk
<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T14:59:28+01:00 → 2026-03-22T15:02:54+01:00 (206s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.verify.log`
- git: `main@9ac2d3b`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? api/services/manufacturing_plan_builder.py
?? canvases/web_platform/h2_e4_t2_manufacturing_plan_builder.md
?? codex/codex_checklist/web_platform/h2_e4_t2_manufacturing_plan_builder.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e4_t2_manufacturing_plan_builder.yaml
?? codex/prompts/web_platform/h2_e4_t2_manufacturing_plan_builder/
?? codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md
?? codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.verify.log
?? scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py
?? supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt |
| --- | ---: | --- | --- | --- |
| #1 Letezik `run_manufacturing_plans` + `run_manufacturing_contours` | PASS | `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql:L11-L58` | Ket tabla audit FK-lancokkal, unique constraint (run_id, sheet_id) | smoke Test 1 |
| #2 A builder snapshot + projection + derivative + classification + rule set alapjan epit | PASS | `api/services/manufacturing_plan_builder.py:L57-L80` | `build_manufacturing_plan()` beolvassa a snapshot-ot, projection-t, derivative-ket, classification-t es matching-et | smoke Test 1: 39/39 |
| #3 Nem live project manufacturing selectionbol dolgozik | PASS | `api/services/manufacturing_plan_builder.py:L73-L82` | A builder `nesting_run_snapshots.manufacturing_manifest_jsonb`-t olvassa; nincs `project_manufacturing_selection` hivatkozas | smoke Test 8 |
| #4 Nem talal ki cut rule set resolver logikat | PASS | `api/services/manufacturing_plan_builder.py:L57` | Explicit `cut_rule_set_id` parameter; nincs resolver | smoke Test 7 |
| #5 Contour rekordok matched rule + entry/lead/cut-order infot tartalmaznak | PASS | `api/services/manufacturing_plan_builder.py:L138-L170` | Minden contour tartalmaz `matched_rule_id`, `entry_point_jsonb`, `lead_in_jsonb`, `lead_out_jsonb`, `cut_order_index` | smoke Test 2, Test 3 |
| #6 A builder idempotens | PASS | `api/services/manufacturing_plan_builder.py:L108-L110` | `_delete_existing_plans()` torli a korabbi planeket, cascade torli a contour-okat | smoke Test 6 |
| #7 Nem ir vissza korabbi truth tablaba | PASS | `api/services/manufacturing_plan_builder.py` | Csak `run_manufacturing_plans` + `run_manufacturing_contours` tablakba ir | smoke Test 4 |
| #8 Nem nyit preview / postprocessor / export scope-ot | PASS | `api/services/manufacturing_plan_builder.py` | Nincs `run_artifacts` iras, nincs SVG generacio, nincs export logika | smoke Test 5 |
| #9 Task-specifikus smoke script keszult | PASS | `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py` | 39/39 teszt, 9 tesztkategoria | `python3 scripts/smoke_h2_e4_t2_...py` |
| #10 Checklist es report evidence-alapon kitoltve | PASS | `codex/codex_checklist/web_platform/h2_e4_t2_manufacturing_plan_builder.md` | 16/16 pont kipipalva | — |
| #11 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.verify.log` | PASS, 206s, 56/56 pytest, mypy 0 issues | `./scripts/verify.sh ...` |

## 6) Miert explicit `cut_rule_set_id` input?

A jelenlegi repoallapotban nincs bizonyitott, tartosan hasznalhato FK-lanc a snapshotolt manufacturing profile version es az aktiv `cut_rule_set_id` kozott. A `manufacturing_profile_versions` tablaban nincs `default_cut_rule_set_id` FK mező. A `cut_rule_matching.py` engine is explicit `cut_rule_set_id`-t var. Ezert ebben a taskban a builder explicit inputkent kapja a rule set azonositot — ez repo-hu dontes, nem ad-hoc workaround.

## 7) Mit szallit le es mit NEM

**Leszallitva:**
- Persisted plan truth reteg (`run_manufacturing_plans` + `run_manufacturing_contours`).
- Builder service snapshot-first + explicit rule set + meglevo matching engine hasznalataval.
- Audit FK-lanc a korabbi H2 truth tablakhoz.

**Meg nem szallitva:**
- Manufacturing preview SVG (H2-E5-T1 scope).
- Postprocessor adapter (H2-E5-T2/T3 scope).
- Machine-neutral export (H2-E5-T3 scope).
- Machine-specific export (H2-E5-T4 scope).

## 8) Advisory notes

1. A builder a `part_revisions.selected_manufacturing_derivative_id` mezot hasznalja. Ha egy placement part revisionjenek nincs manufacturing derivative-je, a builder skip-eli (warning log).
2. Az `entry_point_jsonb` jelenleg a placement transform-ot adja referenciapontkent. Valodi machine-ready entry geometry a postprocessor scope-ja.
3. A `lead_in_jsonb` / `lead_out_jsonb` strukturalt descriptor (type + source), nem geometria. Machine-ready lead path generacio nem scope.
4. Az idempotencia delete-then-insert mintaval mukodik (a `run_manufacturing_plans` CASCADE ON DELETE torli a contour-okat).

## 9) Follow-ups

- H2-E4-T3: Manufacturing metrics calculator (a plan truth retegre epulve pierce count, cut length, becsult ido).
- H2-E5-T1: Manufacturing preview SVG (a plan + contour adatokbol vizualis preview).
- Kesobbi task: `manufacturing_profile_versions.default_cut_rule_set_id` FK bevezetesekor a builder kaphat opcionalis resolver modot.
