# Master Plan — `jagua-rs` + saját optimizer átállás

**Projekt:** DXF Nesting / VRS_nesting  
**Dátum:** 2026-05-21  
**Dokumentum szerepe:** kötelező vezérdokumentum a `jagua-rs` + saját optimizer fejlesztési lánchoz.  
**Státusz:** munkaterv / master control document

---

## 1. Rövid döntés

A projekt stratégiai iránya:

> Átállunk egy `jagua-rs` alapú gyors collision / geometry backend + saját optimizer architektúrára.  
> Az optimizer a Sparrow szemléletéből és mintáiból indul ki, de nem az eredeti Sparrow teljes solver-loopját vesszük át vakon.  
> A saját optimizer a VRS_nesting ipari fixed-sheet, multi-sheet, remnant és későbbi cavity-prepack céljaihoz igazodik.

A fejlesztés három fő képességi lépcsőben halad:

1. **Rectangular multi-sheet nesting, hole-ok kizárásával.**
2. **Irregular / remnant sheet nesting, hole-ok kizárásával.**
3. **Hole / part-in-hole kezelés cavity-prepack rétegen keresztül.**

Minden fázisban kötelező az **exact final validation**. Invalid layout nem lehet sikeres eredmény.

---

## 2. Hivatkozott alapdokumentumok

A teljes munkalánc csak az alábbi forrásdokumentumok együttese alapján vihető tovább.

### 2.1 Audit

**Hivatkozás:** `jagua-rs / Sparrow / SparrowGH / Sparrow BPP átalakíthatósági audit`

Az audit szerepe:

- tisztázza, hogy a `jagua-rs` milyen szerepet tölthet be a projektben;
- elkülöníti a `jagua-rs` backend szerepét a Sparrow optimizer/search szerepétől;
- feltárja a fixed-sheet, multi-sheet, irregular/remnant és hole/cavity kérdéseket;
- azonosítja, hogy mely részek vehetők át mintaként, és melyeket kell saját kódként megírni;
- stratégiai alapot ad a mostani átállási döntéshez.

Az auditot minden későbbi tasknál háttérforrásként kell kezelni. Ha egy task ellentmondana az auditban rögzített fő megállapításoknak, azt a task reportban explicit `DEVIATION` vagy `REQUIRES_DECISION` státusszal kell jelölni.

### 2.2 Fejlesztési terv

**Fájl:** `jagua_rs_sajat_optimizer_fejlesztesi_terv.md`

Ez a dokumentum tartalmazza:

- a célarchitektúrát;
- a `jagua-rs` szerepét;
- a saját optimizer felépítését;
- a Phase 0–5 fejlesztési sorrendet;
- a rectangular, irregular/remnant és cavity-prepack fázisok részletes technikai céljait;
- a fő kockázatokat;
- a döntési kapukat;
- az exact final validation kötelező szerepét.

A taskok részletes tartalma ebből a dokumentumból vezetendő le.

### 2.3 Canvas+YAML+runner task bontás

**Fájl:** `jagua_optimizer_canvas_yaml_runner_task_bontas.md`

Ez a dokumentum bontja a fejlesztési tervet repo-konform taskokra.

A task bontás szerepe:

- megadja a `JG-00…JG-27` taskláncot;
- meghatározza a taskok sorrendjét;
- meghatározza a dependency-ket;
- meghatározza, hogy melyik taskhoz milyen canvas, YAML és runner prompt tartozzon;
- rögzíti a phase gate-eket;
- biztosítja, hogy a munka ne egyszerre, hanem kontrollált, ellenőrizhető lépésekben történjen.

### 2.4 Pipálható folyamat-checklist

**Fájl:** `jagua_optimizer_task_progress_checklist.md`

Ez a dokumentum a taskok végrehajtásának kötelező ellenőrző listája.

A checklist szerepe:

- taskonként pipálható ellenőrzési pontokat ad;
- globális master checklistet tartalmaz;
- phase gate checklistet tartalmaz;
- rögzíti a kötelező záró mezőket;
- biztosítja, hogy a folyamat ne csak „elkészültnek mondott”, hanem ténylegesen ellenőrzött legyen.

A checklist pipálása **kötelező**, nem opcionális adminisztráció.

---

## 3. Kötelező alapelv a későbbi task csomagokra

