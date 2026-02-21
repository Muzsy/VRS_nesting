# Canvas: P2 — Minőségjavítás (compaction, part-in-part, remnant scoring, okos rotáció)

## 🎯 Funkció

A P2 célja, hogy a P1-ben stabilizált, determinisztikus motor minőségben nagyot ugorjon:

- Compaction: ugyanannyi bin/sheet mellett jobb kihasználtság, kevesebb “lyuk”
- Part-in-part: kis alkatrészek lyukakba/üregekbe rakása ipari módon
- Remnant scoring: maradékok értékelése és tudatos megőrzése (későbbi készletgazdálkodás alap)
- Okos rotáció jelöltek: 1° rács marad, de ne bruteforce legyen mindenhol

P2-ben még mindig: feasibility 0 hiba, determinisztika megtartása (P1 kapuk nem lazulnak).

## 🧠 Fejlesztési részletek

### P2-1 — Compaction v1: lokális “slide / push / nudge” javító lépések

**Leírás**

A baseline placer után (P0/P1) fut egy determinisztikus compaction modul, ami:

- alkatrészeket x/y irányban csúsztat a legközelebbi ütközésig (inflated alapján),
- cél: üres területek csökkentése, “balra-le” tömörítés (vagy választott irány policy),
- opcionálisan: egyszerű swap/move próbák (kismértékű lokális keresés).

**Kimenet**

- Compaction modul a solverben (Rust oldalon javasolt)
- Metrikák: compaction előtte/utána (bin count, remnant score, area utilization proxy)

**DoD**

- Ugyanarra az input+seed-re determinisztikus
- Legalább X% átlagos javulás az “üres terület” proxyban (fixture készleten mérve)
- Validator PASS (0 overlap / 0 out-of-bounds)

### P2-2 — Part-in-part pipeline v1: jelölt generálás nominalból, validálás inflated-del

**Leírás**

Part-in-part ipari módon:

- jelöltek generálása a nominal lyukak/üregek alapján (hogy az offsetelt lyuk “eltűnése” ne ölje meg a lehetőséget),
- a tényleges behelyezhetőség/ütközés ellenőrzése inflated geometriával (safe),
- placement heurisztika: “hole-first” – kis alkatrészeket előbb próbál a lyukakba.

**Kimenet**

- Hole index / candidate generator
- Search integráció: hole-first lépés + fallback normál placementre
- Diagnosztika: part-in-part találatok száma, sikerráta

**DoD**

- Legalább 1 fixture, ahol part-in-part demonstrálhatóan javít (kevesebb bin vagy jobb remnant)
- Collapsed hole eset kezelve (jelöltből kizárás vagy “nominal-only hint”)
- Determinisztikus és validator PASS

### P2-3 — Remnant value model v1: “értékes maradék” mérőszám + policy

**Leírás**

Megszületik a maradékok értékelése (nem csak area):

- Area (nyers)
- Hasznosság proxy:
  - kompaktság (pl. area / bbox area)
  - min szélesség / “thin sliver” büntetés
  - egyszerű “inscribed rectangle” proxy (ha van)

Cél: min bin count után a kereső preferálja a jobb maradékot.

**Kimenet**

- Remnant scoring definíció docs-ban + implementáció metrics modulban
- Search hook: döntésekben figyelembe veszi (lexikografikus P2 cél)

**DoD**

- Remnant score definíció dokumentált, fix (verziózott)
- Fixture készleten mérhetően jobb maradékokat hagy (azonos bin count mellett)
- Run artifactba bekerül a remnant score bontás

### P2-4 — Okos rotáció jelöltek: adaptív szűkítés + lokális sűrítés

**Leírás**

A 1° diszkrét rotáció megmarad, de:

- ne próbáljon minden part minden bin minden pozícióján 360 szöget
- legyen:
  - alap jelölt halmaz (pl. 0..359 step=1)
  - szűrés gyors heurisztikákkal (bbox fit, “edge alignment” jelöltek)
  - lokális sűrítés (±k°) ott, ahol javulás várható

**Kimenet**

- Rotáció candidate generator modul
- Perf metrikák: tried_rotations_count, prune_rate

**DoD**

- Azonos minőség mellett futásidő csökken (vagy minőség javul azonos időben)
- Determinisztikus candidate lista (seed/policy alapján)
- Validator PASS

### P2-5 — Local search v1 (LNS-lite / tabu-lite): “javító” operátorok

**Leírás**

P2 végén jön egy könnyű metaheurisztika réteg:

- “kiveszek N alkatrészt → újrapakolom” (ruin & recreate)
- “swap két alkatrészt / rotációt változtatok”
- acceptance: lexikografikus objective szerint

**Kimenet**

- Search operátorok modul (determinista seedelt)
- Stop criteria (iter limit, time budget)

**DoD**

- Fixture készleten javul a remnant score / utilization proxy bin count megtartásával
- Determinisztikus (azonos seed → azonos eredmény)
- Perf budget és log metrikák run artifactban

## ✅ P2 Pipálható ellenőrzőlista

### P2-1 Compaction v1

- Slide/push compaction implementálva (inflated alapján)
- Előtte/utána metrikák a run artifactban
- Determinisztikus (seed/policy)
- Validator PASS minden fixture-n
- Mérhető minőségjavulás (proxy) dokumentálva

### P2-2 Part-in-part v1

- Nominal hole index / candidate generator elkészült
- Hole-first placement integrálva
- Inflated-del validált behelyezés
- Collapsed hole eset kezelve
- Legalább 1 fixture bizonyítja a nyereséget

### P2-3 Remnant value model v1

- Remnant score definíció dokumentálva (verziózva)
- Score számítás implementálva
- Search döntésekben bekötve (lexikografikus cél)
- Run artifactban score bontás szerepel
- Fixture-k alapján “jobb maradék” mérhető

### P2-4 Okos rotáció jelöltek

- Candidate generator elkészült (szűrés + lokális sűrítés)
- Tried rotations szám és prune rate logolva
- Perf vagy minőség javulás mérhető
- Determinisztikus candidate lista
- Validator PASS

### P2-5 Local search v1

- Ruin & recreate operátor elkészült
- Swap/rotate operátor elkészült
- Stop criteria + time budget implementálva
- Objective szerinti acceptance korrekt
- Fixture-k alapján javulás mérhető + determinisztikus

## 🧪 Tesztállapot

P2 PASS kritérium:

- P1 gate-ek (determinism, validator, export) továbbra is zöldek,
- compaction + part-in-part + remnant scoring mérhetően javít,
- futásidő nem romlik kontrollálatlanul (profil metrikák).

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- P1 stabilizálás canvas
- docs/solver_io_contract_v2.md
- docs/tolerance_policy.md
- docs/perf_baseline.md
- Run artifact meta (objective + timing + cache stats)
