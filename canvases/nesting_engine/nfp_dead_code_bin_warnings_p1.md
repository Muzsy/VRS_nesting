# canvases/nesting_engine/nfp_dead_code_bin_warnings_p1.md

> **TASK_SLUG:** `nfp_dead_code_bin_warnings_p1`  
> **AREA:** `nesting_engine`

## 🎯 Funkció

A `rust/nesting_engine` crate **bin target** buildje során a NFP modul(oka)t érintő `dead_code` warningokat meg kell szüntetni úgy, hogy:

- a meglévő funkciók nem sérülnek,
- nem kerül be új dependency,
- a megoldás determinisztikus és karbantartható.

## 🧠 Fejlesztési részletek

### Kötelező horgonyok
- Szabályok: `AGENTS.md`, `docs/codex/*`
- NFP modulok (létező fájlok alapján):
  - `rust/nesting_engine/src/nfp/mod.rs`
  - `rust/nesting_engine/src/nfp/concave.rs`
  - `rust/nesting_engine/src/nfp/convex.rs`
  - `rust/nesting_engine/src/nfp/boundary_clean.rs`
  - `rust/nesting_engine/src/nfp/cache.rs`
- Gate: `scripts/check.sh`, `scripts/verify.sh`

Ha bármelyik hiányzik: **NINCS** jelzéssel dokumentálni (konkrét útvonallal).

### Probléma definíció
A bin target build (pl. `cargo build --release --bin nesting_engine`) során a Rust `dead_code` warningokat ad olyan NFP-s itemekre (fn/struct/enum/const), amelyek:
- csak tesztből vannak használva, vagy
- debug/trace jellegűek, vagy
- régi/átmeneti helper maradt használat nélkül.

### Felderítés: bin build warningok (NFP szűrés)

`cd rust/nesting_engine && cargo build --release --bin nesting_engine` alapján:

| item | típus | fájl:sor | miért unused | státusz |
|---|---|---|---|---|
| `LoopDetected` | enum variant (`OrbitFailureReason`) | `rust/nesting_engine/src/nfp/concave.rs:182` | legacy ág; az aktuális orbit ciklus már transition-tiltás + backtrack útvonalon kezeli a loopokat | javítandó (eltávolítás) |

Megjegyzés: a buildben látható további `dead_code` warningok (`cross_product_i128`, `signed_area2_i128`, `is_ccw`, `is_convex`) a `src/geometry/types.rs` fájlra vonatkoznak, nem NFP modulra.

### Megoldási elvek (nem alkuképes)
1) **Ne blanket `#[allow(dead_code)]` modul-szinten.**  
   Csak célzottan, indokolt helyen, kommenttel.
2) Ha item **csak tesztben kell**: `#[cfg(test)]` vagy `#[cfg(any(test, debug_assertions))]` gate mögé.  
   - `test` → test buildben él
   - `debug_assertions` → debug buildben él (release-ben nem)
3) Ha item **valóban része a runtime API-nak**, de jelenleg nem hívják:  
   - preferált: dokumentáltan eltávolítani vagy áttenni későbbi taskba **(ha a backlog nem igényli)**  
   - ha nem lehet: nagyon célzott `#[allow(dead_code)]` a konkrét itemen, és komment: miért marad.
4) A változtatás **nem módosíthatja** a bin működését (no new side effects).

### DoD
- `cd rust/nesting_engine && cargo build --release --bin nesting_engine` során **NFP modulból származó** `dead_code` warning **nincs**.
- `cd rust/nesting_engine && cargo test` PASS
- `./scripts/check.sh` PASS
- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_dead_code_bin_warnings_p1.md` PASS

## 🧪 Tesztállapot
- A javítás után a build logban nincs NFP-eredetű `dead_code` sor.
- A CI/gate wrapper-ek zöldek.

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- F2-2 stabilitás: a warningok eltüntetése nem “szépítés”, hanem determinisztikus gate-tisztítás.
