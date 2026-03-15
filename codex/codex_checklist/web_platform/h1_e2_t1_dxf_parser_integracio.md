# Codex checklist - h1_e2_t1_dxf_parser_integracio

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A parser utófeldolgozás a meglévő `vrs_nesting.dxf.importer.import_part_raw` logikára épül
- [x] Sikeres parse esetén létrejön `app.geometry_revisions` rekord a source file-hoz kötve
- [x] A rekord `geometry_role='part'` és `status='parsed'` értékkel jön létre
- [x] A rekord `revision_no` értéke source file-onként konzisztensen képződik
- [x] A rekord `canonical_geometry_jsonb` mezője determinisztikus minimum geometry payloadot tartalmaz
- [x] A rekord `canonical_hash_sha256` mezője a canonical payloadból szerveroldalon képződik
- [x] A rekord `source_hash_sha256` mezője a `file_objects.sha256` truth-ra ül
- [x] A rekord `bbox_jsonb` mezője a parse-olt geometriából képződik
- [x] Sikertelen object letöltés vagy parse hiba esetén nem jön létre hamis `parsed` geometry revision rekord
- [x] Letrejott a task-specifikus smoke script: `scripts/smoke_h1_e2_t1_dxf_parser_integracio.py`
- [x] Smoke script futtatva: `python3 scripts/smoke_h1_e2_t1_dxf_parser_integracio.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
