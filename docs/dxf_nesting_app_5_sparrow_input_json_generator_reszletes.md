# DXF nesting app – 5) Sparrow input JSON generátor (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
A 4) lépésből kapott `PreparedBin` + `PreparedPart[]` adatokból előállítani a **sparrow futtatásához szükséges input JSON instance-t**, úgy, hogy:
- darabszámok (quantity) kezelve legyenek,
- rotációs szabályok (fixed/step/list) át legyenek fordítva `allowed_orientations` listává,
- a futás paraméterei (time limit, seed, workers) rögzítve legyenek,
- minden run mappában elmentsük az *exact* inputot (reproducibility).

**Megjegyzés:** a `margin` és `spacing` betartását itt nem „distance” mezővel oldjuk, hanem a 4) fázisban végrehajtott **offset/inset** miatt a motor 0-clearance mellett is korrekt lesz.

**Kimenet:**
- `runs/.../artifacts/instance.json`
- opcionálisan `runs/.../artifacts/instance_summary.json` (debug, emberbarát)

---

## 🧠 Fejlesztési részletek

### 5.1. Sparrow instance JSON specifikáció rögzítése (MVP-safe)

**Összefoglaló:**
MVP-ben nem akarunk „formátum-felfedezést” futás közben. Kell egy belső, rögzített mapping a saját modelljeinkből a sparrow JSON struktúrára. Ha később változik a sparrow schema, egy helyen kell módosítani.

**Feladatlista:**
- [ ] Hozz létre egy `core/sparrow_schema_notes.md`-t (belső jegyzet), amiben leírod:
  - milyen mezőket írsz a JSON-ba
  - hogyan néz ki egy bin
  - hogyan néz ki egy item/shape
  - hogyan kezeled a rotációt és a példányosítást
- [ ] Írj egy `SparrowInstance` pydantic modellt (vagy egyszerű dict builder + validátor)
- [ ] Döntsd el: MVP-ben **egy** bin típus van (téglalap) vagy később többféle

**Kimenet:**
- dokumentált, belső „schema contract”

---

### 5.2. Bin (tábla) leképezése: PreparedBin → JSON

**Összefoglaló:**
A sparrow számára a bin a „konténer”. A 4) fázisból a bin már insetelt, tehát a ténylegesen használható területet reprezentálja.

**Feladatlista:**
- [ ] Készíts `build_bin(prepared_bin)` függvényt:
  - név/azonosító (pl. `sheet_bin`)
  - polygon pontlista (outer ring)
  - (ha kell) bbox / width / height meta
- [ ] Validáció:
  - a bin poligon zárt és érvényes
  - area > 0

**Kimenet:**
- JSON bin blokk (stabil és valid)

---

### 5.3. Part geometria leképezése: PreparedPart → JSON shape

**Összefoglaló:**
A sparrow/jagua oldalon a shape tipikusan egy **outer boundary + holes** poligon. A 3) és 4) fázis garantálja, hogy ez érvényes.

**Feladatlista:**
- [ ] Készíts `build_shape(prepared_part)` függvényt:
  - outer ring pontjai
  - holes ringek pontjai
  - (opcionális) meta: bbox, area
- [ ] Koordináta konvenció:
  - a pontok ugyanabban a mm koordinátarendszerben legyenek, mint a bin
  - a part saját origóját ajánlott 0,0 környékére normalizálni (reproducibility + numerikus stabilitás)
- [ ] Validáció:
  - outer pontszám >= 3
  - holes mind >= 3
  - nincs NaN/Inf

**Kimenet:**
- JSON shape blokk

---

### 5.4. Darabszám kezelés (quantity): példányosítás vs natív quantity

**Összefoglaló:**
A darabszám kezelés két módon megoldható:

**A) PÉLDÁNYOSÍTÁS (MVP-ben ez a legbiztosabb):**
- ha egy partból 7 db kell, akkor 7 külön „item instance” jön létre
- előnye: egyszerű, egyértelmű mapping placement → instance
- hátránya: nagyobb JSON (de MVP-ben oké)

**B) NATÍV QUANTITY mező (csak ha biztosan támogatott):**
- egy itemhez quantity érték
- előnye: kisebb JSON
- hátránya: placement mapping bonyolódhat

**MVP döntés:** példányosítás.

**Feladatlista:**
- [ ] Implementáld `expand_instances(parts)`:
  - output: `PartInstance[]` (pl. `part_id#001`, `part_id#002`…)
  - örökölt meta: name, source_ref
- [ ] Logold a total instance countot (összes darabszám)
- [ ] Rakj be védelmet:
  - ha total instances > pl. 10 000 → warning (MVP)

