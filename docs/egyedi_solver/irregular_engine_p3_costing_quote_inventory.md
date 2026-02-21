# Canvas: P3 — Costing + gépadatbázis + ajánlatkérés (ipari üzemi réteg)

## 🎯 Funkció

A P3 célja, hogy a nesting eredmény üzemileg használható legyen:

- gépprofil adatbázisból származó kerf + technológiai paraméterek,
- nesting outputból vágásidő és költség számítás,
- ajánlatkéréshez (quote) exportálható, verziózott, determinisztikus “quote artifact”.

P3-ban a solver már stabil (P0–P2), itt a fókusz: számolhatóság, auditálhatóság, integrációra kész contract.

## 🧠 Fejlesztési részletek

### P3-1 — Costing proxies “most”: cut length / pierce / travel baseline (solver output bővítés)

**Leírás**

Már a gépadatbázis előtt is legyen megbízható becslési alap:

- outer cut length (külső kontúr összhossz)
- inner cut length (lyukak összhossz)
- pierce count
- opcionális rapid travel proxy (egyszerű: kontúrok közti távolság összeg)

Ezek bekerülnek:

- run artifact meta/objective bontásba
- későbbi costing modul bemenetébe

**Kimenet**

- Metrics/costing-proxy modul (Rust oldalon javasolt)
- Run artifact mezők (v2 contractban)

**DoD**

- Metrikák determinisztikusan számolva
- Fixture készleten validálható (konszisztens számok)
- Output contractban stabil mezőnevek/egységek

### P3-2 — Machine profile DB schema v1 (kerf + feedrate + pierce + setup)

**Leírás**

Készül egy verziózott gépadat “tudásbázis”, ami később bővíthető:

- technológia: laser/plasma/waterjet
- anyag + vastagság → kerf
- anyag + vastagság → feedrate (vágási sebesség)
- pierce time
- opcionális: accel/rapid, setup idők, min feature, corner slowdowns

Formátum első körben lehet:

- JSON/YAML fájl a repóban (determinista, verziózható)
- később DB/API irányba vihető

**Kimenet**

