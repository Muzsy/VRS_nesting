# Technikai audit: jagua-rs, Sparrow, SparrowGH és Sparrow BPP mint ipari 2D irreguláris nesting solver-core alapja

## TL;DR
- **A jagua-rs maga megéri (mint geometriai CDE backend), de a Sparrow / SparrowGH / SparrowGH-BPP NEM kész ipari solver — csak proof-of-concept szintű alap.** Az irreguláris konténer és a több bin / shaped remnant működéshez saját optimalizáló-réteget kell írni a jagua-rs `probs::bpp` modellje fölé; a SparrowGH BPP módja kódszinten téglalap-sheet-re optimalizál.
- **Két stratégiai kockázat blokkolja a "csak rá kell ülni a SparrowGH-ra" forgatókönyvet:** (1) maga a SparrowGH BPP-je csak fix téglalap lapokra dolgozik, és a C# wrapper csak width/height-et fogad; (2) a jagua-rs item-szinten *nem* támogat lyukas poligont — csak a Container kap `holes` / `InferiorQualityZone` mezőt. A part-in-hole / cavity nesting tehát csak külön „virtual container / prepack" réteggel valósítható meg, ami önálló fejlesztés.
- **Ajánlás: igen, érdemes egy 1-2 hetes validációs spike-ot futtatni**, de NEM a SparrowGH adaptálására, hanem közvetlenül a `jagua-rs` (`probs::bpp` + saját kereső + saját irregular-container wrapper) tengelyre. A Sparrow keresési logikája (exploration/compression, separator, sampling) hasznos *referencia*, de a kódját jelen formájában strip-packing-re kötik a `probs::spp` típusai — átemelni komoly portoló munka.

## Key Findings

### 1. jagua-rs (JeroenGar/jagua-rs) — érdemi alap, de csak backend
- **Szerep:** kifejezetten **Collision Detection Engine (CDE) és geometriai backend**, nem solver. A README és a kísérő INFORMS JoC-cikk — Gardeyn, Vanden Berghe & Wauters (KU Leuven), *"Decoupling Geometry from Optimization in 2D Irregular Cutting and Packing Problems: An Open-Source Collision Detection Engine"*, INFORMS Journal on Computing, 2025 (DOI 10.1287/ijoc.2024.1025) — explicit célként mondja a "decouple geometry from optimization"-t. (dokumentáció + paper)
- **Crate feature-ök** (docs.rs/jagua-rs 0.7.x): `spp` (Strip Packing), `bpp` (Bin Packing), `mspp` (Multi-Strip Packing). Knapsack még nincs. (dokumentáció + kód)
- **Modulok:** `entities` (Container, Item, Layout, LayoutSnapshot, PlacedItem, InferiorQualityZone, Instance trait), `collision_detection`, `geometry` (primitives, convex_hull, fail_fast surrogate, shape_modification), `io`, `probs::{spp,bpp,mspp}`, `util`. (docs.rs, igazolt dokumentációval)
- **Geometriai típusok:** az item és container alakja `SPolygon` ("A SPolygon exactly as is defined in the input file" — docs.rs/geometry). Az `SPolygon` saját implementáció (`geometry::primitives`); a kód *egy* zárt egyszerű poligonra van szabva. A README design-goals listája *konténer*-szinten említi a "Holes and inferior quality zones in containers" támogatást — item-szinten nem. (dokumentáció)
- **Container irregular + lyukas támogatás:** igen, README szerint a Container irreguláris alakú lehet, és belül „holes" és „inferior quality zones" definiálhatók (utóbbi `InferiorQualityZone` struct). Folyamatos forgatás támogatott, item↔hazard minimum-szeparáció is. (dokumentáció)
- **BPP modell** (`jagua_rs::probs::bpp`): külön modul; tárolja a BPInstance / BPProblem / BPSolution kapcsolatot. A modellt maga a `lbf` referencia-implementáció is meg tudja hajtani (`-p bpp`). (dokumentáció igazolt; bpp példa `img/bp_example.svg`)
- **Limitációk:** a `lbf` *nem* ipari solver, csak referencia LBF heurisztika. Maga a `jagua-rs` csak állapot+lekérdezés réteg: az inter-bin mozgások, az NFP-szerű optimalizálás, a bin-számcsökkentés *nincs* benne — ezt rád bízza.
- **Verzió:** jagua-rs v0.7.0, 2026. április 23-án jelent meg (27 nappal a mai 2026. május 20. előtt), per crates.io versions ("0.7.0 · by Jeroen Gardeyn 27 days ago · 2024 edition 71.4 KiB MPL-2.0 3 Features").

