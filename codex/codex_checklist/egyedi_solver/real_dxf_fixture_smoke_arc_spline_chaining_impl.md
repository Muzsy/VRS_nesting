# Codex checklist - real_dxf_fixture_smoke_arc_spline_chaining_impl

- [x] Canvas scope/DoD pontosítva a pozitiv/negativ DXF fixture ellenorzesekkel (`canvases/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`)
- [x] Valodi `.dxf` fixture keszlet letrehozva (`samples/dxf_demo/*.dxf`) es README frissitve
- [x] Uj smoke script kesz: `scripts/smoke_real_dxf_fixtures.py` (ARC/SPLINE + chaining + negativ kod)
- [x] `scripts/smoke_real_dxf_sparrow_pipeline.py` DXF fixture-re allitva (JSON helyett)
- [x] Gate-be kotve az uj smoke (`scripts/check.sh`)
- [x] Verify wrapper futtatva: `./scripts/verify.sh --report codex/reports/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`
- [x] Kotelezo vegso gate futtatva: `./scripts/check.sh`
