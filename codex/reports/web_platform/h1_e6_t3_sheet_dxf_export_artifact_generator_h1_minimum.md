PASS

## 1) Meta
- Task slug: `h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.yaml`
- Futas datuma: `2026-03-20`
- Branch / commit: `main @ 343fd79 (dirty working tree)`
- Fokusz terulet: `Worker sheet DXF generator boundary + export artifact persistence`

## 2) Scope

### 2.1 Cel
- Worker-oldali, explicit sheet DXF generator boundary bevezetese projection truth folott.
- Per hasznalt sheet deterministic, basic-visszaolvashato DXF artifact generalas.
- `nesting_canonical` derivative-alapu geometriarajz placement transzformacioval.
- Worker lifecycle bovitese: `replace_projection -> sheet_svg -> sheet_dxf -> done`.
- Task-specifikus smoke a sikeres + hibas export agakra.

### 2.2 Nem-cel (explicit)
- `bundle_zip` workflow, manufacturing canonical, machine-program export.
- Nagy route/API redesign vagy frontend redesign.
- Eredeti DXF entitasok teljes megoerzese.
- Uj DB schema/enum/tablamodositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum/run.md`
- `worker/main.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`
- `codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md`

### 3.2 Mi valtozott es miert
- `worker/sheet_dxf_artifacts.py`: kulon boundary keszult a projection+snapshot+`nesting_canonical` alapu DXF exportra, deterministic filename/storage/meta policyval.
- `worker/main.py`: bekerult a `nesting_canonical` derivative fetch, majd a sheet DXF artifact persistence a sheet SVG utan es a `done` zaras ele.
- `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`: fake gateway-vel bizonyitja a success + deterministic rerun + hibaagakat, valamint basic DXF visszaolvasast.

### 3.3 Export input truth
- Export input: worker projection (`projection.sheets`, `projection.placements`) + snapshot (`parts_manifest_jsonb.source_geometry_revision_id`) + DB-bol feloldott `nesting_canonical` derivative payload.
- Nem raw `solver_output.json` parserbol keszul a geometry.

### 3.4 Determinizmus / retry-biztossag
- Placement es sheet feldolgozas rendezett sorrendben tortenik.
- DXF payload stabil formatumon keszul (`LWPOLYLINE`, fix decimal format).
- Storage path hash: `sha256(filename + "\n" + content_sha256)`.
- Azonos bemenetre azonos payload/storage/meta kimenet.

### 3.5 Route kompatibilitas
- Artifact kind: `sheet_dxf`.
- Metadata: `filename` (`out/sheet_XXX.dxf`) + `sheet_index` + `legacy_artifact_type=sheet_dxf`.
- A kimenet route/artifact-lista oldalon `.dxf` + `sheet_index` alapon kompatibilis.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit worker-oldali sheet DXF generator helper/boundary. | PASS | `worker/sheet_dxf_artifacts.py:323` | A DXF export boundary kulon modulba kerult. | `py_compile` |
| A generator a projection truth + snapshot geometry/`nesting_canonical` derivative alapjan exportal, nem raw solver outputbol. | PASS | `worker/sheet_dxf_artifacts.py:160`; `worker/main.py:1410` | A geometry feloldas `nesting_canonical` derivative-bol tortenik. | Smoke PASS |
| Per hasznalt sheet legalabb egy deterministic DXF dokumentum generalodik. | PASS | `worker/sheet_dxf_artifacts.py:323`; `worker/sheet_dxf_artifacts.py:124`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:233` | Per sheet egy DXF artifact keszul stabil naminggel. | Smoke deterministic assert |
| A geometriak a `nesting_canonical` derivative-bol rajzolodnak, a placement transzformaciot kovetve. | PASS | `worker/sheet_dxf_artifacts.py:160`; `worker/sheet_dxf_artifacts.py:299`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:301` | `outer_ring` + `hole_rings` transzformalva kerulnek a DXF polylinekba. | Smoke transformed-point assert |
| Az artifactok `sheet_dxf` artifactkent a canonical run-artifacts bucketbe kerulnek. | PASS | `worker/main.py:1413`; `worker/sheet_dxf_artifacts.py:381` | Worker `run-artifacts` bucketbe tolti, `artifact_kind=sheet_dxf` regisztracioval. | Smoke metadata assert |
| A regisztracio route-kompatibilis `filename` + `sheet_index` metadata truth-ot ad. | PASS | `worker/sheet_dxf_artifacts.py:124`; `worker/sheet_dxf_artifacts.py:370`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:281` | `out/sheet_XXX.dxf` + explicit `sheet_index` metadata adodik. | Smoke metadata assert |
| Az upload/regisztracio ugyanarra a sheetre retry-biztos/idempotens replace viselkedest ad. | PASS | `worker/sheet_dxf_artifacts.py:367`; `worker/sheet_dxf_artifacts.py:400`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:252` | Azonos bemenetre azonos payload/storage/meta kimenet. | Smoke rerun assert |
| A worker success path a sheet DXF generator utan zarja `done`-ra a runt. | PASS | `worker/main.py:1410`; `worker/main.py:1427` | DXF export a `complete_run_done_and_dequeue` elott fut. | Diff review |
| A task nem csuszik at bundle/manufacturing vagy nagy frontend/redesign scope-ba. | PASS | `worker/sheet_dxf_artifacts.py:241`; `worker/main.py:1410` | Csak worker export boundary + integracio valtozott. | Diff review |
| Keszul task-specifikus smoke a sikeres es hibas DXF-generator agakra. | PASS | `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:233`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:333`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:355`; `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py:377` | Success + empty-sheet + hianyzo derivative + invalid kapcsolatok fedettek. | Smoke PASS |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md:1`; `codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md:1` | Dokumentacios artefaktok kitoltve. | Dokumentacios ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.verify.log` | A kotelezo gate lefutott, AUTO_VERIFY blokk PASS eredmenyt rogzit. | verify.sh |

## 6) Advisory notes
- A DXF writer H1 minimum szintu exportot ad (`LWPOLYLINE` + egyszeru layer policy), tudatosan nem manufacturing-fidelity cel.
- A task nem vallal bundle/workflow vagy frontend oldali boviteseket; ezek tovabbi taskokban kezelhetok.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-20T22:44:43+01:00 → 2026-03-20T22:48:15+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.verify.log`
- git: `main@6b4dd37`
- módosított fájlok (git status): 4

**git diff --stat**

```text
 ...eet_dxf_export_artifact_generator_h1_minimum.md |  26 +++--
 ...export_artifact_generator_h1_minimum.verify.log |  82 +++++++--------
 ...eet_dxf_export_artifact_generator_h1_minimum.py | 114 +++++++++++++++++++++
 worker/sheet_dxf_artifacts.py                      |  70 ++++++++++++-
 4 files changed, 232 insertions(+), 60 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md
 M codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.verify.log
 M scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py
 M worker/sheet_dxf_artifacts.py
```

<!-- AUTO_VERIFY_END -->
