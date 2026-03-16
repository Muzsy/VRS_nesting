# Codex checklist - h1_e2_t4_geometry_derivative_generator_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszul explicit geometry derivative generator service a validalt geometry truth folott
- [x] A task a meglévo `app.geometry_derivatives` tablat hasznalja
- [x] Letrejon legalabb a `nesting_canonical` es a `viewer_outline` derivative
- [x] A derivative rekordok `producer_version`, `format_version`, `derivative_jsonb`, `derivative_hash_sha256`, `source_geometry_hash_sha256` mezoit korrektul tolti
- [x] A derivative payloadok determinisztikusak
- [x] Ujrafuttatas eseten a `(geometry_revision_id, derivative_kind)` uniqueness nem torik el
- [x] A geometry import/validation lanc valid geometry eseten automatikusan general derivative-eket
- [x] Rejected geometry eseten nem jon letre derivative rekord
- [x] Parse/import failure eseten tovabbra sem jon letre hamis geometry revision vagy derivative
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
- [x] `python3 -m py_compile api/services/geometry_derivative_generator.py api/services/dxf_geometry_import.py scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
