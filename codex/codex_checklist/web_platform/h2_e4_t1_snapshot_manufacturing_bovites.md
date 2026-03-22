# Codex checklist - h2_e4_t1_snapshot_manufacturing_bovites

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a migracio: `supabase/migrations/20260322020000_h2_e4_t1_snapshot_manufacturing_bovites.sql`
- [x] A `nesting_run_snapshots` tablaban megjelenik `includes_manufacturing` es `includes_postprocess`
- [x] A `run_snapshot_builder.py` valos manufacturing manifestet ad vissza selection eseten
- [x] Selection hianya eseten a builder tovabbra is mukodik, tiszta placeholder allapottal
- [x] `includes_manufacturing` korrektul jelzi a selection jelenletet
- [x] `includes_postprocess` explicit false marad
- [x] A snapshot hash valtozik, ha a manufacturing selection valtozik
- [x] A task nem nyitja ki a resolver / plan builder / postprocessor domain scope-ot
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py`
- [x] `python3 -m py_compile api/services/run_snapshot_builder.py api/services/run_creation.py scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py` PASS
- [x] `python3 scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py` PASS (128/128)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t1_snapshot_manufacturing_bovites.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
