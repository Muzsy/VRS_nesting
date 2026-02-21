# Canvas: P0 — Ipari 2D Irregular Nesting Engine “Truth Layer” (BLOCKER backlog)

## 🎯 Funkció

A P0 célja, hogy létrejöjjön az ipari minőségű “truth layer”:

- kettős geometria (nominal + inflated) kezeléssel,
- determinista (integer) geometriai kernellel,
- feasibility engine-nel,
- és egy baseline placerrel, ami már end-to-end fut: DXF import → inflate+validate → solve → JSON artifact → nominal DXF export.

P0-ban még nem a “világ legjobb” nesting a cél, hanem a hibamentes, determinisztikus, később bővíthető mag.

## 🧠 Fejlesztési részletek

### P0-1 — Contract v2: dual geometry + rotáció + irreguláris bin-ek

**Leírás**

Új IO-szerződés (v2), ami explicit kezeli:

- nominal_geometry vs inflated_geometry (ref-szinten),
- rotation_step_deg (pl. 1°), illetve rotációs policy,
- bin-eket polygonként (stock sheet + remnant egyaránt),
- objective bontást (bins used / remnant score / cut proxy),
- solver meta: solver_version, seed, determinism-hash.

**Kimenet**

- docs/solver_io_contract_v2.md (vagy kiegészítés)
- docs/dxf_project_schema_v2.md (vagy kiegészítés)
- Példa input+output JSON (minimum 1-1)
- Adapter terv: v1 → v2 kompat réteg

**DoD (Definition of Done)**

- V2 schema dokumentált, példákkal.
- V1 futások nem törnek (fallback/adapter).
- Rotáció reprezentáció és pivot policy rögzítve.

### P0-2 — Projekt eleji gép/lemez paraméterek → kerf/spacing → offset_margin

**Leírás**

A projekt indításakor bekért gép + anyag + vastagság adatokból a rendszer:

- meghatározza a kerf értéket (fix vagy lookup stub),
- beállítja az él-él spacing értéket,
- ebből számolja a offset_margin-t (kőbe vésett definícióval).

**Kimenet**

- Runtime paraméterek és project schema bővítése (v2)
- kerf_source jelölése: fixed | lookup_stub
- Egységek és képlet rögzítése a docs-ban

**DoD**

- offset_margin számítás determinisztikus és dokumentált.
- Későbbi gépadatbázis integráció “helye” megvan (interface stub).

### P0-3 — Determinisztikus geometriai kernel Rustban (Clipper2 + scaled i64)

**Leírás**

A shapely/float jellegű geometriát ipari szintre kell emelni:

- belső reprezentáció: skálázott egész (i64),
- műveletek: offset, simplify/clean, intersection, containment,
- determinisztikus output (azonos input → azonos JSON byte-szinten).

**Kimenet**

- Rust modul(ok): geometry_kernel (offset/clean/ops)
- Python → Rust hívás (subprocess/stdio protokoll vagy más meglévő repo mintához igazítva)
- Egységes SCALE policy rögzítve

**DoD**

- Offset működik (outer kifelé, holes befelé) stabilan.
- Clean/simplify után valid polygon invariánsok.
- Determinisztika teszt (azonos input → azonos hash).

### P0-4 — Inflate + Validate “truth layer” (nominal → inflated, diagnosztikával)

**Leírás**

A DXF importált (nominal) geometriából a pipeline:

- normalizál (winding, zárt kontúr, self-intersection kezelés),
- előállítja az inflated geometriát (offset_margin alapján),
- validál mindkettőt:
  - nominal valid gate
  - inflated valid gate
- diagnosztikát ad: HOLE_COLLAPSED, OFFSET_INVALID, SELF_INTERSECT, stb.

**Kimenet**

- Inflated geometriák előállítása a kernelből
- Error code katalógus (docs) + gépbarát diagnosztika a run artifactban

**DoD**

- Invalid part/bin nem mehet solverbe (fail-fast).
- Collapsed hole jelölve (nem feltétlen FAIL, de rögzítve).
- Szabály fix: solver=inflated, export=nominal.

### P0-5 — Feasibility engine MVP (irreguláris bin-ekkel)

**Leírás**

Készül egy “igazsággép”:

