PASS

## 1) Meta
- Task slug: `h2_e2_t2_contour_classification_service`
- Kapcsolodo canvas: `canvases/web_platform/h2_e2_t2_contour_classification_service.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h2_e2_t2_contour_classification_service.yaml`
- Futas datuma: `2026-03-21`
- Branch / commit: `main`
- Fokusz terulet: `Mixed (geometry contour classification + pipeline integration + smoke)`

## 2) Scope

### 2.1 Cel
- Az `app.geometry_contour_classes` tabla bevezetese a H2 docs szerinti minimalis mezoivel.
- Contour classification service, amely a `manufacturing_canonical` derivative `contours` payloadjat olvassa.
- Outer/inner alapklasszifikacio a valos derivative payload alapjan (outer->outer, hole->inner).
- Alap geometriametrikak tarolasa contouronkent (`area_mm2`, `perimeter_mm`, `bbox_jsonb`, `is_closed`).
- Idempotens upsert logika ugyanarra a derivative-re es contour_indexre.
- DXF import pipeline bekotese: validated geometry eseten a contour classification is lefusson.

### 2.2 Nem-cel (explicit)
- `cut_rule_sets`, `cut_contour_rules`, rule matching.
- Contour-level lead-in/lead-out vagy entry side policy.
- Snapshot manufacturing manifest, run_manufacturing_plans vagy run_manufacturing_contours.
- Worker / preview / postprocess / export.
- Manufacturing profile vagy project manufacturing selection ujabb bovitese.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- Task artefaktok:
  - `canvases/web_platform/h2_e2_t2_contour_classification_service.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h2_e2_t2_contour_classification_service.yaml`
  - `codex/prompts/web_platform/h2_e2_t2_contour_classification_service/run.md`
  - `codex/codex_checklist/web_platform/h2_e2_t2_contour_classification_service.md`
  - `codex/reports/web_platform/h2_e2_t2_contour_classification_service.md`
- DB migration:
  - `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- Backend:
  - `api/services/geometry_contour_classification.py` (uj)
  - `api/services/dxf_geometry_import.py` (modositott)
- Smoke:
  - `scripts/smoke_h2_e2_t2_contour_classification_service.py`

### 3.2 Mi valtozott es miert
- **Migration SQL**: `app.geometry_contour_classes` tabla letrehozasa a H2 docs szerinti mezoivel (`id`, `geometry_derivative_id`, `contour_index`, `contour_kind`, `feature_class`, `is_closed`, `area_mm2`, `perimeter_mm`, `bbox_jsonb`, `metadata_jsonb`, `created_at`) + unique constraint `(geometry_derivative_id, contour_index)` + index + RLS policyk (select/insert/update/delete a derivative owner lancra epitve).
- **geometry_contour_classification.py**: uj service, amely a `manufacturing_canonical` derivative `contours` payloadjat olvassa, contouronkent kiszamolja a metrikakat (shoelace area, edge-sum perimeter, AABB bbox, closed check), es idempotens upsert logikával tarolja a `geometry_contour_classes` tablaba. Mapping: `outer->outer`, `hole->inner`. Feature class: `default`. Metadata: `source_contour_role`, `source_winding`, `source_point_count`.
- **dxf_geometry_import.py**: a `import_source_dxf_geometry_revision()` pipeline bovult — a derivative generalas utan, ha a `manufacturing_canonical` derivative letrejott, a contour classification service is lefut. Hiba eseten try/except + warning log, nem akasztja el a pipeline-t.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t2_contour_classification_service.md` -> **PASS**

