# Q54D Codex Checklist

Task: `sgh_q54d_freespace_band_insert`
Canvas: `canvases/egyedi_solver/sgh_q54d_freespace_band_insert.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54d_freespace_band_insert.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md`

## DoD

- [ ] Repo szabályfájlok + Q54A-C előzmények + a felhasználói free-space stratégia rögzítve a reportban.
- [ ] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [ ] CDE final validation semantics nem gyengült; a free-space score csak rangsoroló proxy.
- [ ] Nincs NFP, nincs bbox collision shortcut (clearance-hez), nincs cavity/hole fősolver logika.
- [ ] Continuous rotation guardrail nem sérült.
- [ ] Nincs part-id hack, nincs hardcoded 3+3, nincs darabszám-előrejelzés a sheet-close guardban.
- [ ] Task-specifikus unit tesztek elkészültek.
- [ ] Diagnosztika/report bizonyítja a free-space döntést és a band-insertet.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md` lefutott.
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [ ] Free-space proxy: nagy összefüggő sáv > sok apró rés (azonos terület mellett).
- [ ] Naiv elhelyezés elrontja a 3. critical helyét; free-space score-ral marad edge-connected sáv →
      band-insert sikeres.
- [ ] Sheet-close guard nem zár, amíg alkalmas nagy szabad régió van; zár, ha nincs.
- [ ] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md`
