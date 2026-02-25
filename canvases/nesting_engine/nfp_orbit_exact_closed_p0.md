# canvases/nesting_engine/nfp_orbit_exact_closed_p0.md

> **TASK_SLUG:** `nfp_orbit_exact_closed_p0`  
> **AREA:** `nesting_engine`

## 🎯 Funkció

A jelenlegi F2-2 állapotban az **ExactOrbit** mód minőségi résen van: a regressziós elvárás szerint **legalább 3** `prefer_exact: true` konkáv fixture-nek **`ExactClosed`** outcome-ot kell adnia (no-fallback módban), de ez nem teljesül.

A feladat célja:
1) **ExactOrbit** mód stabilizálása úgy, hogy **≥3 prefer_exact fixture**:
   - `enable_fallback=false` mellett **nem** hibázik, és
   - outcome = **`ExactClosed`**,
   - és a teszt **bizonyítja**, hogy ez **nem stable baseline** (canonical ring összevetéssel, vagy explicit allow flaggel).
2) A “silent fallback” tiltás elve **nem sérülhet**: no-fallback módban orbit fail → **Err**, nem “Ok(stable seed)”.

Nem cél:
- a teljes F2-2 újranyitása,
- a stable baseline (Minkowski+dekompozíció+union) módosítása,
- holes támogatás bevezetése (külön P0),
- új dependency hozzáadása (Rust/Python).

## 🧠 Fejlesztési részletek

### Kötelező horgonyok
- Backlog/kontextus:
  - `canvases/nesting_engine/nesting_engine_backlog.md` (F2-2 DoD)
  - `canvases/nesting_engine/nfp_computation_concave.md`
- Orbit next-event:
  - `canvases/nesting_engine/nfp_concave_orbit_next_event.md`
- No silent fallback:
  - `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
- Kód:
  - `rust/nesting_engine/src/nfp/concave.rs`
  - `rust/nesting_engine/src/nfp/mod.rs`
  - `rust/nesting_engine/src/nfp/boundary_clean.rs`
- Regresszió:
  - `poc/nfp_regression/*.json`
  - `rust/nesting_engine/tests/nfp_regression.rs`
  - `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs` (ha létezik)

Ha bármelyik nem létezik: **NINCS** jelzéssel, konkrét útvonallal.

### Minőségi rés leírása (mit kell bezárni)
- Jelenleg a prefer_exact fixture-ök közül kevesebb, mint 3 ad `ExactClosed`-ot (no-fallback módban).
- Tipikus okok (kódból/trace-ből bizonyítandó):
  - `next_event_translation` nem talál érvényes t-t (dead-end),
  - loop / visited ismétlődés,
  - “event jelölt kiesik” valamilyen integritási feltétel miatt,
  - túl agresszív tie-break → rossz irány → gyors dead-end.

### Kötelező megkötések
- **Determinista tie-break** nem lazulhat.
- **i128** minden orientáció/cross/dot döntésnél.
- **f64 PIP** továbbra is tiltott core döntésekben.
- **boundary_clean** a kimenet végén kötelező.
- **enable_fallback=false** esetén nincs “kibúvó”: ha nem zárható → Err.

### Megoldási stratégia (elvárás)
1) **Objektív diagnózis**:
   - azonosítsd, mely prefer_exact fixture-ek buknak, és miért (konkrét outcome/reason).
   - ha van trace smoke: használd; ha nincs, minimal debug collector csak tesztből hívható.
2) **Célzott algoritmus javítás** (minimum invazív):
   - candidate irányok generálása/tie-break finomítása a touching group esetekre,
   - next-event jelöltek generálásának bővítése (pl. edge-edge collinear határ, vertex-vertex események, ha hiányoznak),
   - loop-kerülő lépés: determinisztikus alternatív irányválasztás, ha az első irány dead-end,
   - max_steps/visited signature: csak akkor jelentsen loopot, amikor tényleg ugyanabban a topológiai állapotban vagyunk.
3) **Reális DoD**:
   - legalább **3** prefer_exact fixture legyen `ExactClosed`, és ezt a teszt bizonyítsa.
   - a többi maradhat stable-only vagy error, de prefer_exact jelzővel nem.

### Érintett fájlok

**Módosul:**
- `rust/nesting_engine/src/nfp/concave.rs` (ExactOrbit hardening)
- `rust/nesting_engine/tests/nfp_regression.rs` (prefer_exact elvárás: ≥3 ExactClosed)
- `poc/nfp_regression/*.json` (legalább 3 prefer_exact fixture beállítása “ExactClosed elvárásra”)

**Új:**
- `codex/codex_checklist/nesting_engine/nfp_orbit_exact_closed_p0.md`
- `codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md`
- `codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.verify.log`

## 🧪 Tesztállapot

### DoD
- [x] `cargo test -q nfp_regression` PASS
- [x] **≥3** fixture, ahol `prefer_exact: true` és:
  - `enable_fallback=false` mellett outcome = `ExactClosed`
  - és a teszt bizonyítja: `exact != stable` canonical ring alapon (vagy explicit `allow_exact_equals_stable=true` csak indokolt esetben)
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` PASS

### Evidence
- Reportban táblázat: fixture → prefer_exact → expected outcome → tényleges outcome → steps/events (ha elérhető)

### Célzott ExactClosed fixture-ek
- `poc/nfp_regression/concave_touching_group.json`
- `poc/nfp_regression/concave_interlock_c.json`
- `poc/nfp_regression/concave_multi_contact.json`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások
- F2-2 audit: `codex/reports/nesting_engine/f2_2_full_audit.md` (P0-2 gap)
- Orbit spec/trace: `docs/nesting_engine/orbit_next_event_spec.md` (ha létezik)
- Orbit trace smoke: `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs` (ha létezik)
