# canvases/nesting_engine/nfp_concave_orbit_next_event.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_concave_orbit_next_event.md`
> **TASK_SLUG:** `nfp_concave_orbit_next_event`
> **Terület (AREA):** `nesting_engine`

---

# F2-2 Hardening — Orbitális “exact” konkáv NFP: next-event sliding + touching group + determinisztika

## 🎯 Funkció

Az F2-2 konkáv NFP **ExactOrbit** módját fel kell emelni “valódi orbitális” szintre:

- **Next-event sliding:** a kiválasztott csúszási iránnyal nem 1 egységet lépünk, hanem **a következő eseményig** (új érintkezés, kontaktváltás, ütközés, “blokkolás”).
- **Touching group kötelező:** többszörös érintkezés (3–4 kontakt) esetén kontaktcsoportból számolunk jelölt vektorokat.
- **Determinista:** ugyanarra a bemenetre bitazonos canonical output (outer CCW + fix start + collinear merge).
- **Loop guard + dead-end:** visited signature + max_steps; dead-end/loop esetén fallback a stabil baseline-ra (de csak akkor).
- **Float tiltás:** core döntésekben nincs f64 és nincs float PIP.

Nem cél:
- Stable baseline mód (az előző P0 már kezelte)
- Holes teljes támogatás (külön P0)
- F2-3/F2-4

---

## 🧠 Fejlesztési részletek

### Kötelező olvasmány / szabályok (prioritás)

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md`
6. `canvases/nesting_engine/nesting_engine_backlog.md` (F2-2 elvárások)
7. `canvases/nesting_engine/nfp_computation_concave.md` (F2-2 canvas)
8. `canvases/nesting_engine/nfp_concave_integer_union.md` (P0 #1 eredmény)
9. `rust/nesting_engine/src/nfp/concave.rs` (ExactOrbit jelenlegi állapot)
10. `rust/nesting_engine/src/nfp/boundary_clean.rs`
11. `rust/nesting_engine/tests/nfp_regression.rs`
12. `poc/nfp_regression/concave_*.json` (boss fight fixture-ek)

Ha bármelyik hiányzik: STOP, pontos fájlútvonallal jelezni.

---

### Kiinduló probléma (jelenlegi ExactOrbit)

A jelenlegi ExactOrbit tipikusan:
- “irányvektor” alapján **egységlépéseket** tesz,
- könnyen ismétel/loopol,
- és a fixture-ek szerint gyakran fallbackel.

Ez nem felel meg az orbitális NFP lényegének.

### Felderítési jegyzet (konkrét kódpontok)

Az implementáció előtti felderítésben a következő pontok lettek azonosítva:

- Az egységlépéses mozgás a `compute_orbit_exact_nfp()` ciklusban történt (`next = current + delta`), ezért nem eseményig léptetett.
- A fallback döntés a `compute_concave_nfp()` exact ágában dőlt el (ExactOrbit hiba -> stable concave path).
- A touching/contact segédfüggvények:
  - `build_touching_group()`
  - `build_candidate_slide_vectors()`
  - `hash_state()`
- A loop guard és dead-end kezelés ugyanabban a fő ciklusban történt, de next-event számítás nélkül.

Az átépítés célja ezért: az egységlépést racionális `t` alapú next-event lépésre cserélni, a touching groupot kontakt-komponens szintre emelni, és a döntési tie-breaket teljesen determinisztikussá tenni.

---

### Kötelező követelmények (nem alkuképes)

1) **Next-event léptetés**
- Egy választott slide irány `v` mellett számolni kell a **maximális t > 0** eltolást úgy, hogy:
  - addig “szabad” (nincs átfedés),
  - és az eltolás végén **esemény történik** (kontakt létrejön/megszűnik, blokkolás).
- A lépés hossza legyen determinisztikus (i64/i128 predikátumok + racionális összehasonlítás).

2) **Touching group**
- Több kontakt esetén kontaktcsoportot kell képezni, és abból jelölt slide irányokat számolni (Burke 2007 + Luo&Rao 2022 szemlélet).

3) **Determinista tie-break**
- Candidate irányok rendezése: stabil sorrend (pl. fél-sík/kvadráns, majd cross/alignment, majd lexikografikus, majd kontakt indexek).
- Esemény t-értékek közül mindig a legkisebb pozitív (következő esemény), stabil tie-breakkel.

4) **i128 minden orientáció/cross döntéshez**
- Nincs i64 szorzásra támaszkodás.

5) **f64 és f64 PIP tiltás**
- Nincs `geo` f64 PIP.
- Ha kell containment check: integer winding/ray-cast Point64-on.

6) **boundary_clean kötelező**
- Kimenet mindig `boundary_clean` után.

---

### Next-event modell (implementálandó minimum)

#### Fogalmak
- A: fix poligon
- B: mozgatott poligon (rögzített rotáció, csak transzláció)
- `p` = B aktuális transzlációja (Point64)

#### Események típusai
- Vertex(B) → Edge(A) érintkezés létrejötte / megszűnése
- Vertex(A) → Edge(B) érintkezés létrejötte / megszűnése
- Collinear overlap határ (párhuzamos élek “ráfutása”)
- Blokkolás: slide irányban nincs pozitív t (dead-end)

#### Számítás (high-level)
- Adott irány `v` mellett keressük a legkisebb pozitív `t`-t, ahol bármely releváns páros “kontaktba ér”:
  - paraméteres 1D projekció: dot((x_B + p) - x_A, n) jellegű feltételek
  - ütközésmentesség: az esemény előtt nincs “strict overlap”
- Gyakorlatban: per edge-pair jelölt t-k gyűjtése, majd minimum kiválasztása.

Megjegyzés: itt nem “tökéletes matematikai bizonyítás” kell, hanem determinisztikus, stabil, és fixture-eket verő implementáció.

---

### Teszt / DoD (ehhez a taskhoz)

- [ ] Az ExactOrbit mód **nem fallbackel** a 5 concave fixture-ből legalább 3-on (target: mind az 5, de minimum 3 bizonyíték)
- [ ] Determinisztika teszt: 2 futás bitazonos canonical ring (exact módon is)
- [ ] Loop guard: nincs végtelen ciklus, max_steps esetén kontrollált fallback
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` PASS

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- F2-2: `canvases/nesting_engine/nfp_computation_concave.md`
- P0 #1: `canvases/nesting_engine/nfp_concave_integer_union.md`
- Kód: `rust/nesting_engine/src/nfp/concave.rs`, `rust/nesting_engine/src/nfp/boundary_clean.rs`
- Fixture: `poc/nfp_regression/concave_*.json`
