PASS

## 1) Meta
- Task slug: `dxf_prefilter_e1_t6_api_contract_specification`
- Kapcsolodo canvas: `canvases/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t6_api_contract_specification.yaml`
- Futas datuma: `2026-04-19`
- Branch / commit: `main @ 4077c1e (dirty working tree)`
- Fokusz terulet: `Docs`

## 2) Scope

### 2.1 Cel
- Docs-only API contract freeze a DXF prefilter lane E1-T6 feladathoz.
- Current-code route truth es future canonical DXF prefilter HTTP API surface szetvalasztasa.
- Rules profile/version, project selection, preflight run/artifact/review route-csaladok rogzitese a meglevo API mintak alapjan.
- Minimalis request/response/status-code elvek docs-szintu rogzitese implementacio nelkul.

### 2.2 Nem-cel (explicit)
- FastAPI route vagy service implementacio.
- `api/request_models.py` modositas.
- OpenAPI export frissites.
- Auth/RLS policy kidolgozas.
- Frontend hook/service es polling flow implementacio.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`

### 3.2 Miert valtoztak?
- A task celja a DXF prefilter V1 API contract docs-level fagyasztasa volt a mar letezo files/profile/selection/runs route mintakra tamaszkodva.
- A checklist/report bizonyitja, hogy a scope docs-only maradt, route/request-model/OpenAPI implementacio nelkul.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md` -> PASS

### 4.2 Opcionais, feladatfuggo parancsok
- Nincs (docs-only API contract freeze task).

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md` dokumentum. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:1` | A dedikalt T6 API contract dokumentum letrejott. | Doc review |
| A dokumentum explicit kulonvalasztja a current-code route truthot es a future canonical DXF prefilter API contractot. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:15`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:64` | Kulon fejezet rogziti a jelenlegi route truthot es a future canonical API surface-et. | Doc review |
| A dokumentum a rules profile/version route-csaladot a meglevo owner-scoped profile mintakhoz igazitja. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:74`; `api/routes/run_strategy_profiles.py:29`; `api/routes/run_strategy_profiles.py:248`; `api/routes/scoring_profiles.py:29`; `api/routes/scoring_profiles.py:244`; `api/routes/postprocessor_profiles.py:29`; `api/routes/postprocessor_profiles.py:252` | A javasolt `dxf-rules-profiles` route-csalad explicit a mar letezo profile/version CRUD+versions mintat koveti. | Doc review |
| A dokumentum a project-level active rules selectiont kulon route-csaladkent rogziti. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:87`; `api/routes/project_strategy_scoring_selection.py:30`; `api/routes/project_strategy_scoring_selection.py:154`; `api/routes/project_manufacturing_selection.py:22` | A T6 contract kulon `dxf-rules-selection` resourcekent kezeli a projekt-szintu aktiv bindinget, a meglevo selection mintak analogiajara. | Doc review |
| A dokumentum a preflight run / artifact / review action route-csaladot kulon resource-kent kezeli. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:97`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:103`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:109`; `api/routes/files.py:22`; `api/routes/runs.py:591`; `api/routes/runs.py:630`; `api/routes/runs.py:667` | A contract kulon `preflight-runs` resource-csaladot rogzit file/project scopeban, es artifacts/review action endpointokat kulon route-on. | Doc review |
| A dokumentum rogzit minimalis request/response/status-code mintakat docs-szinten, implementacio nelkul. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:118`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:130`; `api/request_models.py:6`; `api/request_models.py:7`; `api/routes/runs.py:684` | A dokumentum leirja a strict request body elvet, response stilusokat es status code mintakat (201/200/204/307) implementacio nelkul. | Doc review |
| A dokumentum explicit anti-scope listat tartalmaz. | PASS | `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:143` | Kulon anti-scope blokk tiltja az implementacios scope creep-et. | Doc review |
| Nem jon letre vagy modosul implementacios route/request-model/OpenAPI/frontend fajl. | PASS | `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t6_api_contract_specification.yaml:27`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:148`; `canvases/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md:185` | Az outputs korlat es a dokumentum anti-scope pontjai biztositanak docs-only valtoztatast; implementacios API fajlok erintetlenek maradtak. | `./scripts/verify.sh --report ...` |