A `JG-00…JG-27` taskokhoz tartozó későbbi **canvas+YAML+runner csomagok kizárólag** az alábbiak alapján készülhetnek:

1. a jagua/Sparrow audit megállapításai;
2. a `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` fejlesztési terv;
3. a `jagua_optimizer_canvas_yaml_runner_task_bontas.md` task bontás;
4. a `jagua_optimizer_task_progress_checklist.md` checklist;
5. a repo aktuális, valós kódja;
6. a repo szabályfájljai és meglévő mintái.

Tilos:

- általános, repo nélküli, elméleti taskot írni;
- nem létező fájlokra vagy modulokra építeni;
- feltételezett architektúrát valós kódnak beállítani;
- a hole-okat Phase 1–2-ben csendben figyelmen kívül hagyni;
- a `jagua-rs`-t teljes üzleti solverként kezelni, ha a valós kód/API ezt nem támasztja alá;
- a Sparrow teljes outer-loopját vakon átvenni;
- validáció nélkül sikeres layoutot elfogadni;
- checklist pipálása nélkül taskot lezárni.

---

## 4. Repo szabályfájlok és minták kötelező használata

Minden egyes canvas+YAML+runner csomag elkészítése előtt kötelező újraolvasni a repo szabályfájljait és mintáit.

A konkrét fájllista a repo aktuális állapotától függ, de a korábbi munkák alapján tipikusan ide tartoznak:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- meglévő canvas taskok
- meglévő goal YAML fájlok
- meglévő runner promptok
- meglévő reportok
- meglévő benchmark / verify scriptek

A task csomag készítőjének minden esetben a **repo valós mintáit** kell követnie:

- fájlnevezés;
- task slug;
- YAML mezők;
- report path;
- verify log path;
- runner prompt szerkezet;
- elfogadási kritériumok;
- output artifact elvárások;
- no-hallucination / real-code-only szabály.

Ha a repo mintája és a master plan között eltérés van, a task csomagban ezt explicit jelölni kell:

```text
REQUIRES_DECISION:
- repo pattern says: ...
- master plan says: ...
- proposed resolution: ...
```

---

## 5. Fő architekturális döntések

### 5.1 `jagua-rs` szerepe

A `jagua-rs` szerepe:

- gyors collision / geometry backend;
- item-item collision;
- lehetőség szerint sheet/container boundary check;
- később irregular/remnant boundary támogatás vizsgálata;
- optimizer által generált candidate állapotok validálása.

Nem a `jagua-rs` feladata:

- VRS üzleti workflow;
- DXF import/preflight;
- material/thickness profilok;
- sheet készletkezelés;
- cavity-prepack stratégia;
- final layout report;
- exact final validation;
- UI/API folyamatlogika.

### 5.2 Saját optimizer szerepe

A saját optimizer feladata:

- initial placement;
- move generation;
- repair-search;
- scoring;
- sheet assignment;
- sheet elimination;
- remnant preference;
- time/iteration stopping policy;
- reproducible seed kezelés;
- metrics/report adatok előállítása.

A Sparrow szerepe ebben:

- search/repair/penalty szemléleti minta;
- nem vakon átvett production core.

### 5.3 Exact final validation

Az exact final validation minden fázisban kötelező.

Elfogadott layout csak akkor lehet sikeres, ha:

- nincs item-item overlap;
- nincs sheet boundary violation;
- margin/gap szabályok teljesülnek;
- quantity helyes;
- instance identity helyes;
- Phase 3-ban child/parent/cavity expansion is valid;
- a validator PASS státuszt ad.

---

## 6. Fejlesztési fázisok

## 6.1 Phase 0 — Audit, scaffold, integrációs előkészítés

Érintett taskok:

- `JG-00`
- `JG-01`
- `JG-02`

Cél:

- master runner / task index létrehozása;
- repo és `jagua-rs` / Sparrow audit;
- solver module scaffold;
- integrációs előkészítés viselkedésváltozás nélkül.

Phase 0 kimenete:

- világos architektúra;
- build/integrációs kockázatok ismerete;
- no-op vagy minimális adapter előkészítés;
- Phase 1 indíthatósági döntés.

## 6.2 Phase 1 — Rectangular multi-sheet, hole nélkül

