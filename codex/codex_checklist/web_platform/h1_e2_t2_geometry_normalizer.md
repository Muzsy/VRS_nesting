# Codex checklist - h1_e2_t2_geometry_normalizer

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A geometry import láncban explicit normalizer lépés jött létre a parser fölött
- [x] A normalizer a meglévő `vrs_nesting.dxf.importer.import_part_raw` eredményére épül
- [x] A `geometry_revisions.canonical_geometry_jsonb` determinisztikus normalized payloadot tartalmaz
- [x] A normalized payload explicit `outer_ring` / `hole_rings` szerkezetet és stabil metaadatokat hordoz
- [x] A `canonical_hash_sha256` a normalized payloadból képződik
- [x] A `bbox_jsonb` a normalized geometryval konzisztensen töltődik
- [x] A `canonical_format_version` normalized truth verzióra áll
- [x] Ugyanabból a source DXF-ből ismételt feldolgozásnál konzisztens canonical payload/hash keletkezik
- [x] Parse hiba esetén nem jön létre félrevezető normalized geometry revision rekord
- [x] Készült task-specifikus smoke script: `scripts/smoke_h1_e2_t2_geometry_normalizer.py`
- [x] Smoke script futtatva: `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` PASS
- [x] `python3 -m py_compile api/services/dxf_geometry_import.py api/routes/files.py scripts/smoke_h1_e2_t2_geometry_normalizer.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
