# DXF nesting app – 3) Ívek/spline-ok poligonizálása + geometria clean (részletes)

## 🎯 Funkció

**Cél ebben a fázisban:**
A 2) lépésből kapott `PartRaw` (outer+holes szegmensláncok: LINE/ARC/POLYLINE) átalakítása **robosztus, zárt poligonokká** (pontlisták), amiket a nesting motor (sparrow/jagua) stabilan kezel.

**Kimenet:** `PartGeom`:
- `outer`: `List[Point]` (zárt poligon pontjai)
- `holes`: `List[List[Point]]`
- `stats`: pontszámok, bbox, area, warnings

**MVP cél:** gyártásbiztos pontosság (nem tökéletes CAD), stabil offset-elhetőség és ütközésvizsgálat.

---

## 🧠 Fejlesztési részletek

### 3.1. Paraméterek rögzítése (pontosság vs teljesítmény)

**Összefoglaló:**
A poligonizálás és a clean minősége paraméterfüggő. Ezeket *konfigból* kell olvasni, defaultokkal.

**MVP default javaslat:**
- `arc_tolerance_mm` = 0.2 (chord error)
- `min_arc_segments` = 12 (kis íveknél se legyen 3 pont)
- `circle_segments_min` = 36
- `dedupe_epsilon_mm` = 0.01–0.05
- `min_edge_len_mm` = 0.05–0.2
- `simplify_epsilon_mm` = 0.0 (MVP-ben alapból OFF)
- `max_points_per_ring` = 5000

**Feladatlista:**
- [ ] Definiáld a paramétereket a `project_model`-ben
- [ ] Adj értelmes defaultokat
- [ ] Logold ki a használt értékeket run elején

**Kimenet:**
- `QualityConfig`

---

### 3.2. „Path sampling” – szegmensek pontlistává alakítása

**Összefoglaló:**
Minden Path (szegmenslánc) végén egy pontlista legyen, ahol a pontok sorban követik a kontúrt.

**Alapelv:**
- LINE: csak a végpont kell (a kezdő pontot az előző szegmens adja)
- ARC: több pontot kell mintavételezni a toleranciához igazodva
- POLYLINE: meglevő pontokat felveszed (bulge eset külön)

**Feladatlista:**
- [ ] Írj `sample_path_to_points(path, cfg) -> List[Point]`:
  - indulj a path első szegmens start pontjából
  - minden szegmenshez add hozzá a szükséges pontokat
  - garantáld a folytonosságot (következő pont közel legyen az előzőhöz)
- [ ] LINE sampling:
  - add hozzá a `p1` pontot
- [ ] ARC sampling (részletesebb a 3.3-ban)
- [ ] POLYLINE sampling:
  - zárt flag kezelése
  - pontduplikációk elkerülése a csatlakozásnál

**Kimenet:**
- nyers pontlista (még clean előtt)

---

### 3.3. ARC/CIRCLE poligonizálás (chord error alapján)

**Összefoglaló:**
Az ívet úgy kell szegmentálni, hogy a poligon és az eredeti ív közti legnagyobb eltérés (chord error) ne haladja meg a toleranciát.

**Gyakorlati képlet:**
- adott `r` és `tol` mellett a maximális szög `dtheta`:
  - `dtheta = 2 * acos(1 - tol / r)` (ha `tol < 2r`)
- ív teljes szöge: `theta_total`
- szegmensek száma: `n = ceil(theta_total / dtheta)`
- `n >= min_arc_segments`

**Edge case-ek:**
- nagyon kicsi sugár / túl nagy tol → dtheta túl nagy → de min_arc_segments védi
- 0 hosszú ív → kezeld line-ként vagy skip
- irány (CW/CCW) és start/end normalizálás

**Feladatlista:**
- [ ] Implementáld az ARC pontgenerálást:
  - normalize angle range
  - compute n
  - generálj pontokat egyenletes szögosztással
- [ ] CIRCLE:
  - tekintsd 0..2π ívnek
  - `n = max(circle_segments_min, ceil(2π / dtheta))`
- [ ] Pont hozzáadásnál ne duplikáld az előző pontot (eps)

**Kimenet:**
- ív pontjai (köztes pontokkal)

---

### 3.4. SPLINE/ELLIPSE kezelési stratégia (MVP-safe)

**Összefoglaló:**
A spline a legnagyobb rizikó. MVP-ben két út van:
- (A) approximálás, ha az ezdxf ad rá elég infót
- (B) hard error + file listázás

**MVP javaslat:**
- próbálj approximálni fix mintaszámmal + tolerancia alapján
- ha nem sikerül stabil zárt ringet kapni → hiba

**Feladatlista:**
- [ ] Detektáld SPLINE/ELLIPSE típusokat outer/inner layeren
- [ ] Implementáld az approximálást:
  - uniform paraméter mintavétel (N pont)
  - N kezdőérték pl. 200, majd ha kell növeld
- [ ] Zártság ellenőrzés:
  - utolsó pont közel az elsőhöz (eps)
- [ ] Ha nem zárt / túl zajos / önmetsz: hiba (MVP)

**Kimenet:**
- spline-okból is pontlista vagy hiba

---

### 3.5. Ring zárás, irány (CW/CCW) és normalizálás

**Összefoglaló:**
A nesting motor és az offset könyvtárak szeretik, ha:
- ring zárt (első=utolsó vagy implicit zárás)
- outer és hole irány konzisztens (pl. outer CCW, hole CW)
- nincs extrém eltolás/float drift

