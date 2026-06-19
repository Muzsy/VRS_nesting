# Q55C Codex Checklist

Task: `sgh_q55c_band_insert_candidate_generator`
Canvas: `canvases/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55c_band_insert_candidate_generator.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md`

## DoD

- [ ] Repo szabályfájlok + Q54D free-space + Q55A/B elolvasva, reportban rögzítve.
- [ ] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [ ] CDE final validation semantics nem gyengült; a befértetés-proxy csak rangsoroló.
- [ ] Nincs NFP, nincs bbox-corner shortcut primary, nincs cavity/hole fősolver logika.
- [ ] Continuous rotation guardrail nem sérült (band-aligned pozíció continuous refine).
- [ ] Nincs part-id hack, nincs hardcoded 3+3.
- [ ] Task-specifikus unit + LV8 mechanizmus-teszt elkészült.
- [ ] Diagnosztika/report bizonyítja a band-insertet (band_slot_found/can_fit, candidates accepted).
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md` lefutott.
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [ ] Szabad sáv + beférő part → edge-aligned candidate-ek a sáv mentén (nem szomszéd-feature illesztés).
- [ ] A band-aligned candidate refined rotációja continuous (nem snapping).
- [ ] LV8 (a Q55F-fel közös): 6-big spacing 5 → ≥1 sheeten Anchor+Interlock+BandInsert, max_big ≥ 3, CDE-valid.
- [ ] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md`
