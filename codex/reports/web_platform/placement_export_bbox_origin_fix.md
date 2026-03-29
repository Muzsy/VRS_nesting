PASS

## 1) Meta
- Task slug: `placement_export_bbox_origin_fix`
- Kapcsolodo canvas: `canvases/web_platform/placement_export_bbox_origin_fix.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_placement_export_bbox_origin_fix.yaml`
- Futas datuma: `2026-03-29`
- Branch / commit: `main @ 6f15fe4 (dirty working tree)`
- Fokusz terulet: `Worker projection + sheet SVG/DXF export placement reference bugfix`

## 2) Scope

### 2.1 Cel
- A placement-reference szemantika harmonizalasa a normalizer, SVG es DXF retegek kozott.
- A `bbox_jsonb` szamitas atalakitasa normalizalt lokalis bbox referencia alapra.
- Determinisztikus out-of-sheet guard bevezetese, hogy ervenytelen projectionnel ne mehessen a run csendben `done` allapotba.
- Regresszio bizonyitas arra, hogy a worker a kapott nem nulla (`180.0`) `rotation_deg` erteket vegigviszi.

### 2.2 Nem-cel (explicit)
- Solver policy atirasa vagy shape-aware rotacio-valaszto logika bevezetese.
- `rust/vrs_solver` heuristikak modositasa.
- Viewer API/front-end redesign.
- H2/H3 feature-bovites.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/placement_export_bbox_origin_fix.md`
- `codex/goals/canvases/web_platform/fill_canvas_placement_export_bbox_origin_fix.yaml`
- `codex/prompts/web_platform/placement_export_bbox_origin_fix/run.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_placement_export_bbox_origin_fix.py`
- `codex/codex_checklist/web_platform/placement_export_bbox_origin_fix.md`
- `codex/reports/web_platform/placement_export_bbox_origin_fix.md`

### 3.2 Mi valtozott es miert
- `worker/result_normalizer.py`: kozos placement transform (`R(local-base)+translation`) bevezetve; a bbox-projekcio mar a normalizalt lokalis (`0..width`, `0..height`) dobozbol szamol.
- `worker/sheet_svg_artifacts.py`: a `viewer_outline` geometriak transzformja bbox-min base offsettel tortenik.
- `worker/sheet_dxf_artifacts.py`: a `nesting_canonical` geometriak ugyanazzal a bbox-min base offsettel transzformalodnak, mint az SVG-ben.
- `worker/main.py`: explicit projection-bound guard hivas (`assert_projection_within_sheet_bounds`) a projection write es `done` zaras elott.
- `scripts/smoke_placement_export_bbox_origin_fix.py`: task-specifikus smoke a negativ lokalis bbox + rotacio + SVG/DXF konzisztencia + guard hibaag igazolasara.

### 3.3 Valodi bugfix vs solver-korlat
- Valodi bugfix: negativ lokalis koordinataju geometriak eseteben a projection/export referencia eltért, emiatt a bbox es vizualis kimenet nem ugyanazt a sheet-beli helyzetet mutatta.
- Solver-korlat (valtozatlan): a `rust/vrs_solver` tovabbra is bbox-alapu kontroll solver; a shape-aware rotation valasztas nem ennek a tasknak a celja.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py scripts/smoke_placement_export_bbox_origin_fix.py` -> PASS
- `python3 scripts/smoke_placement_export_bbox_origin_fix.py` -> PASS
- `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| A worker placement referenciaja (`bbox_min_corner`) explicit es kovetkezetes truth-ra kerul. | PASS | `worker/result_normalizer.py:137`; `worker/sheet_svg_artifacts.py:145`; `worker/sheet_dxf_artifacts.py:129` | Kozos transzform szemantika (`local-base`) mindharom retegben. | Smoke + regresszios smoke PASS |
| A `worker/result_normalizer.py` a projectalt bbox-ot a normalizalt lokalis bbox-bol szamolja. | PASS | `worker/result_normalizer.py:167` | A bbox projekcio mar `0..width` x `0..height` lokalis dobozbol megy. | `smoke_placement_export_bbox_origin_fix.py:227` |
| A `worker/sheet_svg_artifacts.py` a lokalis bbox-min base offsettel, helyesen exportal. | PASS | `worker/sheet_svg_artifacts.py:268`; `worker/sheet_svg_artifacts.py:338` | SVG pontok transzformja bbox-min korrekcioval tortenik. | `smoke_placement_export_bbox_origin_fix.py:252` |
| A `worker/sheet_dxf_artifacts.py` ugyanazzal a placement szemantikaval exportal, mint az SVG. | PASS | `worker/sheet_dxf_artifacts.py:254`; `worker/sheet_dxf_artifacts.py:419` | DXF outer/hole geometriak ugyanazzal a base-offset transzformmal mennek. | `smoke_placement_export_bbox_origin_fix.py:273` |
| A canonical projection es a tenyleges SVG/DXF export ugyanarra a sheet-beli helyzetre mutat. | PASS | `scripts/smoke_placement_export_bbox_origin_fix.py:227`; `scripts/smoke_placement_export_bbox_origin_fix.py:252`; `scripts/smoke_placement_export_bbox_origin_fix.py:273` | A normalizer bbox es a rajzolt/exportalt pontok megegyeznek. | Task smoke PASS |
| A task bevezet determinisztikus out-of-sheet guardot a referenciahiba elfedese ellen. | PASS | `worker/result_normalizer.py:202`; `worker/result_normalizer.py:552`; `worker/main.py:1380` | Kulon projection-bound guard fut worker flow-ban a `done` zaras elott. | `smoke_placement_export_bbox_origin_fix.py:280` |
| A task regressziosan bizonyitja, hogy a worker helyesen alkalmazza a nem nulla `rotation_deg` erteket. | PASS | `scripts/smoke_placement_export_bbox_origin_fix.py:218`; `scripts/smoke_placement_export_bbox_origin_fix.py:252` | `rotation_deg=180.0` atmegy projection + SVG + DXF retegeken. | Task smoke PASS |
| A task explicit kimondja, hogy a shape-aware rotation valasztas tovabbra is out-of-scope, mert a jelenlegi solver bbox-alapu. | PASS | `canvases/web_platform/placement_export_bbox_origin_fix.md:174`; `codex/reports/web_platform/placement_export_bbox_origin_fix.md:41` | A solver policy szandekosan valtozatlan, csak worker-side referencia bugfix tortent. | Canvas + report review |
| Keszul task-specifikus smoke script. | PASS | `scripts/smoke_placement_export_bbox_origin_fix.py:1` | Uj smoke script elkeszult, fake snapshot/derivative/gateway alapon. | Script PASS |
| Checklist es report evidence-alapon frissitve. | PASS | `codex/codex_checklist/web_platform/placement_export_bbox_origin_fix.md:1`; `codex/reports/web_platform/placement_export_bbox_origin_fix.md:1` | Mindket artefakt kitoltve evidence hivatkozasokkal. | Dokumentacios ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md` PASS. | PASS | `codex/reports/web_platform/placement_export_bbox_origin_fix.verify.log` | A kotelezo gate sikeresen lefutott. | verify.sh |