Érintett taskok:

- `JG-03…JG-14`

Cél:

- outer-only input contract;
- hole gate;
- JaguaAdapter proof-of-contact;
- rectangular sheet provider;
- item geometry store;
- layout state;
- construction placer;
- repair-search loop;
- score model;
- multi-sheet manager;
- sheet elimination;
- Phase 1 benchmark.

Fontos szabály:

> Phase 1-ben a hole-os inputot nem szabad csendben kezelni. Explicit unsupported / rejected / blocked státuszt kell adni.

Phase 1 kimenete:

- valid rectangular multi-sheet solver;
- exact validation PASS;
- reproducible seed;
- benchmark report;
- Gate 1 döntés.

## 6.3 Phase 2 — Irregular / remnant sheet, hole nélkül

Érintett taskok:

- `JG-15…JG-20`

Cél:

- irregular/remnant capability spike;
- sheet provider és margin kezelés;
- irregular boundary validation;
- boundary-aware candidate generation;
- remnant score model;
- Phase 2 benchmark.

Fontos szabály:

> Phase 2-ben továbbra sincs item-hole vagy container-hole kezelés. Csak outer-only partok és hole nélküli irregular/remnant sheetek engedélyezettek.

Phase 2 kimenete:

- alakos/remnant sheet kezelés;
- konzervatív boundary/margin validation;
- rectangular regresszió ellenőrizve;
- benchmark report;
- Gate 2 döntés.

## 6.4 Phase 3 — Cavity-prepack alapú hole kezelés

Érintett taskok:

- `JG-21…JG-25`

Cél:

- meglévő cavity-prepack pipeline audit;
- cavity extraction;
- usability filter;
- single-child cavity-prepack;
- macro-part expansion;
- final validation;
- main solver bridge.

Fontos szabály:

> A fő solver továbbra is outer-only macro-partokat kap. A hole/cavity szemantikát a prepack + expansion + final validation réteg kezeli.

Phase 3 kimenete:

- hole metadata megőrzése;
- child placement cavity-ben;
- macro-part létrehozás;
- expansion globális layoutba;
- exact validation PASS;
- Gate 3 döntés.

## 6.5 Phase 4–5 — Integráció, profilok, záró benchmark

Érintett taskok:

- `JG-26`
- `JG-27`

Cél:

- új backend/profil bekötése;
- capability flags;
- API/worker integráció;
- regresszió régi solver útvonalakon;
- final benchmark;
- release/continue/revise döntés.

---

## 7. Canvas+YAML+runner csomag készítési szabály

Minden taskhoz három fő artifact kell:

1. **Canvas / fejlesztési leírás**
2. **Goal YAML**
3. **Runner prompt**

Ezek nem készülhetnek sablonos általánosságként. Minden csomagnak tartalmaznia kell:

- task azonosító és slug;
- phase;
- dependency-k;
- cél;
- valós repo fájlok;
- csak engedélyezett módosítási scope;
- explicit out-of-scope lista;
- acceptance criteria;
- required tests;
- required reports;
- required verify parancs;
- checklist update kötelezettség;
- rollback / failure policy;
- no silent geometry loss szabály;
- exact validation szabály, ha layoutot érint.

### 7.1 Canvas minimumtartalom

A canvasban legyen:

- kontextus;
- probléma;
- cél;
- miért most;
- érintett fájlok;
- elvárt architektúra;
- részletes lépések;
- tesztek;
- report elvárás;
- blokkolók;
- elfogadási kritérium.

### 7.2 YAML minimumtartalom

A YAML a repo sémája szerint készüljön. A konkrét mezőket mindig a repo `yaml_schema` alapján kell kitölteni.

Kötelező tartalmi elemek:

- id / slug;
- title;
- phase;
- dependencies;
- mode;
- allowed paths;
- forbidden paths;
- steps;
- checks;
- artifacts;
- report path;
- verify log path;
- acceptance criteria.

### 7.3 Runner prompt minimumtartalom

A runner prompt legyen önállóan futtatható Hermes/Codex/Claude jellegű agenttel.

Tartalmazza:

- repo path;
- szabályfájlok kötelező olvasása;
- task canvas/YAML olvasása;
- valós kód audit;
- implementációs lépések;
- test parancsok;
- report követelmény;
- CHECKPOINT/REPORT blokk;
- no hallucination szabály;
- ha valami nem létezik a repo-ban, ne találja ki, hanem reportolja.

