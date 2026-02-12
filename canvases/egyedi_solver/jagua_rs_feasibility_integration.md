# jagua-rs integracio geometriai feasibility ellenorzesekhez

## 🎯 Funkcio
A task celja a P0 audit masodik BLOCKER pontjanak javitasa: a Rust solver geometriai feasibility ellenorzeseiben valodi `jagua-rs` hasznalat bevezetese (containment, hole-exclusion, edge metszes ellenorzesek).

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `rust/vrs_solver/Cargo.toml` frissitese pinned `jagua-rs` dependencyvel.
  - `rust/vrs_solver/src/main.rs` feasibility utvonal atallitasa `jagua-rs` geometriara (`Point`, `Edge`, `SPolygon`, `CollidesWith`).
  - Checklist + report artefaktok letrehozasa a taskhoz.
- Nincs benne:
  - Teljes heurisztika-csere vagy uj candidate generator.
  - Python oldali geometriai engine csere.
  - Jagua teljes CDE/layout API bekotese (MVP-ben a solver feasibility reteg a cel).

### Erintett fajlok
- `canvases/egyedi_solver/jagua_rs_feasibility_integration.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_rs_feasibility_integration.yaml`
- `rust/vrs_solver/Cargo.toml`
- `rust/vrs_solver/Cargo.lock`
- `rust/vrs_solver/src/main.rs`
- `codex/codex_checklist/egyedi_solver/jagua_rs_feasibility_integration.md`
- `codex/reports/egyedi_solver/jagua_rs_feasibility_integration.md`

### DoD
- [ ] `rust/vrs_solver/Cargo.toml` pinned `jagua-rs` dependencyt tartalmaz.
- [ ] A feasibility check `jagua-rs` geometriat hasznal (`Point`, `Edge`, `SPolygon`, `CollidesWith`).
- [ ] Shape+holes smoke input mellett a solver/validator gate PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_rs_feasibility_integration.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: f32/f64 konverzio miatti hatarhelyzet eltetes.
- Mitigacio: a megmarado check flow determinisztikus, a boundary esetek a jagua `collides_with` implementaciojara vannak bizva.
- Rollback: dependency + feasibility helper blokk reverzibilis, a korabbi sajat geometriara visszaallithato.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_rs_feasibility_integration.md`
- Task-specifikus ellenorzesek:
  - `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml`
  - `python3 scripts/validate_nesting_solution.py --help`

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p0_audit.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
