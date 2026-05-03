# Engine v2 NFP RC — T02 Geometry Profile Contract

## Cél
Definiálni és dokumentálni az exact / canonical / solver geometry háromszintű contractot.
Ez egy read-only dokumentációs task — nincs Rust kód változás. A contract képezi
T03–T10 minden geometriai döntés referenciaalapját.

## Miért szükséges
A reduced convolution NFP fejlesztés során kritikus, hogy minden réteg (exact gyártási,
canonical cleanup, solver NFP) pontosan definiált legyen. Ha a rétegek közötti határok
elmosódnak — például solver geometry kerül gyártási exportba — az gyártási hibához vezet.
A contract egyértelűen rögzíti, mi módosítható és mi nem.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64, PartGeometry struktúrák
- `rust/nesting_engine/src/geometry/pipeline.rs` — run_inflate_pipeline logika
- `rust/nesting_engine/src/geometry/scale.rs` — i64_to_mm, mm_to_i64, SCALE konstans értéke
- `rust/nesting_engine/src/geometry/float_policy.rs` — GEOM_EPS_MM értéke és használata
- `rust/nesting_engine/src/nfp/mod.rs` — NfpError enum (EmptyPolygon, NotConvex, NotSimpleOutput, OrbitLoopDetected, OrbitDeadEnd, OrbitMaxStepsReached, OrbitNotClosed, DecompositionFailed)
- `rust/nesting_engine/src/nfp/boundary_clean.rs` — clean_polygon_boundary, ring_has_self_intersection

### Létrehozandó:
- `docs/nesting_engine/geometry_preparation_contract_v1.md` — a geometry contract dokumentum

## Nem célok / scope határok
- Nem kell Rust kódot módosítani.
- Nem kell új típusokat definiálni.
- Nem kell Python kódot módosítani.
- Nem kell teszteket futtatni (csak dokumentáció).
- Nem kell a meglévő pipeline-t megváltoztatni.

## Részletes implementációs lépések

### 1. Meglévő kód olvasása és megértése

Olvasd el az érintett Rust fájlokat. Különösen fontos:
- `geometry/types.rs`: Point64 `x: i64, y: i64` — ez az integer robust layer
- `geometry/scale.rs`: SCALE konstans (pl. 1 mm = N internal unit) — rögzítsd a pontos értéket
- `geometry/float_policy.rs`: GEOM_EPS_MM pontos értéke — rögzítsd
- `nfp/boundary_clean.rs`: mit csinál a `clean_polygon_boundary` és mi a `ring_has_self_intersection` feltétele

### 2. Contract dokumentum megírása

A `docs/nesting_engine/geometry_preparation_contract_v1.md` kötelező tartalom:

#### 2.1 Geometry rétegek definíciója

**Exact geometry** (1. réteg):
- Definíció: az eredeti gyártási kontúr, ahogy a DXF-ből érkezik, spline/arc polygonizálás után
- Mikor keletkezik: DXF import pipeline végén
- Módosíthatóság: CSAK tolerancián belüli javítás megengedett (dupla pont eltávolítás, orientáció fix)
- Mit NEM szabad tenni: vertex elhagyás ha az konvexitást/konkavitást változtat, terület csökkentés
- Mire használható: gyártási export, final overlap validáció, boundary checking
- Implementáció: `PartGeometry` struktúra exact mezői

**Canonical clean geometry** (2. réteg):
- Definíció: topológiailag ekvivalens az exact-tal, de degenerate elemektől megszabadítva
- Mikor keletkezik: exact geometriából, `clean_polygon_boundary` hívás után
- Megengedett transzformációk: dupla vertex removal, null edge removal, orientáció normalizálás (outer CCW, holes CW), collinear merge CSAK ha szög < ε
- Tiltott transzformációk: reflex vertex removal, chord error > GEOM_EPS_MM, hole elhagyás
- Mire használható: NFP számítás inputja, konvex dekompozíció inputja
- Invariáns: area(canonical) ≈ area(exact), max_deviation ≤ GEOM_EPS_MM

**Solver/NFP geometry** (3. réteg):
- Definíció: topology-preserving simplification, kifejezetten az NFP számítás gyorsítására
- Mikor keletkezik: canonical clean-ből, explicit simplification pipeline után
- Megengedett transzformációk: Ramer-Douglas-Peucker epsilon-nal, arc re-polygonization kontrollált chord error-ral, agresszívebb collinear merge, minimum edge length enforcement
- Kritikus korlát: max_deviation ≤ solver_eps (pl. 0.5 mm, de ez paraméter)
- Tiltott transzformációk: reflex vertex elvesztése (topológia változás!), hole elhagyás, narrow neck eltűntetése
- Mire NEM használható: gyártási export, boundary violation check, final validáció
- Invariáns: topology_changed = false kötelező

#### 2.2 Integer robust layer

- A `Point64 {x: i64, y: i64}` típus az integer robust layer implementációja
- Skálázás: 1 mm = SCALE internal unit (pontos érték a scale.rs-ből)
- Koordináta tartomány: max sheet méret × SCALE ≤ i64::MAX (overflow védelem)
- Snap tolerance: GEOM_EPS_MM × SCALE (integer snap)
- Minimum edge length: legalább 1 internal unit (= 1/SCALE mm)
- Minimum area threshold: legalább 1 square internal unit
- Overflow check: max_coord_mm × SCALE ≤ 4_611_686_018_427_387_903 (i64::MAX/2, biztonsági határ)

