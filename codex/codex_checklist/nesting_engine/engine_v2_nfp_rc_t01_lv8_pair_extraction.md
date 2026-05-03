# Codex checklist - engine_v2_nfp_rc_t01_lv8_pair_extraction

- [x] AGENTS.md + T01 master runner/canvas/YAML/runner prompt beolvasva
- [x] T01 altal eloirt valos repo fajlok beolvasva (LV8 fixture, benchmark minta, export minta, concave/cache/cavity kontextus)
- [x] `scripts/experiments/extract_nfp_pair_fixtures_lv8.py` letrehozva
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` letrehozva
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` letrehozva
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` letrehozva
- [x] `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json` letrehozva
- [x] `python3 scripts/experiments/extract_nfp_pair_fixtures_lv8.py` PASS
- [x] `python3 -c "import ast; ast.parse(open('scripts/experiments/extract_nfp_pair_fixtures_lv8.py').read()); print('syntax OK')"` PASS
- [x] `ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` PASS
- [x] `ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` PASS
- [x] `ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` PASS
- [x] `ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json` PASS
- [x] `python3 -c "import json,pathlib; p=json.loads(pathlib.Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text()); assert p['fixture_version']=='nfp_pair_fixture_v1'; assert len(p['part_a']['points_mm'])>0; assert len(p['part_b']['points_mm'])>0; print('schema OK')"` PASS
- [x] Nincs meglevo production kod modositas (`git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'` -> ures)
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t01_lv8_pair_extraction.md` PASS
