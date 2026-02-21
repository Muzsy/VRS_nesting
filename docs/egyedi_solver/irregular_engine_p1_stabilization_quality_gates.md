# Canvas: P1 — Stabilizálás + minőségkapuk (determinism, regresszió, DXF edge-case, export szabályok)

## 🎯 Funkció

A P1 célja, hogy a P0 “már fut” állapotból ipari stabilitás legyen:

- DXF import edge-case-ek (ARC/SPLINE, chaining, degenerált geometriák) robusztus kezelése
- Független validator és “safe-side” tolerancia policy
- Nominal-only export fixen, plusz debug-inflated opció
- CI gate: determinisztika + smoke regresszió (ugyanaz az input+seed → azonos output hash)

P1-ben a minőségi kapuk és regressziók fontosabbak, mint a “jobb pack”.

## 🧠 Fejlesztési részletek

### P1-1 — DXF edge-case suite: ARC/SPLINE + chaining + kritikus geometriák

**Leírás**

Épül egy DXF fixture + teszt suite, ami direkt az ipari hibaforrásokat célozza:

- ARC/SPLINE poligonizálás (kontrollált chord error / max segment length)
- chaining hibák (nem zárt kontúr, duplikált/átfedő szakaszok)
- degenerált élek (0 hossz, közel-kolineáris pontok)
- lyukak és szigetek topológia (outer + inner rings)

**Kimenet**

- Fixture DXF-ek repo-ba (külön mappa, pl. fixtures/dxf/edge_cases/*)
- Tesztek: import → nominal normalize → inflate → validate PASS/FAIL elvárt eredménnyel
- Dokumentált poligonizálási policy (tolerancia, outward-approx, stb.)

**DoD**

- Minimum 10–20 célzott DXF fixture
- Minden fixture-re elvárt eredmény rögzítve (PASS / FAIL + error code)
- ARC/SPLINE poligonizálás paraméterezhető és dokumentált

### P1-2 — Validator “split”: független ellenőrző réteg + safe-side policy

**Leírás**

A validátor ne ugyanazt a “shortcutot” használja, mint a solver. P1-ben:

- explicit touching/epsilon szabály (inflated érintés OK, de bizonytalan eset reject)
- külön “narrow-phase” ellenőrzések:
  - out-of-bounds bin polygonra
  - overlap (inflated-inflated)
- diagnosztika: pontos “miért bukott” (bin containment fail, overlap, invalid polygon, stb.)

**Kimenet**

- vrs_nesting/validate/solution_validator.py megerősítése / refactor
- docs/tolerance_policy.md (új) – kőbe vésett tolerancia és touching policy
- Validator output: gépbarát error listák

**DoD**

- Validator képes ugyanazt a run artifactot “cold” módon ellenőrizni
- Közös “policy” dokumentum: SCALE, epsilon, touching, simplify szabályok
- Buktatásoknál konkrét error code és érintett entity (part_id/bin_id) listázva

### P1-3 — Export: nominal-only kötelező + debug inflated layer opció

**Leírás**

A te fix követelményed: solver=inflated, export=nominal. P1-ben ez:

- DXF export mindig nominal kontúrokat ír (CUT_OUTER, CUT_INNER)
- debug módban opcionális: inflated kontúrok külön layeren (pl. DEBUG_INFLATED_OUTER/INNER)
- biztosítani kell, hogy a transform/pivot egységes: ugyanaz a (x,y,rot) működik mindkettőn

**Kimenet**

- vrs_nesting/dxf/exporter.py módosítások (export mód paraméter)
- docs/export_modes.md (új) – nominal vs debug-inflated definíció
- Legalább 1 end-to-end teszt, ami vizuálisan/strukturálisan is ellenőrzi a layer-eket

**DoD**

- Default export: csak nominal layer-ek
- Debug export: nominal + inflated külön layeren
- A DXF-ben a kontúrok ténylegesen látszanak (nem csak furatok) – regresszió teszt

### P1-4 — CI determinism gate: hash-stabil output + smoke regresszió

**Leírás**

Ipari minőséghez determinisztika kell:

- ugyanaz az input + seed + solver_version → azonos output (byte/hash)
- smoke futtatás CI-ben (idő budget)
- fail ha nondeterministic / regresszió

**Kimenet**

- CI workflow frissítés (repo meglévő GitHub Actions / scripts szerint)
- scripts/ci_smoke.sh (ha van scripts struktúra; ha nincs, a meglévő check scriptbe)
- Hash-számítás rögzítése (canonical JSON: kulcs rendezés, float tiltás, stb.)

**DoD**

- CI-ben legalább 1 fixture run + validator run
- Hash összehasonlítás PASS
- Nondeterminism = FAIL, logolva (seed, diff, artifact paths)

### P1-5 — Performance baseline: geometry time share + cache hit-rate metrikák

**Leírás**

Nem optimalizálás, hanem mérhetőség:

- mennyi idő megy import/offset/feasibility/search/export fázisokra
- cache hit-rate (rotated polygon cache, broad-phase találati arány)
- ezek bekerülnek a run artifact meta részébe

**Kimenet**

- Profil metrikák a run artifactba
- docs/perf_baseline.md (új) – célértékek és mérési módszer

**DoD**

- Run artifact tartalmaz egyszerű timing breakdown-ot
- Cache hit-rate logolva
- Legalább 1 baseline mérés rögzítve

## ✅ P1 Pipálható ellenőrzőlista

### P1-1 DXF edge-case suite

- Fixture mappa létrehozva és feltöltve (10–20 DXF)
- ARC/SPLINE poligonizálás policy dokumentálva (chord error / max segment)
- Chaining/degenerált esetekhez elvárt PASS/FAIL + error code rögzítve
- Import→inflate→validate regressziós tesztek futnak

### P1-2 Független validator + tolerancia policy

- docs/tolerance_policy.md elkészült (SCALE/epsilon/touching)
- Validator “cold” módban validál run artifactot
- Overlap és containment ellenőrzések safe-side szerint
- Hibákhoz részletes diagnosztika (part_id/bin_id, ok)

### P1-3 Nominal export + debug inflated mód

- Default export csak nominal (CUT_OUTER, CUT_INNER)
- Debug export: inflated kontúrok külön layeren
- Transform/pivot konzisztencia tesztelve
- “Kontúr nem látszik” jellegű regresszió teszt bekerült

### P1-4 CI determinism gate + smoke

- CI futtat 1+ smoke end-to-end run-t
- Canonical JSON hash összehasonlítás PASS
- Validator fut CI-ben a generált artifacton
- Nondeterminism/regr.: FAIL + log

### P1-5 Performance baseline metrikák

- Timing breakdown bekerült a run artifact meta részébe
- Cache hit-rate bekerült
- docs/perf_baseline.md célértékekkel elkészült
- 1 baseline mérés rögzítve (fixture + gép)

## 🧪 Tesztállapot

P1 PASS kritérium:

- DXF edge-case suite fut és stabil,
- CI determinism gate zöld,
- export nominal-only alapértelmezett és a kontúrok látszanak,
- validator safe-side policy szerint megbízhatóan fogja a hibákat.

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- P0 truth layer canvas (előző)
- docs/solver_io_contract_v2.md
- docs/dxf_project_schema_v2.md
- vrs_nesting/dxf/importer.py
- vrs_nesting/dxf/exporter.py
- vrs_nesting/validate/solution_validator.py
- (új) docs/tolerance_policy.md, docs/export_modes.md, docs/perf_baseline.md
- CI workflow / scripts (repo meglévő struktúrája szerint)
