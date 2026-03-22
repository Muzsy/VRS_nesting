# Report — H2-E3-T3 rule matching logic

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e3_t3_rule_matching_logic`
* **Canvas:** `canvases/web_platform/h2_e3_t3_rule_matching_logic.md`
* **Goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t3_rule_matching_logic.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Service + Smoke

## 2) Scope

### 2.1 Cel
- Dedikalt rule matching service bevezetese (`api/services/cut_rule_matching.py`).
- A matching engine a `geometry_contour_classes` + `cut_contour_rules` meglevo truth retegre epul.
- Explicit `cut_rule_set_id` inputtal dolgozik, nem resolver.
- Determinisztikus tie-break, feature_class fallback, hossztartomany-szures.
- Task-specifikus smoke script.

### 2.2 Nem-cel (explicit)
- Manufacturing profile resolver vagy project manufacturing selection.
- Snapshot manufacturing bovites.
- `run_manufacturing_plans` / `run_manufacturing_contours` irasa.
- Uj migracio vagy persisted matching tablak.
- Preview, postprocess vagy export.
- A kesobbi H2-E4 plan builder majd ezt a matching service-t fogyasztja, de ez a task meg nem keszit manufacturing plant.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Service:**
  * `api/services/cut_rule_matching.py`
* **Smoke:**
  * `scripts/smoke_h2_e3_t3_rule_matching_logic.py`
* **Docs:**
  * `canvases/web_platform/h2_e3_t3_rule_matching_logic.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t3_rule_matching_logic.yaml`
  * `codex/prompts/web_platform/h2_e3_t3_rule_matching_logic/run.md`
  * `codex/codex_checklist/web_platform/h2_e3_t3_rule_matching_logic.md`
  * `codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md`

### 3.2 Miert valtoztak?
- A H2-E3-T3 task bevezeti a contour class -> cut contour rule matching engine-t.
- A service, smoke es dokumentacio a canvas specifikacioja szerint keszultek.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md` -> PASS

### 4.2 Feladat-specifikus parancsok
* `python3 -m py_compile api/services/cut_rule_matching.py scripts/smoke_h2_e3_t3_rule_matching_logic.py` -> PASS
* `python3 scripts/smoke_h2_e3_t3_rule_matching_logic.py` -> PASS (37/37)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T12:41:24+01:00 → 2026-03-22T12:44:49+01:00 (205s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e3_t3_rule_matching_logic.verify.log`
- git: `main@bd867ba`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? api/services/cut_rule_matching.py
?? canvases/web_platform/h2_e3_t3_rule_matching_logic.md
?? codex/codex_checklist/web_platform/h2_e3_t3_rule_matching_logic.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e3_t3_rule_matching_logic.yaml
?? codex/prompts/web_platform/h2_e3_t3_rule_matching_logic/
?? codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md
?? codex/reports/web_platform/h2_e3_t3_rule_matching_logic.verify.log
?? scripts/smoke_h2_e3_t3_rule_matching_logic.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

**Tie-break szabalyok (explicit dokumentacio):**
1. Specifikus `feature_class` egyezes elobb, mint `default` fallback.
2. Kisebb `sort_order` elobb.
3. Lexikografikusan kisebb `id` (UUID string) mint vegso determinisztikus tie-break.

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Keszul dedikalt rule matching service | PASS | `api/services/cut_rule_matching.py:L1-L236` | Onallo service `match_rules_for_derivative()` foependponttal | `python3 -m py_compile` |
| #2 A matching engine meglevo truthra epul | PASS | `api/services/cut_rule_matching.py:L95-L122` | `_load_contour_classes` olvassa `geometry_contour_classes`-t, `_load_enabled_rules` olvassa `cut_contour_rules`-t — mindketto csak `select_rows` | smoke Test 1-8 |
| #3 Explicit `cut_rule_set_id` input, nem resolver | PASS | `api/services/cut_rule_matching.py:L37-L55` | `match_rules_for_derivative()` kotelezo `cut_rule_set_id` parametert var; semelyik importban nincs manufacturing profile, project selection vagy resolver | smoke Test 1 |
| #4 `feature_class` fallback egyertelmu es tesztelt | PASS | `api/services/cut_rule_matching.py:L152-L181` | Eloszor specifikus `feature_class` match, ha nincs, `default` fallback; ha egyik sem, unmatched | smoke Test 3: slot beats default; default contour gets default rule |
| #5 `min/max_contour_length_mm` szures mukodik | PASS | `api/services/cut_rule_matching.py:L202-L216` | `_filter_by_perimeter()`: NULL hatarok = korlatlan; perimeter < min vagy > max = kizarva | smoke Test 5: 50mm perimeter vs 100-200mm range -> unmatched; 150mm -> matched |
| #6 Tie-break determinisztikus es dokumentalt | PASS | `api/services/cut_rule_matching.py:L219-L226`, modul docstring:L21-L26 | `_pick_best()`: sort by (sort_order ASC, id ASC); modul docstringben dokumentalt | smoke Test 6: same sort_order -> lex smaller id; lower sort_order wins |
| #7 Unmatched contour eseten tiszta indok | PASS | `api/services/cut_rule_matching.py:L140-L150,L183-L192` | `unmatched_reason` string: "no rules for contour_kind=..." vagy "all rules exclude perimeter_mm=..." | smoke Test 5, 10 |
| #8 Nem ir vissza truth tablaba | PASS | `api/services/cut_rule_matching.py` | Kizarolag `select_rows` hivasok; nincs `insert_row`, `update_rows`, `delete_rows` | smoke Test 7: write_calls == 0, contour classes unchanged |
| #9 Nem nyitja ki plan/snapshot/export scope-ot | PASS | `api/services/cut_rule_matching.py` | Az egyetlen import `api.supabase_client.SupabaseClient`; nincs manufacturing plan, snapshot, projection, export hivatkozas | kod audit |
| #10 Task-specifikus smoke script keszul | PASS | `scripts/smoke_h2_e3_t3_rule_matching_logic.py` | 37/37 teszt PASS: outer/inner match, feature_class fallback, disabled rule, perimeter range, tie-break, no-write, mixed contours, empty/no-rules edge cases | `python3 scripts/smoke_h2_e3_t3_rule_matching_logic.py` |
| #11 Checklist es report evidence-alapon kitoltve | PASS | `codex/codex_checklist/web_platform/h2_e3_t3_rule_matching_logic.md` | Minden pont evidence-cel kitoltve | jelen report |
| #12 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e3_t3_rule_matching_logic.verify.log` | verify.sh PASS, check.sh exit 0, 205s futasido, pytest 56/56, mypy 0 issue | `./scripts/verify.sh --report ...` |

## 8) Advisory notes

- A matching engine szandekosan nem vezet be uj migraciot es nem perzisztal eredmenyt. A kesobbi H2-E4 manufacturing plan builder fogyasztja majd ezt a service-t.
- A tie-break vegso lepese lexikografikus UUID osszehasonlitas; ez determinisztikus, de nem "ertelem-alapu". Ha szukseges, kesobbi taskban bovitheto (pl. `created_at`).
- A `feature_class` egyelore csak `"default"` a contour classification service-ben (H2-E2-T2); ha a classification gazdagodik, a matching engine automatikusan kihasznalhatja.

## 9) Follow-ups

- H2-E4: manufacturing plan builder, amely ezt a matching service-t fogyasztja.
- Kesobbi bovites: tobb `feature_class` ertek a contour classification-ben (pl. `slot`, `micro_inner`).
