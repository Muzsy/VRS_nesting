PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e6_t1_result_normalizer_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t1_result_normalizer_h1_minimum.yaml`
- Futas datuma: `2026-03-20`
- Branch / commit: `main @ 73212cd (dirty working tree)`
- Fokusz terulet: `Worker result normalizer + projection truth (H1 minimum)`

## 2) Scope

### 2.1 Cel
- Raw `solver_output.json` v1 payload normalizalasa a snapshot manifest truth alapjan.
- Canonical projection write a H0 tablavilagra: `app.run_layout_sheets`, `app.run_layout_placements`, `app.run_layout_unplaced`, `app.run_metrics`.
- Run-szintu idempotens projection replace/retry-biztos viselkedes kialakitasa.
- Worker success zaras atallitasa a normalizer summary-ra (counts mar nem a legacy `_read_run_metrics` fallbackbol jon).
- Task-specifikus smoke fake snapshot + fake DB gateway boundaryval.

### 2.2 Nem-cel (explicit)
- Viewer SVG/DXF vagy export artifact pipeline.
- Raw artifact policy/path redesign.
- Nagy `api/routes/runs.py` redesign.
- Uj DB tabla/enum/schema bevezetese.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t1_result_normalizer_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e6_t1_result_normalizer_h1_minimum/run.md`
- `worker/result_normalizer.py`
- `worker/main.py`
- `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- `codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`

### 3.2 Mi valtozott es miert
- `worker/result_normalizer.py`: explicit normalizer boundary keszult a snapshot truth + raw solver output egyuttes feldolgozasara, deterministic bbox/metrics/unplaced aggregacioval.
- `worker/main.py`: bekerult a run-szintu projection replace SQL boundary (`replace_run_projection`), es a `done` zaras mar a normalizer summary-bol szamolt countokra epul.
- `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`: fake snapshot/fake gateway smoke bizonyitja a mappinget, aggregaciot, idempotens rerunt es hibagakat.

### 3.3 Part/sheet feloldas a snapshot manifestekbol
- Part mapping: `parts_manifest_jsonb.part_revision_id` + `selected_nesting_derivative_id` alapjan, geometria `geometry_manifest_jsonb`-bol.
- Sheet mapping: `sheets_manifest_jsonb` canonical sorrendben, `required_qty` szerint kiterjesztett sheet-instance lista; a solver `sheet_index` erre mutat.

### 3.4 Projection vegallapot kialakitasa
- `run_layout_sheets`: csak hasznalt sheet indexekre sor, `sheet_revision_id/width_mm/height_mm/utilization_ratio`.
- `run_layout_placements`: placementenkent sor, `transform_jsonb` + transzformalt `bbox_jsonb`.
- `run_layout_unplaced`: `(part_revision_id, reason)` aggregacio `remaining_qty` alapon.
- `run_metrics`: deterministic counts + utilization + metrics_jsonb.

### 3.5 Utilization_ratio szamitas (kompromisszum explicit)
- `part_area_mm2`: snapshot geometry polygon (outer - holes) shoelace terulet.
- `sheet_area_mm2`: `width_mm * height_mm`.
- `sheet utilization`: adott sheet placed_area / sheet_area.
- `run utilization`: osszesitett placed_area / osszesitett hasznalt sheet_area.
- `remnant_value`: H1 minimumon `null` marad (nincs gazdasagi input a megbizhato szamitasra).

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/engine_adapter_input.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit worker-oldali result normalizer helper/boundary. | PASS | `worker/result_normalizer.py:14-27`; `worker/result_normalizer.py:279-472` | Kulon helper modul adja a normalizer boundaryt, projection + summary kimenettel. | `py_compile` |
| A normalizer a raw `solver_output.json`-t a snapshot manifest truth-tal egyutt dolgozza fel. | PASS | `worker/result_normalizer.py:174-277`; `worker/result_normalizer.py:279-295` | A part/sheet/geometria indexeles a snapshot manifestekbol tortenik, nem ad hoc raw heurisztikabol. | Smoke PASS |
| A `run_layout_sheets` projection hasznalt sheetenkent feltoltodik. | PASS | `worker/result_normalizer.py:352-394`; `worker/main.py:575-596` | A normalizer hasznalt sheet indexenkent epit sorokat, majd a worker beszurja a canonical tablaba. | Smoke sheet assertions |
| A `run_layout_placements` projection placementenkent feltoltodik platform-kompatibilis `transform_jsonb` es `bbox_jsonb` adattal. | PASS | `worker/result_normalizer.py:322-350`; `worker/result_normalizer.py:134-167`; `worker/main.py:597-633`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:204-216` | Minden placement sorhoz deterministic transform es transzformalt bbox keszul. | Smoke rotated bbox assert |
| A `run_layout_unplaced` projection aggregalt `remaining_qty` szemantikaval feltoltodik. | PASS | `worker/result_normalizer.py:395-433`; `worker/main.py:634-659`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:218-222` | `(part_revision_id, reason)` bucket aggregacio adja a projection sorokat. | Smoke aggregation assert |
| A `run_metrics` sor determinisztikusan kiszamolt counts/utilization adatokkal frissul. | PASS | `worker/result_normalizer.py:434-460`; `worker/result_normalizer.py:116-131`; `worker/main.py:660-688`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:180-203` | Counts + utilization determinisztikus terulet-szamitasbol jonnek, run_metrics upserttel frissulnek. | Smoke utilization assert |
| A projection write run-szintu idempotens replace viselkedest ad. | PASS | `worker/main.py:549-688`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:175-179`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:224-230` | Run-szintu delete+insert+upsert pattern, ugyanarra a bemenetre stabil projection kimenet. | Smoke deterministic + fake gateway replace |
| A worker `done` zarasa mar a normalizer summary-ra epul, nem a legacy `_read_run_metrics(run_dir)` fallbackra. | PASS | `worker/main.py:1493-1512`; `worker/main.py:984-1012` | Canonical success path a normalizer summary countsot hasznalja; legacy helper mar nem a `done` truth forrasa. | Diff review + smoke |
| A task nem csuszik at viewer SVG/DXF/export vagy nagy runs API redesign scope-ba. | PASS | `worker/result_normalizer.py:279-472`; `worker/main.py:1493-1512`; `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t1_result_normalizer_h1_minimum.yaml:16-26` | Csak worker-side projection truth valtozott, route/viewer/export reszek nem nyitottak uj scope-ot. | Diff review |
| Keszul task-specifikus smoke a sikeres es hibas normalizer agakra. | PASS | `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:168-230`; `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py:233-258` | Smoke lefedi success mappinget + idempotenciat + unknown part/sheet_index hibagakat. | Smoke PASS |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md:1`; `codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md:1` | Dokumentacios artefaktok DoD->Evidence alapon kitoltve. | Dokumentacios ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.verify.log` | Standard repo gate wrapperrel futtatva. | verify.sh |

## 6) Advisory notes
- A `worker/main.py` legacy `_read_run_metrics` helper megmaradt a fajlban, de a canonical done-zaras mar nem erre epul.
- A `replace_run_projection` SQL boundary run-idempotens replace, de tranzakcio explicit SQL function nelkul, egyetlen multi-CTE statementben valosul meg.
- `remnant_value` H1 minimumon tovabbra is `null`, mert nincs megbizhato gazdasagi input.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-20T20:56:46+01:00 → 2026-03-20T21:00:18+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.verify.log`
- git: `main@73212cd`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 worker/main.py | 188 +++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 183 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M worker/main.py
?? canvases/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e6_t1_result_normalizer_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e6_t1_result_normalizer_h1_minimum/
?? codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md
?? codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.verify.log
?? scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py
?? worker/result_normalizer.py
```

<!-- AUTO_VERIFY_END -->