**Feladatlista:**
- [ ] Zártság biztosítása:
  - ha last-first távolság <= close_eps → állítsd last=first
  - különben (MVP) hiba
- [ ] Irány meghatározása terület előjellel (shoelace)
- [ ] Outer irány egységesítés (pl. CCW)
- [ ] Hole irány egységesítés (ellentétes)
- [ ] Normalizáld a ringet:
  - start index rotálás (opcionális) – pl. lexikografikus minimum pont legyen az első (reproducibility)

**Kimenet:**
- konzisztens ringek

---

### 3.6. Geometria clean 1: pont deduplikáció és rövid élek

**Összefoglaló:**
A DXF-ek gyakran tartalmaznak nagyon rövid szakaszokat, duplikált pontokat. Ezek offsetnél és collisionnél instabilitást okoznak.

**Feladatlista:**
- [ ] Adj `dedupe_epsilon_mm` alapján:
  - egymás utáni azonos/közeli pontok törlése
- [ ] `min_edge_len_mm` alapján:
  - ha két egymás utáni pont távolsága < min_edge → vond össze (töröld a másodikat)
- [ ] Minimum pontszám:
  - ringnek legalább 3 egyedi pontja legyen
- [ ] Max pontszám:
  - ha > `max_points_per_ring`: warning + simplify (ha simplify engedélyezett) vagy hiba

**Kimenet:**
- tisztább pontlista

---

### 3.7. Geometria clean 2: önmetszés és érvényesség ellenőrzés

**Összefoglaló:**
Önmetsző poligonok (self-intersection) a nesting motor és offset számára is problémásak. MVP-ben inkább álljunk meg.

**Feladatlista:**
- [ ] Válassz validációs motort:
  - Shapely `Polygon.is_valid` (ajánlott)
  - vagy saját egyszerű O(n^2) edge-intersection check (csak MVP-hez, de íves pontszámnál drága)
- [ ] Outer valid:
  - valid polygon + area > 0
- [ ] Holes valid:
  - mind valid ring
  - hole tényleg outer-en belül van (containment)
  - hole-ok nem fedik egymást
- [ ] Hibakezelés:
  - self-intersection → hiba + javaslat: tolerancia csökkentés/növelés vagy DXF javítás

**Kimenet:**
- garantáltan érvényes geometria vagy konkrét hiba

---

### 3.8. Hole hozzárendelés és hierarchia (outer + holes)

**Összefoglaló:**
MVP-ben a hole layerből érkező ringeket hozzá kell rendelni az outerhez. Ha több outer lenne, ez fa-struktúra, de MVP-ben 1 outer van.

**Feladatlista:**
- [ ] Számíts centroidot a hole ringre
- [ ] Check: centroid benne van-e az outer polygonban
- [ ] Ha nem: warning/error (MVP-ben inkább error)

**Kimenet:**
- `Polygon(outer, holes)` szerkezet

---

### 3.9. (Opcionális) Simplify és pontszám kontroll – csak kontrolláltan

**Összefoglaló:**
A túl sok pont lelassítja a nestinget és az offsetet. Simplify-t csak akkor kapcsolj be, ha van rá szükség.

**Feladatlista:**
- [ ] Implementáld (ha Shapely): `polygon.simplify(epsilon, preserve_topology=True)`
- [ ] Csak akkor futtasd, ha pontszám > limit vagy explicit config
- [ ] Utána validáld újra

**Kimenet:**
- kezelhető pontszám, megőrzött topológia

---

### 3.10. Statisztikák + debug export (kritikus)

**Összefoglaló:**
A poligonizálás minőségét gyorsan vissza kell tudni nézni. Ezért run-onként ments:
- pontszámok
- bbox
- area
- warningok
- debug SVG/JSON

**Feladatlista:**
- [ ] `PartGeomStats`:
  - outer_points, holes_points_total
  - bbox (minx,miny,maxx,maxy)
  - area
  - validity flags
- [ ] Debug export:
  - `runs/.../debug/geom_part_<id>.svg` (outer + holes)
  - `runs/.../debug/geom_part_<id>.json` (pontlisták)
- [ ] Jelöld SVG-ben:
  - outer vastag
  - holes vékony
  - start pont marker

**Kimenet:**
- gyors vizuális QA, trace-elhető hibák

---

## 🧪 Tesztállapot

### Minimum automata tesztek
- [ ] ARC poligonizálás: adott r/tol mellett pontszám >= min_arc_segments és zárt
- [ ] CIRCLE poligonizálás: zárt és pontszám >= circle_segments_min
- [ ] Dedupe/min_edge: rövid szakaszok eltűnnek, ring még valid
- [ ] Validáció: self-intersecting ring → hiba
- [ ] Hole containment: hole centroid outerben, különben error

### Minimum manuális ellenőrzés
- [ ] 1 valós konkáv íves alkatrész poligonizált SVG-je szemre egyezik a DXF-fel
- [ ] offset későbbi fázishoz: a poligon shapely/pyclipper offsetelhető összeomlás nélkül

---

## 🌍 Lokalizáció

Nem kell.

---

## 📎 Kapcsolódások

**Kimenet** közvetlen bemenete a 4) lépésnek:
- spacing/margin offset

Megjegyzés: ha a 3) fázisban instabil a poligonizálás (túl sok pont, invalid ring), a 4) offset fog először látványosan szétesni. Ezért a validáció és debug export nem opcionális.