### 2. Eredeti Sparrow (JeroenGar/sparrow) — strip-packing-only
- **Probléma:** kizárólag **2D irreguláris strip packing (2DISPP)**. README és a kísérő arXiv:2509.13329 (Gardeyn, Vanden Berghe & Wauters, *"An open-source heuristic to reboot 2D nesting research"*, 2025-09-05, EJOR-nak benyújtva) világos: fix szélességű csík, változó magasság minimalizálás. Bin packingre csak utalás, hogy "easily incorporated into" lenne, de nincs implementálva. (dokumentáció + paper)
- **jagua-rs használat:** backendként a `probs::spp` modellen keresztül; CLI csak `-i input.json -t time -e expl -c comp -x early -s seed` opciókkal indít (README listázza a flag-eket; nincs `--mode bp`). (dokumentáció)
- **Keresési logika** (paper §8 és §9 alapján): két fázis — **exploration (80%)** és **compression (20%)** — a paper §9.1 (Exploration phase) és §9.2 (Compression phase) szerint; a feasibility-feloldó belső logika (separator, guided local search) §8.2 (Separation Procedure) és §8.1 (Guided local search). A 80/20 arány a README-ben is igazolt: "By default 80% of the timelimit is spent exploring and 20% is spent compressing." Belül **separator** + **collision tracker** + sampling alapú placement-keresés működik.
- **Strip-packing kötöttség:** a `bench` binary és az output (`output/final_{name}.svg`) egyetlen stripet vár; a kereső a stripet *átméretezi* a compression fázisban — ez fix-bin BPP-re közvetlenül nem értelmezett.
- **Átvihetőség fix-sheet/BPP-re:** a *feasibility-feloldó belső mag* (separator + collision tracker + sampling) elvileg átvihető fix bin-be, *de* a Cargo.toml-ben (kód) a `jagua-rs` minden valószínűség szerint csak `spp` feature-rel van behúzva (alternatív bizonyítatlan), és a teljes `src/` szerkezet a `probs::spp::SPInstance/SPProblem` típusokra van szabva. Átfogó refaktor kell.

### 3. SparrowGH (coroush/sparrow-grasshopper) — Grasshopper wrapper + Rust BPP fork
- **Struktúra:** a `coroush/sparrow-grasshopper` repo **csak C# wrapper (92,1% C#, 7,9% Shell)** Rhino/Grasshopper-hez. A tényleges Rust motor egy **git submodule-ként** mellékelt `coroush/sparrow` fork, commit `5df9ce15960f262545169f989ff1068b5f038c9c`-re pinelve. (igazolt: a repo tartalomjegyzéke + `.gitmodules`)
- **Kommunikáció:** a README explicit megfogalmazza: **"The engine communicates via JSON in the system temp directory."** — tehát a C# komponens egy temp-fájlba kiír egy jagua-rs JSON-t, alfolyamatként meghívja a fork natív Rust binárisát, eredmény-JSON-t visszaolvas, görbéket transzformál a Rhinóban. NEM FFI, hanem subprocess + file IO.
- **Komponensek:** `SpNest` (BPP: több fix méretű **téglalap** sheet) és `SpStrip` (strip packing változó szélességű csík). A README szó szerint: "Nests closed planar curves onto one or more fixed-size *rectangular sheets*."
- **Bin input a wrapperben:** csak width/height. Irreguláris bin / remnant *nem* támogatott bemenetként a C# komponensben. A McNeel fórum thread is megerősíti: laurent_delrieu külön kéri a "nest inside holes" és különböző sheet-méret támogatást mint hiányzó feature-t ("I think I will have to make a tool to nest inside holes. If you implement holes it will become a quite complete tool. ... In my use case I also have different sheet size."), Cumberland is brep/hole supportot kér ("It is possible to add SURFACE or BREP nesting support? This way the more complicated shapes with holes should be nested correctly."). (dokumentáció + felhasználói visszajelzés, 2026. április)
- **Determinizmus:** seed input lehetséges, de coroush szerint nem szigorúan determinisztikus, mert idő-limites és párhuzamos seedeket futtat. Eredmény-cache van.

