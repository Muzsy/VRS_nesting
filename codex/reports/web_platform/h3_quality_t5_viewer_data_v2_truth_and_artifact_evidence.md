PASS_WITH_NOTES

## 1) Meta
- Task slug: `h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence`
- Kapcsolodo canvas: `canvases/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.yaml`
- Futas datuma: `2026-03-30`
- Branch / commit: `main @ acaff6c (dirty working tree)`
- Fokusz terulet: `API truth/parsing bridge (viewer-data)`

## 2) Scope

### 2.1 Cel
- A `viewer-data` endpoint input truth valasztasa formal `solver_input` artifactot preferaljon, snapshot fallback megtartasaval.
- Az output truth valasztas legyen v1+v2 kompatibilis (`solver_output.json` es `nesting_output.json`), `engine_meta.json` alapjan backend-aware preferenciaval.
- A parser reteg legyen egyszerre v1+v2 kompatibilis inputon es outputon is.
- A response schema additive optional evidence mezoket adjon, backward kompatibilis modon.
- A sheet meretek es sheet metrics v2 runnal se maradjanak uresen, ha input truthbol szamolhatok.
- Keszuljon dedikalt smoke a legacy v1, v2 truth, fallback es determinizmus lefedesere.

### 2.2 Nem-cel (explicit)
- Frontend/UI komponens vagy vizualis rollout.
- Worker runtime vagy result normalizer tovabbi bovitese.
- Benchmark harness UX, quality scoring vagy placement tuning.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `api/routes/runs.py`
- `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py`
- `codex/codex_checklist/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- `codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`

### 3.2 Mi valtozott es miert
- Input/output truth valasztasi szabaly:
  - input: `solver_input` artifact -> `solver_input_snapshot.json` fallback;
  - output: backend-aware kimenet valasztas (`nesting_output` vs `solver_output`) `engine_meta` alapjan, kulonben stabil fallback (filename + artifact_type + rendezett sorrend).
- v1/v2 parse helper reteg:
  - input parse: v1 `width/height` + `stocks[]`, v2 `outer_points_mm` bbox + `sheet.width_mm/height_mm`.
  - output parse: v1 legacy mezok (`instance_id`, `sheet_index`, `x`, `y`) es v2 mezok (`instance`, `sheet`, `x_mm`, `y_mm`) egysegesitett kezelese.
- Optional viewer-data evidence mezok:
  - `engine_backend`, `engine_contract_version`, `engine_profile`,
  - `input_artifact_source`, `output_artifact_filename`, `output_artifact_kind`.
- Backward kompatibilitas:
  - a meglevo `placements[]`/`unplaced[]` es sheet response strukturak megmaradtak;
  - az uj evidence mezok csak optional, additive mezok.
- Tudatos task-scope:
  - a valtozas API truth/parsing bridge szinten maradt, frontend/UI rollout nelkul.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 -m py_compile api/routes/runs.py scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` -> PASS
- `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` -> PASS
- ajanlott regresszio: `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` -> FAIL (nem blokkolo, a smoke fix `"engine_backend": "sparrow_v1"` szovegre ellenoriz, ami a T4 ota backend-aware dinamikus)

### 4.3 Ha valami kimaradt
- Kotelezo ellenorzes nem maradt ki; a repo gate lefutott.
- Az ajanlott T1 regresszio smoke failure-je nem a T5 scope altal bevezetett hiba, hanem egy elavult string-assert a T1 scriptben.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 A `viewer-data` endpoint v1 es v2 raw output truthot is helyesen tud olvasni | PASS | `api/routes/runs.py:829`; `api/routes/runs.py:839`; `api/routes/runs.py:1074` | A kimeneti artifact kivalasztas kezeli a `solver_output.json` es `nesting_output.json` vilagot, backend-aware preferenciaval. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #2 A solver input parse v2 inputnal is ad sheet- es part-meretet a viewer response-hoz | PASS | `api/routes/runs.py:683`; `api/routes/runs.py:901`; `api/routes/runs.py:1119` | A part meret parse v2-ben bbox alapu, a sheet meret parse v2-ben `sheet.width_mm/height_mm` alapjan toltodik. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #3 A response `placements[]` / `unplaced[]` strukturaja backward kompatibilis marad | PASS | `api/routes/runs.py:951`; `api/routes/runs.py:976`; `api/routes/runs.py:1002` | A parser megtartja a legacy v1 mezoket, es ehhez ad v2 mezoforras-kompatibilitast determinisztikus `instance_id` kepzessel. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #4 A `ViewerDataResponse` optional engine/artifact evidence mezokkel bovul | PASS | `api/routes/runs.py:142`; `api/routes/runs.py:1220` | A schema additive optional mezoket kapott, a response-ban csak akkor toltodik, ha van megfelelo evidence. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #5 A formal `solver_input` artifact -> snapshot fallback szabaly tovabbra is mukodik | PASS | `api/routes/runs.py:793`; `api/routes/runs.py:1089`; `api/routes/runs.py:1100` | Eloszor a formal artifact jon, hianyaban aktiv snapshot fallback, es ez explicit source-evidence-kent vissza is jon. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #6 A v1 legacy viewer viselkedes nem torik el | PASS | `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py:95`; `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py:166` | A dedikalt v1 eset tovabbra is helyes placement/sheet parse-t ad es megtartja a legacy instance_id formatumot. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #7 A task-specifikus smoke zold | PASS | `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py:423`; `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py:427` | A smoke egyben lefedi a v1, v2, fallback es determinizmus ellenorzeseket. | `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` |
| #8 A standard verify wrapper lefut, report + log frissul | PASS | `codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.verify.log` | A standard gate wrapper lefutott, a `.verify.log` letrejott, es az AUTO_VERIFY blokk automatikusan frissult. | `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md` |

## 6) Advisory notes
- A T5 parser bridge tudatosan nem nyult frontend render logikahoz; a valtozas teljesen API oldali truth/parsing scope-ban maradt.
- A v2 sheet-size kitoltes alapja tovabbra is input truth; objective `utilization_pct` csak kiegeszito evidence marad.
- Az ajanlott T1 smoke jelenleg elavult string-assertet tartalmaz a T4 ota dynamic `engine_meta` valtozas miatt.

## 7) Follow-ups
- Frissitendo a `smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`, hogy backend-aware engine meta assertet hasznaljon fix string helyett.
- Ha a kliensoldal explicit engine/artifact mezoket jelenitene meg, kulon UI taskban erdemes formalizalni a megjelenitesi policy-t.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-30T00:55:27+02:00 → 2026-03-30T00:59:01+02:00 (214s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.verify.log`
- git: `main@acaff6c`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 api/routes/runs.py | 380 ++++++++++++++++++++++++++++++++++++++++++++---------
 1 file changed, 315 insertions(+), 65 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
A  docs/nesting_quality/nesting_quality_konkret_feladatok.md
?? canvases/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md
?? codex/codex_checklist/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.yaml
?? codex/prompts/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence/
?? codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md
?? codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.verify.log
?? scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py
```

<!-- AUTO_VERIFY_END -->
