# Codex checklist - h2_e2_t1_manufacturing_canonical_derivative_generation

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a minimalis migration: `supabase/migrations/20260322001000_h2_e2_t1_manufacturing_canonical_derivative_generation.sql`
- [x] `geometry_derivative_generator.py` bovitve a `manufacturing_canonical` derivativevel
- [x] `dxf_geometry_import.py` pipeline automatikusan generalja a manufacturing derivativet valid geometry eseten
- [x] `part_creation.py` frissitve a manufacturing derivative bindingre
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
- [x] `python3 -m py_compile api/services/geometry_derivative_generator.py api/services/dxf_geometry_import.py api/services/part_creation.py scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py` PASS
- [x] `python3 scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py` PASS (6/6 test)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t1_manufacturing_canonical_derivative_generation.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
