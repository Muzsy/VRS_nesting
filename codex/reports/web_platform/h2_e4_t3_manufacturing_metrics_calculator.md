# Report — h2_e4_t3_manufacturing_metrics_calculator

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e4_t3_manufacturing_metrics_calculator`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t3_manufacturing_metrics_calculator.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Scripts

## 2) Scope

### 2.1 Cel
- Kulon `app.run_manufacturing_metrics` persisted truth reteg bevezetese.
- Dedikalt calculator service, amely persisted manufacturing plan truthbol gepfuggetlen metrikat epit.
- Task-specifikus smoke script az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- Manufacturing preview SVG.
- Postprocessor adapter / domain aktivacio.
- Machine-neutral vagy machine-specific export artifact.
- Gepresolver, anyagkatalogus, valodi CAM-idomodell.
- Pricing / quoting / costing engine.
- Korabbi truth tablak visszairasa.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
* **Service:**
  * `api/services/manufacturing_metrics_calculator.py`
* **Scripts:**
  * `scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t3_manufacturing_metrics_calculator.yaml`
  * `codex/prompts/web_platform/h2_e4_t3_manufacturing_metrics_calculator/run.md`
  * `codex/codex_checklist/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`
  * `codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti a `run_manufacturing_metrics` persisted truth tablat `run_id` primary key-jel, kulon a H1 `run_metrics` tablátol, owner-scoped RLS-szel.
* **Service:** Implementalja a manufacturing metrics calculatort, amely persisted plan truthbol (run_manufacturing_contours + geometry_contour_classes + cut_contour_rules) szamolja a metrikakat. Gepfuggetlen, dokumentalt timing proxy-val. Idempotens (upsert per run_id).
* **Smoke:** Tesztek bizonyitjak a fo invariansokat (metrics letrejon, pierce_count matched rule truthbol, cut length contour perimeter truthbol, rapid determinisztikus, idempotens, nincs write korabbi truthba, nincs preview/export).

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md` -> PASS (208s, 56/56 pytest, mypy 0 issues)

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/manufacturing_metrics_calculator.py scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py` -> PASS
* `python3 scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py` -> PASS (31/31)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T16:14:07+01:00 → 2026-03-22T16:17:35+01:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.verify.log`
- git: `main@eb9e1f9`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? api/services/manufacturing_metrics_calculator.py
?? canvases/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md
?? codex/codex_checklist/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e4_t3_manufacturing_metrics_calculator.yaml
?? codex/prompts/web_platform/h2_e4_t3_manufacturing_metrics_calculator/
?? codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md
?? codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.verify.log
?? scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py
?? supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 Letezik `app.run_manufacturing_metrics` persisted truth reteg | PASS | `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql:L1-L15` | Kulon tabla `run_id` PK-val, a H1 `run_metrics` mellett | smoke + verify |
| #2 A calculator persisted plan truthbol tud metrikat kepezni | PASS | `api/services/manufacturing_metrics_calculator.py` | Olvas: run_manufacturing_contours, geometry_contour_classes, cut_contour_rules | smoke test 1 |
| #3 H2 manufacturing metrics kulon marad H1 run_metrics-tol | PASS | migration: kulon tabla `app.run_manufacturing_metrics` | Nincs modify `app.run_metrics` tablara | smoke |
| #4 pierce_count matched rule truth alapjan szamolodik | PASS | `api/services/manufacturing_metrics_calculator.py` | `cut_contour_rules.pierce_count` osszegzese | smoke test 2 |
| #5 estimated_cut_length_mm contour class perimeter truth alapjan | PASS | `api/services/manufacturing_metrics_calculator.py` | `geometry_contour_classes.perimeter_mm` osszegzese | smoke test 3 |
| #6 estimated_rapid_length_mm determinisztikus proxy | PASS | `api/services/manufacturing_metrics_calculator.py` | entry_point_jsonb pontok kozti tavolsag | smoke test 4 |
| #7 estimated_process_time_s dokumentalt proxy modell | PASS | `api/services/manufacturing_metrics_calculator.py` | Fix default sebessegek, dokumentalt formula | smoke |
| #8 Calculator idempotens | PASS | `api/services/manufacturing_metrics_calculator.py` | delete-then-insert per run_id | smoke test 5 |
| #9 Nem ir vissza korabbi truth tablaba | PASS | smoke write_log ellenorzes | Nincs write geometry_contour_classes, cut_contour_rules, stb. | smoke test 6 |
| #10 Nem nyit preview/export/costing scope-ot | PASS | smoke artifact ellenorzes | Nincs run_artifacts iras | smoke test 7 |
| #11 Task-specifikus smoke script | PASS | `scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py` | Bizonyito ereju tesztek | smoke futtas |
| #12 Checklist es report evidence-alapon | PASS | ez a report | DoD -> Evidence matrix kitoltve | — |
| #13 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.verify.log` | 208s, 56/56 pytest, mypy 0 issues | verify.sh futtas |

## 6) IO contract / mintak
Nem relevans (nincs Sparrow IO / POC valtozas).

## 7) Doksi szinkron
Nem relevans (nincs docs/ modositas).

## 8) Advisory notes

* A timing proxy fix default sebessegeket hasznal (cut: 50 mm/s, rapid: 200 mm/s, pierce: 0.5 s/pierce). Ezek dokumentalt, reprodukalhato ertekek, nem ipari kalibraciohoz igazitottak.
* A rapid length a contourok entry_point_jsonb pontjai kozti euklideszi tavolsag osszege — egyszeru, determinisztikus proxy.
* A `run_manufacturing_metrics` tabla kulon marad a H1 `run_metrics` mellettamintal — kesobb H3/decision layerben osszevonhato, ha szukseges.

## 9) Follow-ups

* H2 kovetkezo: manufacturing preview SVG generator (H2-7).
* Kesobb: machine-specific timing modell machine catalog + material resolver alapjan.
* Kesobb: pricing/costing engine manufacturing metrics felett.