**Kimenet:**
- instance szintű lista, amiből JSON itemeket építesz

---

### 5.5. Rotációk előállítása: fixed/step/list → allowed_orientations

**Összefoglaló:**
A „tetszőleges forgatás” az MVP-ben diszkrét szöglista. A szögek egységesen fokban legyenek, 0..359 tartományban.

**Feladatlista:**
- [ ] Implementáld `build_allowed_orientations(rot_cfg)`:
  - `fixed` → [0, 90, 180, 270]
  - `step` → [0, step, 2*step, …] (360 alatti)
  - `list` → normalize (mod 360, unique, sort)
- [ ] Validációk:
  - step > 0
  - lista nem üres
  - max elem szám limit (pl. 360)
- [ ] Opcionális per-part override (P1): egyes alkatrészekhez tiltott rotációk

**Kimenet:**
- `allowed_orientations: List[float|int]`

---

### 5.6. Run paraméterek leképezése: time_limit, seed, workers

**Összefoglaló:**
A sparrow futást determinisztikusabbá és kontrollálhatóvá kell tenni.

**Feladatlista:**
- [ ] `time_limit_s` beemelése a JSON-ba (ha a sparrow input része), vagy CLI argként tárolása
- [ ] `seed` rögzítése:
  - default fix seed (pl. 12345), felülírható
- [ ] `workers` (threads) kezelése:
  - ha nincs megadva: CPU magok száma (de logold)
- [ ] `run_config.json` mentése a run mappába (akkor is, ha CLI-arg lesz belőle)

**Kimenet:**
- futási paraméterek rögzítve, logolva, mentve

---

### 5.7. Instance JSON összeállítása és mentése (reproducibility)

**Összefoglaló:**
A futás legfontosabb „bizonyítéka” az instance.json. Ezt mindig mentsd el, még hiba esetén is.

**Feladatlista:**
- [ ] Implementáld `build_instance_json(prepared_bin, part_instances, orientations, run_cfg)`:
  - bins blokk
  - items blokk (instance szinten)
  - global config blokk (ha van)
- [ ] Mentsd:
  - `runs/.../artifacts/instance.json`
  - opcionális: `instance_pretty.json` (indentelt)
- [ ] SHA/hash számítás:
  - számolj hash-t az instance.json tartalmára (reportba)

**Kimenet:**
- instance.json + hash

---

### 5.8. Validátor: gyors belső ellenőrzések JSON előtt/után

**Összefoglaló:**
MVP-ben a leggyakoribb hiba: üres ring, rossz irány, NaN, vagy óriási koordináták. Ezeket futtatás előtt ki kell fogni.

**Feladatlista:**
- [ ] `validate_prepared_bin()`:
  - area > 0, bbox size > 0
- [ ] `validate_prepared_part()`:
  - outer >= 3 pont
  - holes mind >= 3 pont
  - bbox nem üres
- [ ] `validate_instance_json()`:
  - bins count >= 1
  - items count >= 1
  - allowed_orientations nem üres
- [ ] Hibaüzenetek:
  - konkrét part_id, és hogy melyik ring a hibás

**Kimenet:**
- gyors, érthető hibák sparrow futtatás előtt

---

### 5.9. Debug/összefoglaló fájlok (human-friendly)

**Összefoglaló:**
A raw instance.json nagy lehet. Kell egy rövid summary.

**Feladatlista:**
- [ ] `instance_summary.json` generálása:
  - bins: W/H (bbox alapján)
  - total instances
  - parts by id: quantity
  - rotations: mode + count
  - clearance: margin, spacing, d
  - quality: arc_tolerance, simplify
- [ ] `report.json`-ba írd bele:
  - instance hash
  - total items

**Kimenet:**
- gyors áttekintés + reprodukciós meta

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] Rotáció generátor:
  - fixed → 4 elem
  - step=5 → 72 elem
  - list normalizál: duplikátum kiszűrés + sort
- [ ] Példányosítás:
  - 1 part quantity=3 → 3 instance id
- [ ] JSON validátor:
  - üres holes ok
  - üres outer → hiba
- [ ] Instance hash stabil:
  - ugyanaz a bemenet → ugyanaz a hash

### Minimum manuális ellenőrzés
- [ ] `instance_pretty.json` szemrevételezés: bin pontok, 1–2 item pontlista, rotációk

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Bemenet:**
- 4) `PreparedBin`, `PreparedPart[]`

**Kimenet:**
- 6) Sparrow futtatás subprocessből (instance.json + run args)

Megjegyzés: ha itt rossz a mapping (pl. ring irány, unit), a sparrow futás vagy összeomlik, vagy „értelmetlen” placementet ad. Ezért a validátor + instance mentés kötelező.