#### 2.3 GEOM_EPS_MM

- Pontos értéke: (a float_policy.rs-ből olvasott érték)
- Mikor érvényes: Euclidean distance alapú összehasonlításoknál float koordinátákban
- Mikor NEM érvényes: integer domain-ben (ott az integer exact arithmetic érvényes, nem epsilon-összehasonlítás)
- Kapcsolat a solver geometry-vel: solver simplification max_deviation ≤ GEOM_EPS_MM × solver_factor

#### 2.4 Simplification safety szabályok

Mindig ellenőrizni kell simplification után:
1. `topology_changed = false` — reflex vertex count változatlan
2. `area_delta_mm2 < threshold` — területveszteség minimális
3. `max_deviation_mm < solver_eps` — maximális eltérés a canonical-tól
4. `hole_count_unchanged` — lyukak száma nem csökkent
5. `narrow_neck_preserved` — szűk átjárók nem tűntek el (key-lock megőrzés)

#### 2.5 Final validation elve

- Minden placement validációt EXACT geometry alapján kell elvégezni
- A solver/NFP geometry alapján elfogadott placement nem minősíthető validnak
- `NfpPlacerStatsV1` overlap count csak exact collision check alapján számolható
- Ha exact és solver geometry conflict van: exact nyeri

#### 2.6 NfpError kontextus

Az NFP számítás az alábbi hibákat adhatja vissza (mod.rs-ből):
- `EmptyPolygon` — üres input, canonical clean-nel kezelendő
- `NotConvex` — nem konvex input a konvex NFP algoritmusnak
- `NotSimpleOutput` — az NFP output önmetsző, cleanup szükséges
- `OrbitLoopDetected`, `OrbitDeadEnd`, `OrbitMaxStepsReached`, `OrbitNotClosed` — az orbit algoritmus megakadt
- `DecompositionFailed` — konvex dekompozíció sikertelen

#### 2.7 Geometry rétegek és a meglévő kód kapcsolata

| Réteg | Rust típus | Rust modul | Használható exportra? |
|-------|-----------|------------|----------------------|
| Exact | PartGeometry (exact mezők) | geometry/types.rs | Igen |
| Canonical | Polygon64 (clean_polygon_boundary után) | nfp/boundary_clean.rs | Nem önmagában |
| Solver | Polygon64 (simplification után) | geometry/pipeline.rs | Tilos |
| Integer robust | Point64 | geometry/types.rs | Igen (scaling-gel) |

### 3. Validálás

```bash
# Dokumentum létezik
ls docs/nesting_engine/geometry_preparation_contract_v1.md

# Kötelező szekciók ellenőrzése
python3 -c "
content = open('docs/nesting_engine/geometry_preparation_contract_v1.md').read()
sections = ['Exact geometry', 'Canonical clean', 'Solver', 'Integer robust', 'GEOM_EPS_MM', 'Simplification safety', 'Final validation']
for s in sections:
    assert s in content, f'MISSING SECTION: {s}'
    print(f'OK: {s}')
"
```

## Adatmodell / contract változások
Nincs production kód változás. Csak `docs/nesting_engine/geometry_preparation_contract_v1.md` keletkezik.

## Backward compatibility
Nincs breaking change. Kizárólag dokumentáció.

## Hibakódok / diagnosztikák
Ha a `geometry/scale.rs`-ből nem olvasható a SCALE konstans értéke:
- `WARN: SCALE constant not found — document as TBD with explicit note`
Ha a `float_policy.rs`-ből nem olvasható a GEOM_EPS_MM:
- `WARN: GEOM_EPS_MM not found — document as TBD with explicit note`

## Tesztelési terv
```bash
# 1. Dokumentum létezik
ls docs/nesting_engine/geometry_preparation_contract_v1.md

# 2. Kötelező kulcsszavak megléte
python3 -c "
content = open('docs/nesting_engine/geometry_preparation_contract_v1.md').read()
required = ['solver geometry', 'exact geometry', 'canonical', 'Point64', 'GEOM_EPS_MM', 'topology_changed', 'gyártási']
for r in required:
    assert r in content, f'HIÁNYZIK: {r}'
print('Minden kulcsszó megtalálható')
"

# 3. Nincs production kód módosítás
git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'
```

## Elfogadási feltételek
- [ ] `docs/nesting_engine/geometry_preparation_contract_v1.md` létezik
- [ ] Mind a 7 kötelező szekció dokumentálva (exact / canonical / solver / integer robust / GEOM_EPS_MM / simplification safety / final validation)
- [ ] Explicit rögzíti: solver geometry ≠ gyártási geometria
- [ ] Explicit rögzíti: Point64 az integer robust layer implementációja a meglévő kódban
- [ ] GEOM_EPS_MM pontos értéke szerepel (vagy explicit TBD, ha nem olvasható)
- [ ] SCALE konstans értéke szerepel (vagy explicit TBD)
- [ ] Nincs production kód változás

## Rollback / safety notes
Ez a task kizárólag `docs/nesting_engine/geometry_preparation_contract_v1.md`-t hozza létre.
Nincs production kód változás, nincs rollback kockázat.

## Dependency
- Nincs blokoló dependency. Párhuzamosan futtatható T01-gyel.
- T03, T05, T06, T07 hivatkoznak erre a contractra.