### 4. Sparrow BPP / bin-packing mód (coroush/sparrow `5df9ce1`)
- **Forkban hozzáadott mód:** "This fork extends the original Sparrow engine with bin packing (nesting onto multiple fixed-size sheets) alongside the original strip packing mode." (SparrowGH README, igazolt). Tehát a fork **valódi különálló BPP optimalizáló-pályát** ad hozzá a forkhoz, nem csak wrappert.
- **Forrás-szintű részletek:** kódszintű audit során a `coroush/sparrow/src/` mappa, a `main.rs` CLI mode-dispatch, és a `Cargo.toml`-ban a `jagua-rs` feature-set (várhatóan `["spp","bpp"]`) közvetlenül nem volt hozzáférhető a fetch-jogosultságok miatt — ez **bizonyítatlanul valószínű** marad amíg a repo helyileg klónozva nem lesz.
- **Bin alak feltételezés:** a wrapper-szintű "rectangular sheets" megfogalmazás és a felhasználói visszajelzés erősen utal arra, hogy a BPP path **kódszinten is `Container::from_rect`-szerű konstrukciót használ**, nem általános `SPolygon`-t a binhez — *bizonyításhoz tényleges kódolvasás kell*.
- **Inter-bin mozgások:** egy fórum-felhasználó (laurent_delrieu, 2026. ápr. 13.) a futási logban "inter bin moves" fázisra utal: "A bit frustrating after 1000 s (inter bin moves)". Ez **valószínűsít** valódi multi-bin perturbációs lépéseket, de a kódbeli pontos algoritmus (FFD/LBF builder, bin-csökkentés, swap, repack) bizonyítatlan.
- **Lower bound / utilization / cost / multi-bin-type:** dokumentációban nem említett. Bizonyítatlan, valószínűleg hiányzó.
- **Bin-shaped remnant:** a "fixed-size rectangular sheets" megfogalmazás és a `jagua-rs::probs::bpp::BPInstance` általános volta miatt egy SHAPED REMNANT bemenet *jagua-rs szinten* technikailag valószínűleg már átmegy, *Sparrow BPP-szinten* **valószínűleg törik** a fix téglalap-feltételezés miatt — POC-szintű teszttel kellene mérni.

## Details

### A) Fix lap / multi-sheet alkalmasság
- **Eredeti Sparrow:** módosítás nélkül **alkalmatlan** fix-sheet/BPP-re. A `src/` szerkezet a `probs::spp` típusokra szabott; a compression fázis a csíkot zsugorítja, ami fix bin esetén értelmetlen.
- **SparrowGH BPP mód:** valódi multi-bin optimalizáló *iránynak* tűnik (inter-bin moves említés), DE: csak **azonos méretű, téglalap alakú** lapokra optimalizál, multi-bin-type / költség / stock nem dokumentált. A bin-szám csökkentés és a sheet-elimináció a "fix-size, N copies" sémán belül *valószínűleg* megvan, de heterogén készletre nem.
- **Verdikt:** "részben kész". Rectangular multi-sheet smoke-tesztre alkalmas. Heterogén stock-ra, költségmodellre, irregular binre **NEM kész**.