- can_place(part_inflated, bin_polygon, transform)
- broad-phase gyors szűrés (AABB + R-tree vagy hasonló),
- narrow-phase pontos ellenőrzés:
  - bin containment (lyukak figyelembe)
  - 0 overlap a már lerakott inflated partokkal

**Kimenet**

- Rust feasibility modul + cache:
  - (part_id, rot) → rotated inflated polygon
- Python oldali adapter, hogy a pipeline ezt tudja hívni

**DoD**

- Validator szerint 0 overlap / 0 out-of-bounds garantált.
- Alap cache működik.
- Determinisztikus döntés “touching policy” szerint (safe-side rögzítve).

### P0-6 — Baseline placer: single-bin → multi-bin (már futó solver mód)

**Leírás**

Egyszerű, determinisztikus konstrukciós placer:

- 1° diszkrét rotációt kezeli,
- first-feasible / BLF-light / CFR-light jellegű elhelyezés,
- először single-bin, majd multi-bin greedy:
  - cél: min bins used (lexikografikus prioritás)
- part-in-part még csak alap szinten (P2-ben lesz erősítve), de P0-ban ne akadályozza.

**Kimenet**

- Új solver mód kapcsoló a pipeline-ban (ne a Sparrow legyen az egyetlen)
- End-to-end run artifact objective mezőkkel

**DoD**

- Legalább 1 valós DXF fixture-rel PASS end-to-end.
- Output JSON tartalmazza: placements + meta (seed, version) + objective mezők.
- Export DXF nominalból korrekt layer-ekkel.

## ✅ P0 Pipálható ellenőrzőlista

### P0-1 Contract v2

- docs/solver_io_contract_v2.md elkészült (dual geometry + rotation + bins polygon)
- docs/dxf_project_schema_v2.md elkészült (machine/material/kerf_source)
- Példa input JSON (v2) + példa output JSON (v2) hozzáadva
- V1 kompat adapter / fallback működik

### P0-2 Kerf/spacing → offset_margin

- Projekt eleji gép/lemez paraméterek beolvasása (v2-ben)
- kerf_source = fixed | lookup_stub támogatott
- offset_margin képlet + egységek dokumentálva és tesztelve

### P0-3 Determinisztikus geometriai kernel

- SCALE policy rögzítve (i64 scaled)
- Offset műveletek stabilak (outer +, holes -)
- Clean/simplify + valid invariánsok
- Determinisztika gate: azonos input → azonos output hash

### P0-4 Inflate + Validate truth layer

- Nominal normalizálás + validálás (fail-fast hibák)
- Inflated generálás a kernelből
- Diagnosztika hibakódokkal (HOLE_COLLAPSED, OFFSET_INVALID, SELF_INTERSECT, …)
- Szabály rögzítve: solver=inflated, export=nominal

### P0-5 Feasibility engine MVP

- can_place(...) implementálva (containment + overlap)
- Broad-phase gyorsítás (AABB/R-tree vagy ekvivalens)
- Cache: (part_id, rot) → polygon
- Validator PASS: 0 overlap / 0 out-of-bounds

### P0-6 Baseline placer + end-to-end

- Konstrukciós placer fut (1° rotációval)
- Multi-bin greedy: min bins used törekvés
- Run artifact: placements + meta (seed, solver_version) + objective mezők
- DXF export nominalból (CUT_OUTER/CUT_INNER) helyes
- Legalább 1 end-to-end smoke PASS (DXF → solve → export)

## 🧪 Tesztállapot

P0 PASS kritérium: egy reprodukálható, determinisztikus end-to-end futás legalább 1 valós DXF fixture-rel, ahol:

- feasibility 100%,
- JSON artifact hash stabil seed mellett,
- DXF export nominal geometriával korrekt.

## 🌍 Lokalizáció

Nem releváns (belső motor + contract).

## 📎 Kapcsolódások

- docs/solver_io_contract.md (v1)
- docs/dxf_project_schema.md (v1)
- vrs_nesting/cli.py, vrs_nesting/pipeline/*
- vrs_nesting/dxf/importer.py, vrs_nesting/dxf/exporter.py
- vrs_nesting/validate/solution_validator.py
- rust/vrs_solver/*
