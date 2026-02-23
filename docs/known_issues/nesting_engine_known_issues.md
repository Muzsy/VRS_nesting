# docs/nesting_engine/known_issues.md

> Élő dokumentum. Az auditok által feltárt, de még nem kezelt problémák
> nyilvántartása. Ez NEM a fejlesztési backlog (`canvases/nesting_engine/
> nesting_engine_backlog.md`), hanem a tech debt és spec drift registry.
>
> Állapotok: OPEN | IN_PROGRESS (task slug) | RESOLVED (task slug, dátum)
> Azonosító-konvenció: KI-NNN (Known Issue, sorszám)

---

## P2 — Közepes prioritás

### KI-001 Irreguláris bin/stock nem megy át end-to-end a v2 solverig
**Állapot:** OPEN  
**Forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `rust/nesting_engine/src/placement/blf.rs`, `docs/nesting_engine/io_contract_v2.md`

A `pipeline.rs` képes irreguláris stockot inverz offsetelni (F1-5 ✓), de a BLF
placer belső rácsgenerálása téglalap bounding-box alapú. Az IO contract `sheet`
objektuma is elsősorban `{width, height}` formátumot használ. Kommunikációs
kockázat: a Fázis 1 azt sugallja, hogy az alakos táblák támogatottak, miközben
a BLF nesting végpont még csak a bbox-ot veszi figyelembe.

**Javasolt DoD:**  
- Az IO contract `sheet` mezője dokumentáltan tartalmaz `outer_points_mm` opciót.  
- A BLF placer dokumentálja, hogy rácsgeneráláshoz a bbox-ot használja, de az
  `i_overlay` narrow-phase a valós poligonra ellenőriz.  
- Teszt: irreguláris stock → a narrow-phase visszautasít olyan elhelyezést, ami
  a bbox-on belül, de a valós kontúron kívül esne.

---

### KI-002 Stock clearance szabály: margin vs. margin+kerf/2
**Állapot:** OPEN  
**Forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `rust/nesting_engine/src/geometry/pipeline.rs`, `docs/nesting_engine/tolerance_policy.md`

A kód `delta_mm = margin_mm + kerf_mm * 0.5` egységesen alkalmaz mind parts,
mind stocks esetén. A táblaszélnél (stock outer kontúr) ez túlzott lehet: ott
nem történik vágás, csak az alkatrész elindulási pozícióját befolyásolja a
margin. Ha a spec mást vár (pl. stock szélnél csak `margin_mm`, alkatrészek
között `margin_mm + kerf/2`), selejtarány-növekedés lehet az eredmény.

**Javasolt DoD:**  
- `tolerance_policy.md` explicit rögzíti a stock outer ágon alkalmazott `delta`
  definícióját és annak gyártástechnológiai indokát.  
- Ha a szabály megváltozik: `pipeline.rs` frissül és regressziós teszt védi.

---

## P3 — Alacsony prioritás (tech debt / dokumentáció)

### KI-003 Seed paraméter a v2 contractban nem hat a BLF keresésre
**Állapot:** OPEN  
**Forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `docs/nesting_engine/io_contract_v2.md`, `rust/nesting_engine/src/placement/blf.rs`

A BLF algoritmus determinisztikus területrendezést alkalmaz (nem RNG-alapú),
a `seed` paraméter értékétől függetlenül azonos kimenet születik. A felhasználó
változtathatja a seed-et, és semmit sem tapasztal.

**Javasolt DoD:**  
- `io_contract_v2.md` a `seed` mezőt "reserved for Phase 2 (NFP/SA)" megjegyzéssel
  dokumentálja; BLF esetén értéke figyelmen kívül marad.

---

### KI-004 tolerance_policy.md és a tényleges HOLE_COLLAPSED kezelés eltér
**Állapot:** OPEN  
**Forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `docs/nesting_engine/tolerance_policy.md`, `rust/nesting_engine/src/geometry/pipeline.rs`

A kód helyesen kezeli az összeomló lyukakat ("outer-only" fallback, diagnosztika),
de a policy dokumentum valószínűleg egy korábbi, szigorúbb állapotot tükröz
(fatal error). A kód jobb a specifikációnál — csak a doksit kell szinkronizálni.

**Javasolt DoD:**  
- `tolerance_policy.md` tartalmazza: `HOLE_COLLAPSED` → "diagnosztika +
  outer-only fallback, usable_for_nesting=false"; `SELF_INTERSECT` → "fatal,
  pipeline reject". Hivatkozik a releváns unit tesztekre.

---

### KI-005 poc/nesting_engine/ alatt illusztrációs placeholder fájlok
**Állapot:** OPEN  
**Forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `poc/nesting_engine/`

Néhány minta fájl "illusztrációs" értékeket tartalmaz, amelyek könnyen
"golden master"-ré válhatnak, miközben nem azok. Teszt szinten félrevezető.

**Javasolt DoD:**  
- Illustratív fájlok átnevezve `*_illustrative.json` névre.  
- Tények által fedett golden output fájlok neve `*_golden.json` vagy
  automatikusan generált.  
- Teszt nem hivatkozik `_illustrative` fájlra assertion forrásként.

---

## Lezárt issue-k (RESOLVED)

*Jelenleg nincs lezárt issue ebben a nyilvántartásban.*

---

## Karbantartási szabály

Amikor egy issue canvas+yaml feladattá válik, az állapota `IN_PROGRESS (task_slug)`-ra
vált. Amikor a task reportja PASS státuszú és a verify.sh gate zöld, az issue
`RESOLVED (task_slug, dátum)`-ra vált, és átkerül a "Lezárt" szekcióba.