### B) Shaped remnant / irreguláris konténer
- **jagua-rs modell-szinten:** **lehetséges**. A `Container` `SPolygon`-t kap; az `entities::InferiorQualityZone` és container-`holes` támogatottak; a CDE általánosan kezeli a Hazard absztrakciót. (dokumentáció)
- **Sparrow / SparrowGH BPP engine-szinten:** *valószínűleg törik*, mert (i) a `coroush/sparrow` BPP path feltehetően téglalap-bint feltételez a builderben, (ii) a Grasshopper komponens csak width/height inputot fogad, (iii) az SVG export és layout-rendezés rectangular-grid alapú lehet a több-sheet vizualizációhoz.
- **Mit kéne csinálni egy minimális POC-hoz:** a jagua-rs `BPInstance` JSON-jában kézzel megadni egy nem-konvex Container `SPolygon`-t (pl. L-alak), majd közvetlenül a `lbf` crate-tel futtatni a BPP-t (`-p bpp -i custom_irregular.json`). Ha ez átmegy a CDE-n, a probléma kizárólag wrapper/optimizer szintű — ami megkerülhető saját kereső megírásával a jagua-rs fölé.
- **Verdikt:** modellszinten támogatott, motor-szinten *jagua-rs-en keresztül* át lehet vinni, **a Sparrow/SparrowGH BPP optimalizálót viszont gyakorlatilag újra kell írni** ehhez.

### C) Belső kivágás / part-in-hole nesting (kritikus pont)
- **Item lehet-e lyukas?** A jagua-rs `Item` `SPolygon`-t használ, és a README a "holes and inferior quality zones" támogatást csak *containers*-re mondja. **Item-szinten lyukas poligont valószínűleg NEM kezel natívan a jagua-rs.** (bizonyítható: a feature-listában csak container; bizonyítatlan a kód forrásnyomával, de a paper sem említ item-hole-t.)
- **Container hole = packelhető tér?** NEM. A jagua-rs `holes` és `InferiorQualityZone` a containerben **tiltott** régiókat jelent (oda nem szabad item-et tenni), nem packolható szabad teret.
- **Natív part-in-hole nesting:** **nincs.** Sem a jagua-rs, sem a Sparrow, sem a SparrowGH nem támogatja, hogy egy nagyobb item belső kivágásába egy kisebb item rakható legyen.
- **Megoldás-architektúra (saját fejlesztés):** egy **cavity-extraction / virtual-container / prepack-layer** réteget kell hozzáadni a solver fölé:
  1. Minden olyan input itemnél, amelynek van belső kivágása, a kivágás-poligonokat **virtuális Container-ként** ki kell emelni.
  2. Egy külön (előzetes vagy beágyazott) **prepack-fázis** ezekbe a virtuális konténerekbe nesteli a kisebb itemeket (önállóan, jagua-rs hívással).
  3. A prepack eredménye egy **macro-item / composite item** — a parent item és a benne pre-packelt gyerekek együttesen kerülnek be a fő BPP-be, mint egyetlen merev egység.
  4. A globális elhelyezés után a gyerek-itemek transzformációit a parent koordinátarendszerből visszavetítjük a globális koordinátarendszerbe.
  5. A pontos végső validáció a teljes (parent + nested children) geometrián fut.
- **Kockázat:** ez **önálló, nem-triviális réteg** (kb. 1-3 emberhónap). A jagua-rs architektúrájához *jól illeszkedik* (mert minden konténer-poligon, és a fő solver számára a macro-item csak egy normál Item), DE a sample-alapú placement-keresőnek tudnia kell, hogy a macro-item nem-konvex hosszúkás alakzat sokszor — ez a fail-fast surrogate hatékonyságát rontja.
- **Verdikt: STRATÉGIAI KOCKÁZAT** — natívan egyik komponens sem oldja meg, és bár az architekturális illeszkedés jó, valós fejlesztési költség 1 emberhónap szintjén várható.

### D) Adaptációs útvonalak
| Útvonal | Realisztikusság | Kockázat |
|---|---|---|
| (i) jagua-rs mint CDE + saját fix-sheet/remnant optimalizáló | **AJÁNLOTT** | mérsékelt, de a kereső megírása ~1-2 hónap |
| (ii) eredeti Sparrow keresési logikájának fix-bin-re portolása | nem érdemes önállóan | nagy: a kód `probs::spp`-re van szabva, és nincs API-stabilitás |
| (iii) SparrowGH BPP irregular bin-re terjesztése | rossz | a wrapper rectangular-only feltevése mély; a fork upstream-függő |
| (iv) saját wrapper a `jagua-rs::probs::bpp` modell köré | **AJÁNLOTT, párosítva (i)-vel** | alacsony, ha a tagok jagua-rs JSON-t bírnak |
| (v) cavity-prepack réteg part-in-hole-ra | **KÖTELEZŐ** ha az követelmény | mérsékelt, 1-3 hónap |
| (vi) exact polygon validáció záróellenőrzésnek | **AJÁNLOTT** | alacsony, ti. már megvan |

