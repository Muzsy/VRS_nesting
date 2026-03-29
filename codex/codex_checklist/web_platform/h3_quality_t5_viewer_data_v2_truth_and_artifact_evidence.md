# Codex checklist - h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A `viewer-data` endpoint deterministic input/output artifact truth valasztast kapott (`engine_meta` preferencia + stabil fallback)
- [x] A solver input parse helper reteg v1+v2 kompatibilis (`stocks[]` + `sheet.width_mm/height_mm`, illetve part bbox)
- [x] A raw output parse helper reteg v1+v2 kompatibilis (`solver_output.json` + `nesting_output.json`)
- [x] A `ViewerDataResponse` additive optional evidence mezokkel bovult (`engine_*`, input/output artifact source)
- [x] A snapshot fallback (`solver_input_snapshot.json`) viselkedes megmaradt
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py`
- [x] `python3 -m py_compile api/routes/runs.py scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
