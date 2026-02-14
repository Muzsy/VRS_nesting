# dxf_demo fixtures

A real DXF pipeline smoke jelenleg a repo-ban levo minimalis geometria fixture-t hasznalja:

- `samples/dxf_import/part_contract_ok.json`

A `scripts/smoke_real_dxf_sparrow_pipeline.py` futaskor ideiglenes `dxf_v1` project JSON keszul,
amely erre a fixture-re mutat stock es part forraskent is.

Cel: determinisztikus, gyors smoke a teljes `dxf-run` pipeline-ra
(schema parse -> import/polygonize/offset -> sparrow run -> per-sheet DXF export).