## 6) Advisory notes
- A guard explicit kulon validacios lepeskent kerult be (`assert_projection_within_sheet_bounds`), hogy a worker lifecycle-ben ervenyesuljon, de a korabbi normalizer smoke fixturek kompatibilisek maradjanak.
- A transzform szemantika harmonizacioja nem valtoztat solver-policyt; shape-aware orientacio tovabbra is kulon tema.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-29T11:27:01+02:00 → 2026-03-29T11:30:32+02:00 (211s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/placement_export_bbox_origin_fix.verify.log`
- git: `main@6f15fe4`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 worker/main.py                |   6 ++-
 worker/result_normalizer.py   | 110 +++++++++++++++++++++++++++++++++++++++---
 worker/sheet_dxf_artifacts.py |  93 +++++++++++++++++++++++++++++++----
 worker/sheet_svg_artifacts.py |  87 +++++++++++++++++++++++++++++----
 4 files changed, 269 insertions(+), 27 deletions(-)
```

**git status --porcelain (preview)**

```text
 M worker/main.py
 M worker/result_normalizer.py
 M worker/sheet_dxf_artifacts.py
 M worker/sheet_svg_artifacts.py
?? canvases/web_platform/placement_export_bbox_origin_fix.md
?? codex/codex_checklist/web_platform/placement_export_bbox_origin_fix.md
?? codex/goals/canvases/web_platform/fill_canvas_placement_export_bbox_origin_fix.yaml
?? codex/prompts/web_platform/placement_export_bbox_origin_fix/
?? codex/reports/web_platform/placement_export_bbox_origin_fix.md
?? codex/reports/web_platform/placement_export_bbox_origin_fix.verify.log
?? scripts/smoke_placement_export_bbox_origin_fix.py
```

<!-- AUTO_VERIFY_END -->