## 6) Kulon kiemelesek (run.md kovetelmenyek)
- A current-code API truth kulon fejezetben rogzult: files ingest, owner-scoped profile/version route-ok, project-level selection route-ok, runs artifact list/url/download (`docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:15`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:19`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:31`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:45`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:53`).
- A future canonical route-csaladok expliciten fel vannak sorolva (`docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:74`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:87`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:97`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:103`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:109`).
- A dokumentum kimondja, hogy auth/RLS, OpenAPI, frontend es route/request-model implementacio nem T6 scope (`docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:8`; `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:143`).
- A dokumentum explicit rogziti, hogy T4 lifecycle es T5 data-model mar fagyasztott szerzodes, T6 csak a HTTP API surface (`docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md:137`).

## 7) Advisory notes
- A preflight `rerun` endpoint extension markerkent szerepel; implementacios kotelezove tetelehez kulon T4/T5 konzisztencia check javasolt az E2/E3 taskokban.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-19T01:07:00+02:00 → 2026-04-19T01:09:51+02:00 (171s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.verify.log`
- git: `main@4077c1e`
- módosított fájlok (git status): 27

**git diff --stat**

```text
 scripts/check.sh                                                          | 0
 scripts/ensure_sparrow.sh                                                 | 0
 scripts/run_real_dxf_sparrow_pipeline.py                                  | 0
 scripts/run_sparrow_smoketest.sh                                          | 0
 scripts/smoke_docs_commands.py                                            | 0
 scripts/smoke_export_original_geometry_block_insert.py                    | 0
 scripts/smoke_export_run_dir_out.py                                       | 0
 ...3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.py | 0
 scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py          | 0
 scripts/smoke_multisheet_wrapper_edge_cases.py                            | 0
 scripts/smoke_nesting_engine_determinism.sh                               | 0
 scripts/smoke_nesting_engine_float_policy_determinism.sh                  | 0
 scripts/smoke_nfp_placer_stats_and_perf_gate.py                           | 0
 scripts/smoke_part_in_part_pipeline.py                                    | 0
 scripts/smoke_real_dxf_fixtures.py                                        | 0
 scripts/smoke_real_dxf_nfp_pairs.py                                       | 0
 scripts/smoke_real_dxf_sparrow_pipeline.py                                | 0
 scripts/smoke_svg_export.py                                               | 0
 scripts/validate_sparrow_io.py                                            | 0
 scripts/verify.sh                                                         | 0
 20 files changed, 0 insertions(+), 0 deletions(-)
```

**git status --porcelain (preview)**

```text
 M scripts/check.sh
 M scripts/ensure_sparrow.sh
 M scripts/run_real_dxf_sparrow_pipeline.py
 M scripts/run_sparrow_smoketest.sh
 M scripts/smoke_docs_commands.py
 M scripts/smoke_export_original_geometry_block_insert.py
 M scripts/smoke_export_run_dir_out.py
 M scripts/smoke_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.py
 M scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py
 M scripts/smoke_multisheet_wrapper_edge_cases.py
 M scripts/smoke_nesting_engine_determinism.sh
 M scripts/smoke_nesting_engine_float_policy_determinism.sh
 M scripts/smoke_nfp_placer_stats_and_perf_gate.py
 M scripts/smoke_part_in_part_pipeline.py
 M scripts/smoke_real_dxf_fixtures.py
 M scripts/smoke_real_dxf_nfp_pairs.py
 M scripts/smoke_real_dxf_sparrow_pipeline.py
 M scripts/smoke_svg_export.py
 M scripts/validate_sparrow_io.py
 M scripts/verify.sh
?? canvases/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t6_api_contract_specification.yaml
?? codex/prompts/web_platform/dxf_prefilter_e1_t6_api_contract_specification/
?? codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md
?? codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.verify.log
?? docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md
```

<!-- AUTO_VERIFY_END -->