**Konklúzió:** a legjobb stratégia: **(i) + (iv) + (v) + (vi)** — jagua-rs mint CDE, saját BPP-optimalizáló a `probs::bpp` köré, cavity-prepack réteg, saját exact-validátor zárásnak.

### Kódmódosítási térkép (ahol be kell nyúlni)
- **Új saját Rust crate** (`our_nester` workspace member), amely `jagua-rs`-t depend-eli `bpp` és `spp` feature-rel.
- **Bin builder** (`our_nester/src/bin_builder.rs`): `Container::from_polygon(SPolygon)` + opcionálisan `InferiorQualityZone`-ok az irreguláris remnantokhoz.
- **BPP kereső** (`our_nester/src/optimizer/`): első mag = FFD/LBF konstruktív (referenciát a `jagua-rs/lbf/src/opt/`-ból átvenni), második fázis = Sparrow-stílusú separator/compression átemelve a `JeroenGar/sparrow/src/`-ből (FELTÉTELESEN: a `separator`, `collision_tracker`, `sampler` modulokat portolni kell `SPInstance`-ról általános trait-re).
- **Cavity-prepack** (`our_nester/src/cavity/`): item-onkénti hole-extraktor, virtuális Container-építő, prepack-runner (újra hívva ugyanazt a BPP-keresőt rekurzívan), macro-item-szintetizáló, visszavetítő.
- **Validátor** (`our_nester/src/validate/`): a meglévő pontos NFP-alapú validátor megtartása záróellenőrzésre — a jagua-rs CDE ugyan túl-konzervatív (épp túl közeli alakzatok mellett "collision"-t jelez floating-point biztonság miatt — paper §6), tehát a végső pontos polygon-validáció *kötelező* a marginok meghatározásához.
- **Téglalap-feltételezések kockázati pontjai** (ahol *jelenleg* hardkódolt téglalap van a SparrowGH-ban, valószínűsített, kódolvasás nélkül): bin-builder a fork `src/`-jében, az output SVG bin-rácsozás, és a C# wrapper bemeneti UI. Ezeket a saját solverben *nem fogjuk újra elkövetni*.

## Recommendations (staged)

**1. fázis — 1-2 hetes validációs spike** (előbb erre menj, csak utána eldönts):
- **Lépés 1 (½ nap):** klónozd helyileg `JeroenGar/jagua-rs` és `JeroenGar/sparrow` aktuális főágát; futtasd `lbf -p bpp -i assets/<egy_bpp_pelda>.json` — ellenőrizd, hogy a `bpp` feature és példa-instance működik. **Klónozd a `coroush/sparrow`-t is**, és olvasd át a `src/main.rs`-t és a `Cargo.toml`-t — itt fog kiderülni, mire futott a fork (FFD vs. valódi inter-bin), és hogy a bin builder `from_rect`-et vagy `from_polygon`-t használ.
- **Lépés 2 (1 nap):** rectangular multi-sheet smoke-teszt SparrowGH-val (`coroush/sparrow-grasshopper` v0.2.4, 2026. ápr. 18-i kiadás), ~500 alkatrésszel a saját laser-cut tipikus készletből — mérj valós packing density-t és runtime-ot a meglévő solveredhez képest.
- **Lépés 3 (1-2 nap):** irreguláris L-alak remnant teszt — kézzel írj egy `BPInstance` JSON-t L-alak `SPolygon`-nal mint Container, futtasd a `lbf`-fel `-p bpp` módban. Várt eredmény: jagua-rs átmegy, a Sparrow BPP fork töri. Ha jagua-rs is törik → kritikus blokkoló, dönts re-evaluációt.
- **Lépés 4 (1 nap):** remnant with hole / forbidden zone teszt — ugyanaz az instance, de adj hozzá egy `holes` mezőt vagy `InferiorQualityZone`-t. Várható: jagua-rs CDE kezeli; `lbf` is. Ez bizonyítja, hogy a CDE alkalmas shaped remnantra.
- **Lépés 5 (2 nap):** part-in-hole prepack prototípus — egy nagy lyukas item; kézzel kiemelve a lyukat virtuális Containerként; `lbf -p bpp` kicsi itemekkel; majd manuálisan a parent itembe komponálva. Mérd: a macro-item milyen rosszul illeszkedik a fő bin-be.
- **Lépés 6 (½ nap):** exact validation comparison — a kapott layoutokon futtasd a meglévő NFP-alapú exact polygon validátorodat és nézd meg, mekkora margin/numerikus eltérés van.