- docs/machine_profile_schema_v1.md
- machine_profiles/*.json (példa profilok)
- Loader modul (Python vagy Rust) + validátor

**DoD**

- Schema dokumentált (mezők, egységek, verzió)
- Legalább 1 “valós” profil mintával
- kerf_source=lookup működik ezzel a profillal (P0-2 stub kiváltása)

### P3-3 — Costing engine v1: időszámítás (cut + pierce + travel) gépprofilból

**Leírás**

A proxy metrikák + gépprofil alapján kiszámoljuk:

- cut_time = (outer_len + inner_len) / feedrate
- pierce_time = pierce_count * pierce_time_per_pierce
- rapid_time = travel_len / rapid_speed (ha használod)
- total_time = cut_time + pierce_time + rapid_time + setup_time

Fontos: determinisztikus és auditálható breakdown.

**Kimenet**

- Costing modul (Rust vagy Python, de determinisztikus)
- Run artifact kiegészítés: cost_breakdown (idő komponensek)

**DoD**

- Breakdown mezők fixek és dokumentáltak
- Egységek egyértelműek (mm/s vagy mm/min)
- Fixture készleten reprodukálható

### P3-4 — Quote artifact v1: ajánlatkérés output (ár + idő + anyag)

**Leírás**

Készül egy dedikált “quote” kimenet:

- anyagköltség (sheet cost / kg, waste faktor)
- gépidő költség (Ft/óra)
- setup költség
- profit/margin szabály (opcionális)
- eredmény: total price + breakdown

Az output nem UI, hanem egy integrálható JSON artifact.

**Kimenet**

- docs/quote_artifact_contract_v1.md
- quote.json generálás a run artifactból (post-process)
- Verzió + hash + hivatkozás a forrás run artifactra

**DoD**

- Quote artifact determinisztikus
- Össze van linkelve a nesting run artifacthoz (id/hash)
- Legalább 1 példa quote a fixture készletből

### P3-5 — Remnant inventory könyvelés v1 (maradék mint készlet)

**Leírás**

A nesting eredményből a fel nem használt területből (binből) maradék keletkezik.
P3-ban nem kell full geometriai “maradék poligon kivágás”, de kell egy üzemi könyvelés:

- melyik binből mennyi anyag maradt (area proxy)
- mi az új maradék azonosítója
- később: alakos maradék poligon generálás (ha már megvan P2/P3 kernel oldalon)

**Kimenet**

- Inventory artifact / ledger (JSON)
- Policy: melyik maradék kerül vissza készletbe

**DoD**

- Maradékok keletkezése könyvelve (legalább area proxyval)
- Visszakereshető kapcsolás a run artifacthoz
- Későbbi alakos maradékra bővíthető mezők előkészítve

### P3-6 — Üzemi integráció előkészítés: export csomag (DXF + JSON + quote)

**Leírás**

A gyártásnak/ajánlatnak egy “csomag” kell:

- DXF (nominal)
- run artifact JSON (layout + meta)
- quote JSON (ár/idő breakdown)
- machine profile hivatkozás

**Kimenet**

- Export bundle directory struktúra (determinista névvel)
- docs/export_bundle.md

**DoD**

- Egyetlen paranccsal előáll a csomag
- Minden fájl verziózott és hivatkozott egymásra (id/hash)
- Reprodukálható (ugyanaz a run → ugyanaz a bundle)

## ✅ P3 Pipálható ellenőrzőlista

### P3-1 Costing proxies

- Outer cut length számítás (nominal vagy inflated? szabály rögzítve)
- Inner cut length számítás
- Pierce count számítás
- (Opcionális) travel proxy számítás
- Run artifact mezők bekerültek + dokumentált egységek

### P3-2 Machine profile DB

- docs/machine_profile_schema_v1.md elkészült
- Példa profil(ok) machine_profiles/*.json
- Loader + validátor elkészült
- kerf_source=lookup működik a profillal

### P3-3 Costing engine v1

- Cut time számítás feedrate alapján
- Pierce time számítás
- (Opcionális) rapid/setup idők
- Teljes idő breakdown run artifactban
- Determinisztikus és reprodukálható

### P3-4 Quote artifact v1

- docs/quote_artifact_contract_v1.md elkészült
- Anyagköltség modell (legalább sheet cost + waste faktor)
- Gépidő költség modell (Ft/óra)
- Quote JSON generálás run artifactból
- Link/hivatkozás: run_id/hash/solver_version

### P3-5 Remnant inventory könyvelés

- Maradék ledger artifact elkészült
- Visszakövethető run artifact kapcsolás
- Policy dokumentált (mi kerül készletbe)
- Bővíthető mezők alakos maradékhoz előkészítve

### P3-6 Export bundle

- Bundle struktúra dokumentált (docs/export_bundle.md)
- DXF + run artifact + quote együtt exportálható
- Determinisztikus fájlnevek/id-k
- Egy parancsos előállítás (pipeline integráció)

## 🧪 Tesztállapot

P3 PASS kritérium:

- ugyanarra a layout run-ra a costing + quote determinisztikus,
- machine profile lookup működik (kerf és feedrate onnan jön),
- export bundle komplett és auditálható (hivatkozások/hashes).

## 🌍 Lokalizáció

Nem releváns (belső motor + contract).

## 📎 Kapcsolódások

- docs/solver_io_contract_v2.md
- docs/dxf_project_schema_v2.md
- docs/dxf_run_artifacts_contract.md
- (új) docs/machine_profile_schema_v1.md, docs/quote_artifact_contract_v1.md, docs/export_bundle.md
- vrs_nesting/run_artifacts/run_dir.py
- vrs_nesting/dxf/exporter.py
- (javasolt) machine_profiles/*.json