---

## 8. Futtatási rend

### 8.1 Task indítás előtti lépések

Minden task előtt:

1. Ellenőrizni kell, hogy a dependency taskok PASS státuszban vannak-e.
2. Meg kell nyitni a task canvas fájlt.
3. Meg kell nyitni a task YAML fájlt.
4. Meg kell nyitni a task runner promptot.
5. Meg kell nyitni a master plan aktuális verzióját.
6. Meg kell nyitni a checklist aktuális verzióját.
7. Újra kell olvasni a repo szabályfájljait.
8. Meg kell nézni a valós kódot az érintett fájlokban.
9. Csak ezután indulhat implementáció.

### 8.2 Task futtatása

A futtatás során:

- kizárólag az adott task scope-jába tartozó fájlok módosíthatók;
- minden eltérést dokumentálni kell;
- ha a repo valósága eltér a task feltételezéseitől, a runner nem találhat ki megoldást ellenőrizetlenül;
- blocking issue esetén reportot kell írni;
- részleges siker esetén `REVISE` státusz szükséges;
- invalid layout soha nem lehet PASS;
- benchmark és report artifactokat menteni kell.

### 8.3 Task lezárása

Task csak akkor zárható le, ha:

1. elkészült a report;
2. lefutottak a kötelező tesztek;
3. lefutott a repo verify wrapper;
4. elmentésre került a verify log;
5. frissült a checklist;
6. phase gate érintettség esetén elkészült a gate döntés;
7. a következő task indíthatósága egyértelmű.

---

## 9. Kötelező ellenőrzések

### 9.1 Build / test

Minden tasknál a repo aktuális szabályai szerint kell futtatni a teszteket.

A jellemző ellenőrzési rétegek:

- Rust build;
- Rust unit tesztek;
- Python unit tesztek;
- solver smoke;
- benchmark smoke;
- exact validator smoke;
- UI/API smoke, ha érintett;
- teljes repo verify wrapper.

Konkrét parancsot mindig a repo aktuális mintái alapján kell meghatározni.

### 9.2 Validation

Layoutot érintő tasknál kötelező:

- valid layout PASS fixture;
- invalid overlap FAIL fixture;
- boundary violation FAIL fixture;
- quantity mismatch FAIL, ha releváns;
- cavity expansion FAIL/PASS, ha Phase 3 task.

### 9.3 Benchmark

Benchmark taskoknál kötelező:

- input fixture azonosítása;
- solver profile azonosítása;
- seed;
- time limit;
- rotations;
- backend;
- runtime;
- placed count;
- unplaced count;
- used sheets;
- utilization;
- validation status;
- report path;
- log path.

---

## 10. Checklist pipálási rend

A `jagua_optimizer_task_progress_checklist.md` pipálása kötelező.

### 10.1 Mikor kell pipálni?

Checklist pipálása szükséges:

- task indításakor státuszmezőnél;
- minden nagyobb részfeladat elkészülésekor;
- tesztek lefutása után;
- report elkészülése után;
- verify lefutása után;
- task lezárásakor;
- phase gate döntésnél.

### 10.2 Ki pipálhat?

Pipálhatja:

- a feladatot futtató agent;
- a reviewer agent;
- kézi ellenőrző személy;
- Codex/Hermes review folyamat, ha a repo workflow ezt támogatja.

De a pipálás csak akkor érvényes, ha van mögötte:

- konkrét fájl;
- konkrét log;
- konkrét tesztkimenet;
- konkrét report;
- vagy explicit dokumentált blocker.

### 10.3 Pipálás szabálya

Tilos kipipálni egy pontot, ha:

- nem történt meg;
- nincs bizonyíték;
- csak feltételezésen alapul;
- a repo valós kódja nem támasztja alá;
- a teszt nem futott le;
- a validator nem PASS;
- a kapcsolódó artifact nem létezik.

Ha egy pont nem teljesíthető, akkor nem kipipálni kell, hanem mellé írni:

```text
BLOCKED:
- reason:
- evidence:
- proposed next step:
```

---

## 11. Jelentési rend

Minden task reportnak tartalmaznia kell:

