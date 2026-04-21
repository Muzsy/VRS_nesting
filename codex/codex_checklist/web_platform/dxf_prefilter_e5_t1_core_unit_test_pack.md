# Codex checklist - dxf_prefilter_e5_t1_core_unit_test_pack

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Új, dedikált cross-module fixture-driven pytest file elkészült (`tests/test_dxf_preflight_core_unit_pack.py`)
- [x] A pack valódi T1->T6 chain helper (`_run_pipeline`) re épül, nem fake-eli a writer/gate réteget
- [x] `pytest.importorskip("ezdxf")` guard explicit módon szerepel (T5/T6 valos ezdxf dependency)
- [x] Minimum V1 scenario-k fedve: simple outer, outer+inner, small gap repair, gap over threshold, duplicate dedupe, ambiguous gap partner, conflicting layer-color role
- [x] Minden scenario állít cross-step invariánsokat (inspect/role/gap/dedupe/writer/gate szinteken)
- [x] Strict vs lenient kimenet különbség explicit módon tesztelve külön test párokkal
- [x] Meglévő T1..T6 réteg-specifikus tesztfájlok nem módosítva, nem törölve
- [x] Nem nyílt E3 runtime/persistence/route scope és nem nyílt E4 UI scope
- [x] Task-specifikus structural smoke elkészült (`scripts/smoke_dxf_prefilter_e5_t1_core_unit_test_pack.py`)
- [x] Kötelező futtatások lefutottak (`py_compile` OK, `pytest` 10 passed, smoke OK)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t1_core_unit_test_pack.md` lefutott és report AUTO_VERIFY frissült (PASS)