**Threshold döntésre a spike után:**
- Ha a 2. lépés packing-density-je < 5%-kal rosszabb mint a jelenlegi solver, és a 3-4. lépés a jagua-rs szinten átmegy → **megéri saját optimalizálót építeni a jagua-rs köré (i + iv + v + vi útvonal), Sparrow csak inspirációként**.
- Ha a 3. lépés *jagua-rs szintjén* törik → **a jagua-rs irányt el kell vetni**, irány: saját CDE továbbfejlesztés, esetleg `gdrr-2bp` (ugyanezen szerző guillotine-2BP Rust kódbázisa) bizonyos eseteire.
- Ha a 5. lépés runtime-ja és minősége nagyon rossz → a cavity-prepack koncepció önmagában éven át tartó probléma; akkor mérlegelendő, hogy a part-in-hole nestinget *opcionális, off-by-default* feature-ként szállítod.

**2. fázis — implementáció** (a spike után, ~3-4 hónap):
- Saját Rust crate jagua-rs `bpp` fölött (FFD/LBF builder + separator-stílusú overlap-feloldó kereső).
- Cavity-prepack réteg.
- C# / külső API (a SparrowGH-tól eltérően nem subprocess+JSON, hanem stabil FFI vagy gRPC).
- Pontos exact-NFP záróvalidáció és margin-pricing.

## Caveats
- **Kódszintű hozzáférési korlát:** a `coroush/sparrow` fork `src/`-jét és `Cargo.toml`-ját nem sikerült közvetlenül beolvasni (GitHub fetch-permission limit). A BPP-mód kódszintű részletei (FFD vs. valódi inter-bin perturbáció; rectangular-only feltevés helye) **bizonyítatlanul valószínűek** maradnak amíg a repo lokálisan ki nem kerül klónozásra. A spike első napja erre menjen.
- **Forum-alapú jelek:** az "inter bin moves" említés egyetlen felhasználó (`laurent_delrieu`, McNeel discourse, 2026. ápr. 13.) post-jából származik, nem kódolvasásból.
- **jagua-rs gyors fejlődik:** v0.7.0 ~27 napja release (2026. április 23.), az `mspp` (Multi-Strip) modul nemrég merge-elve a főágba — pontos CI-szám és dátum nem ellenőrzött, csak az látható, hogy az `mspp` modul már jelen van a `probs/` alatt. Az API instabilitása valós kockázat — pin-elj egy verziót és csak tudatosan upgrade-elj.
- **CDE túl-konzervativitás:** a paper §6 explicit mondja, hogy a jagua-rs *számszaki biztonság miatt* hajlamos kicsit nagyobb távolságot követelni, mint az exact arithmetic — emiatt a pontos exact-validátor megtartása nemcsak QA, hanem packing-density nyerő funkció is.
- **Item-hole hiánya forrással:** a jagua-rs item-szintű lyuk-támogatás hiánya a README design-listából (csak container) következtetett, NEM forráskódból. Mielőtt a cavity-prepack komplex réteget elkezded építeni, ellenőrizd 30 perc alatt a `entities/item.rs` és `geometry/primitives/s_polygon.rs` fileokat, hogy nem támogat-e item-szintű inner-ring poligont közvetlenül (ami megkönnyítené a part-in-hole nesting saját megoldását).
- **Mintavételi sebesség-szám:** korábbi források ~milliós nagyságrendű collision query-per-second-et említenek a jagua-rs-re, de a konkrét számok (pl. SWIM instance-en mért érték) nem ellenőrzöttek a paper publikus változatából, ezért a runtime-tervezésnél saját benchmark futtatása ajánlott a Lépés 1 részeként.