- task id;
- slug;
- dátum;
- futtató;
- módosított fájlok;
- olvasott fontos fájlok;
- implementált változások;
- tesztek;
- benchmarkok;
- verify log path;
- checklist státusz;
- acceptance criteria státusz;
- blocker/deviation lista;
- következő javasolt lépés.

### 11.1 Kötelező státuszok

A report végén egyértelmű státusz kell:

```text
STATUS: PASS
```

vagy

```text
STATUS: REVISE
```

vagy

```text
STATUS: BLOCKED
```

vagy

```text
STATUS: STOP
```

PASS csak akkor adható, ha:

- minden kötelező acceptance criteria teljesült;
- a tesztek lefutottak;
- a verify lefutott;
- nincs elhallgatott invalid layout;
- a checklist releváns pontjai ki vannak pipálva;
- nincs nyitott blocker.

---

## 12. Tiltott rövidítések és veszélyes kerülőutak

A következő megoldások tilosak:

- hole kontúrok eldobása csak azért, hogy a solver fusson;
- invalid layout sikeresnek jelölése;
- benchmark nélküli minőségállítás;
- repo fájlok feltételezése megnyitás nélkül;
- nem létező modulokra való hivatkozás;
- task scope-on kívüli nagy refaktor;
- dependency sorrend felrúgása;
- phase gate átugrása;
- checklist utólagos, bizonyíték nélküli kipipálása;
- jagua API képesség feltételezése kódszintű ellenőrzés nélkül;
- Sparrow teljes átvétele anélkül, hogy fixed multi-sheet / remnant / cavity célhoz igazítanánk.

---

## 13. Elfogadási kapuk összefoglalója

### Gate 0 — Integrációs döntés

Feltétel:

- audit kész;
- scaffold kész;
- nincs showstopper;
- Phase 1 indítható.

### Gate 1 — Rectangular viability

Feltétel:

- rectangular multi-sheet működik;
- hole gate működik;
- exact validation PASS;
- Phase 1 benchmark kész.

### Gate 2 — Irregular/remnant viability

Feltétel:

- irregular boundary működik;
- margin kezelés dokumentált;
- rectangular regresszió nincs;
- Phase 2 benchmark kész.

### Gate 3 — Cavity viability

Feltétel:

- cavity extraction működik;
- single-child prepack működik;
- macro expansion működik;
- exact final validation PASS;
- darabszám/identity helyes.

### Gate 4 — Release / continue decision

Feltétel:

- backend/profile integráció kész;
- final benchmark kész;
- régi backend regresszió ellenőrizve;
- döntés: continue / revise / stop.

---

## 14. A master plan gyakorlati használata

A későbbi munka során minden új task csomag készítésekor az agentnek ezt a sorrendet kell követnie:

1. Nyisd meg ezt a master plan dokumentumot.
2. Nyisd meg az auditot.
3. Nyisd meg a fejlesztési tervet.
4. Nyisd meg a task bontást.
5. Nyisd meg a checklistet.
6. Olvasd el a repo szabályfájljait.
7. Keresd meg a repo meglévő mintáit.
8. Nézd meg a valós érintett kódot.
9. Csak ezután készíts canvas+YAML+runner csomagot.
10. A csomagban mindig hivatkozz a releváns task id-ra és phase-re.
11. A csomag végén rögzítsd az acceptance criteria-t és a checklist update kötelezettséget.

---

## 15. Záró összefoglaló

Ez a master plan rögzíti, hogy a `jagua-rs` + saját optimizer átállás nem ad-hoc kísérlet, hanem kontrollált, auditált, taskokra bontott fejlesztési lánc.

A siker feltételei:

- valós repo-kódra építés;
- repo szabályfájlok és minták követése;
- audit + fejlesztési terv + task bontás + checklist együttes használata;
- phase gate-ek betartása;
- exact final validation;
- hole-ok explicit kezelése;
- cavity-prepack csak a megfelelő fázisban;
- mérhető benchmarkok;
- kötelező checklist pipálás;
- minden task végén report + verify log.

A fejlesztés csak akkor tekinthető kontrolláltan előrehaladónak, ha a taskok nemcsak elkészülnek, hanem a checklist, a reportok és a verify logok alapján auditálhatóan bizonyítottak.