### 4.2 Opcionalis, feladatfuggo parancsok
- `python3 -m py_compile api/services/geometry_contour_classification.py api/services/dxf_geometry_import.py scripts/smoke_h2_e2_t2_contour_classification_service.py` -> **PASS**
- `python3 scripts/smoke_h2_e2_t2_contour_classification_service.py` -> **PASS** (6/6 test)
- `python3 scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py` -> **PASS** (H2-E2-T1 regresszio zold)

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-21T23:41:18+01:00 → 2026-03-21T23:44:47+01:00 (209s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e2_t2_contour_classification_service.verify.log`
- git: `main@6da0264`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 api/services/dxf_geometry_import.py | 22 +++++++++++++++++++++-
 1 file changed, 21 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M api/services/dxf_geometry_import.py
?? api/services/geometry_contour_classification.py
?? canvases/web_platform/h2_e2_t2_contour_classification_service.md
?? codex/codex_checklist/web_platform/h2_e2_t2_contour_classification_service.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e2_t2_contour_classification_service.yaml
?? codex/prompts/web_platform/h2_e2_t2_contour_classification_service/
?? codex/reports/web_platform/h2_e2_t2_contour_classification_service.md
?? codex/reports/web_platform/h2_e2_t2_contour_classification_service.verify.log
?? scripts/smoke_h2_e2_t2_contour_classification_service.py
?? supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Letrejon az `app.geometry_contour_classes` tabla a minimalis H2 schema szerint | PASS | `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql:L8-L21` | Tabla letrehozva a H2 reszletes terv 4. szekcio szerint: id, geometry_derivative_id, contour_index, contour_kind, feature_class, is_closed, area_mm2, perimeter_mm, bbox_jsonb, metadata_jsonb, created_at + unique constraint | code review |
| #2 A classification service a `manufacturing_canonical` derivative `contours` payloadjara epit | PASS | `api/services/geometry_contour_classification.py:L96-L103` | derivative_kind check: csak `manufacturing_canonical`-t dolgoz fel, minden mast skip-el | smoke Test 5 |
| #3 A kezdeti `contour_kind` vilag repo-huen `outer` / `inner` marad | PASS | `api/services/geometry_contour_classification.py:L11-L14` (`_CONTOUR_ROLE_TO_KIND`) | Mapping: `outer->outer`, `hole->inner`. Nincs `slot`, `micro_inner` stb. | smoke Test 2 |
| #4 A `feature_class` kitoltodik es auditalhat | PASS | `api/services/geometry_contour_classification.py:L137` | Minden contourra `feature_class='default'` kerul mentesre | smoke Test 3 |
| #5 A contouronkenti `area_mm2`, `perimeter_mm`, `bbox_jsonb`, `is_closed` tarolodik | PASS | `api/services/geometry_contour_classification.py:L125-L135` | Shoelace area, edge-sum perimeter, AABB bbox, closed check — determinisztikus, points listara epul | smoke Test 3 (area ~9600, ~300; perimeter ~400 ellenorzes) |
| #6 A service idempotens ugyanarra a derivative-re | PASS | `api/services/geometry_contour_classification.py:L163-L207` (upsert logika) | Meglevo rekord update, uj rekord insert; unique constraint vedelem + retry path | smoke Test 4 |
| #7 A DXF import pipeline validated geometry eseten a classificationt is lefuttatja | PASS | `api/services/dxf_geometry_import.py:L233-L248` | A pipeline a derivative generalas utan, ha van manufacturing_canonical, hivja a `classify_manufacturing_derivative_contours()`-t. Hiba eseten warning log, nem torik el a flow | smoke Test 6 + H2-E2-T1 regresszio |
| #8 A task nem nyitja ki a cut rule, matching, snapshot vagy plan scope-ot | PASS | code review | Nincs `cut_rule_sets`, `cut_contour_rules`, rule matching, snapshot vagy plan builder — a scope szorosan contour classification truth | code review |
| #9 Keszul task-specifikus smoke script | PASS | `scripts/smoke_h2_e2_t2_contour_classification_service.py` (6 teszt) | contour class letrehozas + outer/inner mapping + metrics + idempotencia + nem-mfg skip + pipeline flow | smoke PASS |
| #10 Checklist es report evidence-alapon ki van toltve | PASS | jelen report + checklist | Evidence matrix es AUTO_VERIFY blokk kitoltve | verify.sh PASS |
| #11 `verify.sh --report ...` PASS | PASS | AUTO_VERIFY blokk fentebb | check.sh exit code 0, teljes smoke suite zold | verify.sh |

## 6) Advisory notes (nem blokkolo)
- A `dxf_geometry_import.py` pipeline classification hivasa `try/except` blokkban fut, igy a classification hibaja nem torik el a fajlimport flow-t. Ez szandekos: a classification truth opcionalis reteg az import pipeline szempontjabol.
- A H2-E2-T1 smoke a pipeline-hivasban egy warning logot ad, mert a FakeSupabaseClient nem ismeri a `geometry_contour_classes` tablat — ez helyes mukodes, a pipeline kezeli.
- A `_compute_area` es `_compute_perimeter` fuggvenyek a contour `points` listabol szamolnak, nem zarjak explicit a ringet (a shoelace formula modulo indexelessal mukodik). Ez a manufacturing_canonical payload konvenciojara epit, ahol a points lista nyilt vagy zart ring lehet.
- A `feature_class` kezdetben `default` — a kesobbi H2-E3 cut rule rendszer fog ezen finomitani.

## 7) Follow-ups (opcionalis)
- H2-E3 cut rule set es contour rule rendszer bevezetese, amely a classification truth-ra epit.
- Feature class finomitasa heurisztikakkal (pl. area/perimeter arany alapu micro_inner, slot detektalas).
- Contour classification API endpoint (jelenleg csak pipeline-alap, nincs kulon route).
- Manufacturing snapshot bovitese contour classification referenciaval.
