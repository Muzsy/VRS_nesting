PASS

## 1) Meta
- Task slug: `h1_e6_t2_sheet_svg_generator_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t2_sheet_svg_generator_h1_minimum.yaml`
- Futas datuma: `2026-03-20`
- Branch / commit: `main @ 5084611 (dirty working tree)`
- Fokusz terulet: `Worker sheet SVG generator boundary + artifact persistence`

## 2) Scope

### 2.1 Cel
- Worker-oldali, explicit sheet SVG generator boundary bevezetese a projection truth folott.
- Per hasznalt sheet deterministic SVG artifact generalas es canonical storage/regisztracio.
- `viewer_outline` derivative-alapu (hole-kompatibilis) rendereles.
- Worker lifecycle kiegeszitese: `replace_projection -> sheet_svg -> done`.
- Task-specifikus smoke a sikeres + hibas agakra.

### 2.2 Nem-cel (explicit)
- `sheet_dxf`, `bundle_zip`, `machine_program` vagy manufacturing artifact pipeline.
- Nagy `/viewer-data` route redesign.
- Frontend workflow/UI redesign.
- Projection schema bovites vagy uj domain migracio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t2_sheet_svg_generator_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum/run.md`
- `worker/main.py`
- `worker/sheet_svg_artifacts.py`
- `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`
- `codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md`

### 3.2 Mi valtozott es miert
- `worker/sheet_svg_artifacts.py`: kulon boundary a projection+snapshot+`viewer_outline` alapu renderre, deterministic payload/path/metadata policyval.
- `worker/main.py`: bekerult a `viewer_outline` derivative fetch, majd a sheet SVG artifact persistence a `done` zaras ele.
- `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`: fake gateway-vel bizonyitja a sikeragat, determinisztikus rerunt es a hibaagakat.

### 3.3 Render input truth
- A render inputja a worker normalizer projection (`projection.sheets`, `projection.placements`) + snapshot (`parts_manifest_jsonb.source_geometry_revision_id`) + DB-bol feloldott `viewer_outline` derivative payload.

### 3.4 Determinizmus / retry-biztossag
- Az SVG payload stabil sor- es placement-rendben keszul.
- Storage path hash a `filename + content_sha256` kombinaciobol jon.
- Ugyanarra a bemenetre a payload, storage key es metadata kimenet stabil.

### 3.5 Route kompatibilitas
- Artifact kind: `sheet_svg`.
- Metadata: `filename` (`out/sheet_XXX.svg`) + `sheet_index` + `legacy_artifact_type=sheet_svg`.
- Ez kompatibilis a jelenlegi `/viewer-data` route artifact-felismeresevel.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/sheet_svg_artifacts.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit worker-oldali sheet SVG generator helper/boundary. | PASS | `worker/sheet_svg_artifacts.py:286` | Kikulonitett boundary generalja es perzisztalja a sheet SVG artifactokat. | `py_compile` |
| A generator a projection truth + snapshot geometry/viewer derivative alapjan renderel, nem raw solver outputbol. | PASS | `worker/sheet_svg_artifacts.py:176`; `worker/main.py:1527` | A rendereles projection + snapshot + `viewer_outline` payload alapjan tortenik. | Smoke PASS |
| Per hasznalt sheet legalabb egy deterministic SVG dokumentum generalodik. | PASS | `worker/sheet_svg_artifacts.py:286`; `worker/sheet_svg_artifacts.py:323`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:182` | Per sheet index egy SVG keszul, determinisztikus sorrenddel. | Smoke deterministic assert |
| A geometriak a `viewer_outline` derivative-bol rajzolodnak, hole-kompatibilis renderrel. | PASS | `worker/sheet_svg_artifacts.py:176`; `worker/sheet_svg_artifacts.py:279` | `outer_polyline` + `hole_outlines` parse, `fill-rule="evenodd"` render. | Smoke evenodd assert |
| Az artifactok `sheet_svg` artifactkent a canonical run-artifacts bucketbe kerulnek. | PASS | `worker/main.py:1530`; `worker/sheet_svg_artifacts.py:348` | Worker `run-artifacts` bucketet ad at, register `artifact_kind=sheet_svg`. | Smoke gateway asserts |
| A regisztracio route-kompatibilis `filename` + `sheet_index` metadata truth-ot ad. | PASS | `worker/sheet_svg_artifacts.py:142`; `worker/sheet_svg_artifacts.py:333`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:224` | Stabil `out/sheet_XXX.svg` nev + explicit `sheet_index`. | Smoke metadata asserts |
| Az upload/regisztracio ugyanarra a sheetre retry-biztos/idempotens replace viselkedest ad. | PASS | `worker/sheet_svg_artifacts.py:331`; `worker/sheet_svg_artifacts.py:363`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:193` | Azonos bemenetre azonos payload/key/metadata. | Smoke rerun assert |
| A worker success path a sheet SVG generator utan zarja `done`-ra a runt. | PASS | `worker/main.py:1527`; `worker/main.py:1544` | `persist_sheet_svg_artifacts` fut a `complete_run_done_and_dequeue` elott. | Diff review |
| A task nem csuszik at DXF/export/manufacturing vagy nagy frontend/redesign scope-ba. | PASS | `worker/main.py:1527`; `worker/sheet_svg_artifacts.py:286` | Valtozas csak worker SVG artifact boundary + integracio. | Diff review |
| Keszul task-specifikus smoke a sikeres es hibas SVG-generator agakra. | PASS | `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:182`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:246`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:268`; `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py:290` | Success + missing viewer + invalid relation/placement mapping agak fedettek. | Smoke PASS |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md:1`; `codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md:1` | Task dokumentacio kitoltve DoD evidenciakkal. | Dokumentacios ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.verify.log` | A kotelezo gate lefutott, AUTO_VERIFY blokk PASS eredmenyt rogzit. | verify.sh |

## 6) Advisory notes
- A workerben vannak korabbi legacy SVG helper fuggvenyek is, de a canonical T2 path mar az uj `worker/sheet_svg_artifacts.py` boundaryt hasznalja.
- A storage path content-hash alapu; azonos bemenetre stabil, es route-felismeres metadata alapjan valtozatlan.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-20T21:49:25+01:00 → 2026-03-20T21:52:58+01:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.verify.log`
- git: `main@5084611`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 worker/main.py | 71 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 71 insertions(+)
```

**git status --porcelain (preview)**

```text
 M worker/main.py
?? canvases/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e6_t2_sheet_svg_generator_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum/
?? codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md
?? codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.verify.log
?? scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py
?? worker/sheet_svg_artifacts.py
```

<!-- AUTO_VERIFY_END -->
