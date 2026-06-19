# Q54D Codex Checklist

Task: `sgh_q54d_freespace_band_insert`
Canvas: `canvases/egyedi_solver/sgh_q54d_freespace_band_insert.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54d_freespace_band_insert.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md`

## DoD

- [x] Repo szabályfájlok + Q54A-C előzmények + a felhasználói free-space stratégia rögzítve a reportban.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült; a free-space score csak rangsoroló proxy.
- [x] Nincs NFP, nincs bbox collision shortcut (clearance-hez), nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült.
- [x] Nincs part-id hack, nincs hardcoded 3+3, nincs darabszám-előrejelzés a sheet-close guardban.
- [x] Task-specifikus unit tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a free-space döntést és a band-insertet.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] Free-space proxy: nagy összefüggő sáv > sok apró rés (azonos terület mellett).
- [x] Naiv elhelyezés elrontja a 3. critical helyét; free-space score-ral marad edge-connected sáv →
      band-insert sikeres.
- [x] Sheet-close guard nem zár, amíg alkalmas nagy szabad régió van; zár, ha nincs.
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md`
