# `jagua-rs` + saját optimizer átállás — pipálható task checklist
**Projekt:** DXF Nesting / VRS_nesting  
**Kapcsolódó bontás:** `jagua_optimizer_canvas_yaml_runner_task_bontas.md`  
**Cél:** a JG-00…JG-27 munkalánc kézi/agent-alapú előrehaladásának ellenőrzése pipálható Markdown checklisttel.  

---

## Használati szabály

- Egy task csak akkor tekinthető késznek, ha **minden kötelező checkbox** ki van pipálva, vagy az eltérés explicit `BLOCKER / DEVIATION` megjegyzéssel szerepel a task reportban.
- A pipálás nem helyettesíti a repo gate-et: a `./scripts/verify.sh --report ...` futtatás minden task végén kötelező.
- Invalid nesting layout soha nem lehet PASS, akkor sem, ha a task többi része elkészült.
- Phase 1–2 alatt a hole-os itemeket nem szabad csendben kezelni vagy eldobni.
- Phase 3-ban cavity-prepack után expansion + exact final validation kötelező.

---

## Globális master checklist

- [ ] A teljes task lánc aktuális státusza frissítve lett.
- [ ] Minden elindított tasknak van canvas fájlja.
- [ ] Minden elindított tasknak van goal YAML fájlja.
- [ ] Minden elindított tasknak van runner promptja.
- [ ] Minden elindított tasknak van saját checklist fájlja a repo-ban.
- [ ] Minden elindított tasknak van report fájlja.
- [ ] Minden lezárt tasknak van `.verify.log` fájlja.
- [ ] A dependency sorrend nincs megsértve.
- [ ] A phase gate-eknél készült explicit PASS / REVISE / STOP döntés.
- [ ] A régi backends útvonalak regressziója minden integrációs fázis után ellenőrizve lett.
- [ ] A benchmark logok mentése következetes.
- [ ] A release döntés nem tartalmaz ellenőrizetlen feltételezést.

---

## Phase gate checklist

### Gate 0 — Integrációs döntés

- [ ] JG-00 elkészült.
- [x] JG-01 elkészült.
- [ ] JG-02 elkészült.
- [ ] JG-03 előfeltételei tiszták.
- [ ] Nincs build/licenc/API showstopper.
- [ ] Döntés: Phase 1 indítható.

### Gate 1 — Rectangular multi-sheet viability

- [ ] JG-03…JG-14 elkészült.
- [ ] Hole gate működik.
- [ ] Rectangular multi-sheet valid layoutokat ad.
- [ ] Exact final validation minden elfogadott layouton PASS.
- [ ] Phase 1 benchmark report elkészült.
- [ ] Döntés: Phase 2 indítható vagy Phase 1 revise szükséges.

### Gate 2 — Irregular/remnant viability

- [ ] JG-15…JG-20 elkészült.
- [ ] Irregular boundary validation működik.
- [ ] Margin kezelés konzervatív és dokumentált.
- [ ] Rectangular regresszió nincs.
- [ ] Phase 2 benchmark report elkészült.
- [ ] Döntés: Phase 3 indítható vagy Phase 2 revise szükséges.

### Gate 3 — Cavity-prepack viability

- [ ] JG-21…JG-25 elkészült.
- [ ] Hole metadata nem vész el.
- [ ] Macro-part expansion működik.
- [ ] Darabszám/instance consistency PASS.
- [ ] Exact final validation PASS nélkül nincs sikeres layout.
- [ ] Döntés: integráció/release gate indítható.

### Gate 4 — Integration/release closure

- [ ] JG-26 elkészült.
- [ ] JG-27 elkészült.
- [ ] Új backend/profil választható.
- [ ] Régi backendek smoke/regresszió PASS.
- [ ] Záró benchmark és döntési report elkészült.
- [ ] Döntés: continue / revise / stop.

---

## Taskonkénti checklist

### JG-00 — `jagua_optimizer_t00_task_scaffold_and_master_runner`

**Phase:** Phase 0 / scaffold  
**Cél:** A teljes munkalánc task-indexének és master runnerének létrehozása.  
**Függőség:** —  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Megnyitva és ellenőrizve: AGENTS.md, docs/codex/overview.md, docs/codex/yaml_schema.md, docs/codex/report_standard.md, docs/qa/testing_guidelines.md.
- [ ] Létrejött a canvas package a megadott sluggal.
- [ ] Létrejött a goal YAML a kötelező `steps` sémával.
- [ ] Létrejött a runner prompt a repo-konvenciók szerint.
- [ ] Létrejött a task index `JG-00…JG-27` teljes felsorolással.
- [ ] A task index tartalmaz dependency graphot és critical pathot.
- [ ] A task index tartalmaz phase gate-eket.
- [ ] A master runner önállóan futtatható feladatként van megírva.
- [ ] Nem módosult production solver-kód.
- [ ] Létrejött a checklist és report fájl.
- [ ] Lefutott a `./scripts/verify.sh --report ...` wrapper.
- [ ] A verify log mentve lett a megfelelő report útvonalra.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-01 — `jagua_optimizer_t01_repo_and_source_audit`

**Phase:** Phase 0 / audit  
**Cél:** Repo + jagua-rs + Sparrow valóságellenőrzés.  
**Függőség:** JG-00  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [x] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [x] Repo szabályfájlok újraolvasva a task elején.
- [x] `rust/vrs_solver` jelenlegi állapota auditálva.
- [x] `docs/solver_io_contract.md` releváns szerződései auditálva.
- [x] Python runner/adapter boundary auditálva: `vrs_solver_runner.py`, `solver_adapter.py`.
- [x] Meglévő cavity pipeline auditálva: `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py`.
- [x] `jagua-rs` dependency és használhatóság ellenőrizve a valós Cargo/workspace alapján.
- [x] Sparrowból átvehető optimizer/search minták külön táblában rögzítve.
- [x] Rectangular, irregular/remnant és hole/cavity kockázatok külön bontva.
- [x] Licenc/dependency/build kockázatok dokumentálva.
- [x] A report konkrét fájl- és kód-anchorokat tartalmaz, nem csak általánosságokat.
- [x] Blokkolók és döntési javaslatok külön szakaszban szerepelnek.
- [x] Repo gate / verify lefuttatva és logolva.

**Záró mezők:**

- [x] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-02 — `jagua_optimizer_t02_solver_module_scaffold`

**Phase:** Phase 0 / architecture  
**Cél:** A monolit `rust/vrs_solver/src/main.rs` moduláris előkészítése viselkedésváltozás nélkül.  
**Függőség:** JG-01  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Repo szabályfájlok újraolvasva.
- [ ] A jelenlegi `main.rs` viselkedése baseline-ként dokumentálva.
- [ ] Modulstruktúra terv rögzítve: io, geometry, sheet, item, adapter, optimizer, validation.
- [ ] Refaktor csak a YAML outputs listában engedélyezett fájlokat érintette.
- [ ] `main.rs` CLI/orchestration szerepre szűkítve, ha a task ezt engedi.
- [ ] A meglévő input/output contract nem változott kompatibilitást törően.
- [ ] Smoke inputokon a régi output szemantikailag változatlan.
- [ ] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] Unit/smoke tesztek PASS, ahol vannak.
- [ ] Minden viselkedésváltozás explicit NO/YES táblában dokumentált.
- [ ] Report tartalmaz diff összefoglalót.
- [ ] Repo verify lefuttatva és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-03 — `jagua_optimizer_t03_outer_only_contract_and_hole_gate`

**Phase:** Phase 1 / rectangular preflight  
**Cél:** Outer-only Phase 1 contract és hole gate.  
**Függőség:** JG-02  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Phase 1 capability policy dokumentálva: rectangular multi-sheet, hole nélkül.
- [ ] Input contract bővítés rögzítve: `solver_profile`, `capabilities`, `unsupported_reason`.
- [ ] Hole-os part detektálása implementálva vagy explicit tervezve a megfelelő boundaryn.
- [ ] Hole-os input Phase 1-ben determinisztikus unsupported/error státuszt ad.
- [ ] Nincs silent geometry loss: hole kontúrok nem tűnnek el észrevétlenül.
- [ ] Container hole/remnant kezelés nincs véletlenül engedélyezve.
- [ ] Python runner/validator oldali státuszkezelés ellenőrizve.
- [ ] Rectangle-only korábbi smoke nem törik.
- [ ] Unsupported státusz reportban és/vagy output metában megjelenik.
- [ ] Negatív fixture készült hole-os parttal.
- [ ] Pozitív fixture készült outer-only parttal.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-04 — `jagua_optimizer_t04_jagua_adapter_contract_poc`

**Phase:** Phase 1 / backend adapter  
**Cél:** Vékony JaguaAdapter contract és proof-of-contact.  
**Függőség:** JG-02, JG-03  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Adapter trait/contract leírva saját publikus modellben.
- [ ] Jagua-specifikus típusok nem szivárognak át az optimizer publikus modelljébe.
- [ ] VRS polygon → jagua geometry konverzió első verziója elkészült vagy spike-olva.
- [ ] Egyszerű item-item collision smoke valid esetet felismer.
- [ ] Egyszerű item-item collision smoke invalid/overlap esetet felismer.
- [ ] Item-sheet / boundary jellegű smoke lefut, ha a jagua API támogatja.
- [ ] f32/f64 vagy unit konverziós kockázat dokumentálva.
- [ ] Adapter hibakezelés explicit: unsupported, conversion_error, backend_error.
- [ ] A POC nem köt be még teljes optimizer-loopot.
- [ ] Cargo build PASS.
- [ ] Report tartalmaz API-megfigyeléseket és ismert korlátokat.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-05 — `jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures`

**Phase:** Phase 1 / rectangular sheets  
**Cél:** Rectangular sheet provider és determinisztikus outer-only fixture pack.  
**Függőség:** JG-03, JG-04  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Rectangular sheet provider szerződése dokumentált.
- [ ] Stock quantity → expanded sheet lista determinisztikus.
- [ ] Stable `sheet_index` mapping ellenőrizve.
- [ ] Margin/gap alapmezők fixture-ben szerepelnek.
- [ ] Smoke fixture outer-only, kicsi és gyors.
- [ ] Small realistic fixture outer-only, több quantity-vel.
- [ ] Medium fixture előkészítve vagy placeholderrel dokumentálva.
- [ ] Fixture-ök a solver IO contract szerint validak.
- [ ] Validator PASS a valid fixture-ökre.
- [ ] Invalid fixture-ek nem mennek át PASS-ként.
- [ ] Reportban szerepel a fixture lista és futtatási parancs.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-06 — `jagua_optimizer_t06_item_geometry_store_and_rotation_cache`

**Phase:** Phase 1 / item model  
**Cél:** ItemGeometryStore, instance expansion és rotációs cache outer-only polygonokra.  
**Függőség:** JG-05  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Item instance id szabály dokumentálva.
- [ ] Quantity expansion determinisztikus és tesztelt.
- [ ] Area/bbox számítás rögzítve.
- [ ] Allowed rotations ordering stabil.
- [ ] 0/90/180/270 rotációk regresszió nélkül működnek.
- [ ] Unsupported rotáció explicit hibát vagy unsupported státuszt ad.
- [ ] Rotated proxy geometry cache működik.
- [ ] Exact geometry külön megőrzése dokumentálva.
- [ ] Azonos input + seed azonos instance listát ad.
- [ ] Unit tesztek vagy smoke tesztek PASS.
- [ ] Report tartalmaz cache és determinism megjegyzést.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-07 — `jagua_optimizer_t07_layout_state_and_candidate_model`

**Phase:** Phase 1 / optimizer core  
**Cél:** Optimizer állapotmodell és candidate move skeleton.  
**Függőség:** JG-06  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] LayoutState modell létrejött vagy részletesen definiálva.
- [ ] Placed/unplaced állapot külön kezelve.
- [ ] PlacementTransform modell tartalmaz translation + rotation adatot.
- [ ] CandidateMove modell tartalmaz legalább move/reinsert/rotate alapot.
- [ ] ObjectiveBreakdown skeleton létrejött.
- [ ] State diagnosztikába szerializálható.
- [ ] Output contract v1 kompatibilis maradt.
- [ ] State unit tesztek PASS.
- [ ] Invalid/partial state nem jelenik meg sikeres final layoutként.
- [ ] Determinism mezők / seed kezelés előkészítve.
- [ ] Report tartalmaz állapotdiagramot vagy rövid modellt.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-08 — `jagua_optimizer_t08_initial_construction_placer_v1`

**Phase:** Phase 1 / initial placement  
**Cél:** Első construction placer: rendezés + candidate-point próbák jagua collision checkkel.  
**Függőség:** JG-07, JG-04  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Initial item ordering dokumentálva: area/bbox/egyéb tie-breaker.
- [ ] Rectangular candidate point generálás V1 implementálva.
- [ ] Jagua collision check minden candidate próbánál használva.
- [ ] Elhelyezhetetlen item unplaced státuszba kerül, nem tűnik el.
- [ ] Small fixture minden partja validan elhelyezhető vagy explicit okkal unplaced.
- [ ] Medium fixture legalább részleges, de valid layoutot ad.
- [ ] Invalid layout soha nem kap successful PASS státuszt.
- [ ] Exact validator PASS az elfogadott placementekre.
- [ ] Runtime/time limit nem végtelen ciklusos.
- [ ] Candidate count / rejection reason legalább részben reportolva.
- [ ] Report tartalmaz példafuttatást.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-09 — `jagua_optimizer_t09_exact_validation_bridge_and_metrics`

**Phase:** Phase 1 / validation  
**Cél:** Rust solver output és Python exact validator/report metrikák zárása.  
**Függőség:** JG-08  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Rust output tartalmazza a szükséges layout mezőket.
- [ ] Python exact validator bekötés vagy bridge ellenőrizve.
- [ ] Valid fixture PASS státuszt ad.
- [ ] Overlap fixture FAIL státuszt ad.
- [ ] Out-of-sheet fixture FAIL státuszt ad.
- [ ] Invalid layout nem lehet successful.
- [ ] Report metrikák szerepelnek: runtime, placed, unplaced, used_sheets, utilization.
- [ ] Validation status outputban és reportban is látható.
- [ ] Partial success fogalma egyértelműen elkülönül a valid successtől.
- [ ] Regression smoke futtatva.
- [ ] Report tartalmaz parancsokat és kimenet-részleteket.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-10 — `jagua_optimizer_t10_repair_search_loop_v1`

**Phase:** Phase 1 / repair search  
**Cél:** Sparrow-elvű repair-search V1.  
**Függőség:** JG-09  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] MoveGenerator V1 elkészült: translate/reinsert/rotate legalább részben.
- [ ] RepairEngine V1 elkészült vagy világosan behatárolt.
- [ ] StoppingPolicy tartalmaz time limitet.
- [ ] StoppingPolicy tartalmaz iterációs vagy stagnálási limitet.
- [ ] Mesterségesen hibás kezdőállapotból legalább egy repair smoke valid állapotot ad.
- [ ] Ha repair sikertelen, rollback vagy explicit fail történik.
- [ ] Azonos seed determinisztikus eredményt ad.
- [ ] Time limit betartott.
- [ ] Boundary és overlap hibák külön diagnosztikában látszanak.
- [ ] Invalid layout nem mehet át successként.
- [ ] Report tartalmaz repair attempt/success/fail metrikát.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-11 — `jagua_optimizer_t11_score_model_v1`

**Phase:** Phase 1 / objective  
**Cél:** ScoreModel V1.  
**Függőség:** JG-10  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Score komponensek dokumentálva: placed area, unplaced penalty, sheet count, overlap/boundary penalty, compactness proxy.
- [ ] ObjectiveBreakdown outputban auditálható.
- [ ] Score weight defaultok dokumentálva.
- [ ] Invalid layout score-ja mindig rosszabb valid alternatívánál az erre készített tesztben.
- [ ] Unplaced penalty érdemben büntet.
- [ ] Sheet count penalty működik.
- [ ] Boundary/overlap penalty nagy súlyú.
- [ ] Compactness proxy nem írja felül a validitást.
- [ ] Score determinisztikus azonos állapotra.
- [ ] Profile default reportban szerepel.
- [ ] Score smoke tesztek PASS.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-12 — `jagua_optimizer_t12_multi_sheet_manager_v1`

**Phase:** Phase 1 / multi-sheet  
**Cél:** MultiSheetManager V1.  
**Függőség:** JG-11  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Több rectangular sheet kezelése implementálva.
- [ ] Sheet assignment determinisztikus.
- [ ] Used sheets számítása pontos.
- [ ] `sheet_index` contract nem törik.
- [ ] Unplaced kezelés több sheet mellett is helyes.
- [ ] Multi-sheet fixture valid.
- [ ] Azonos seed azonos sheet assignmentet ad.
- [ ] Sheetenkénti metrics reportolva.
- [ ] Construction/repair sheetenkénti működése ellenőrizve.
- [ ] Nincs regresszió single-sheet fixture-ön.
- [ ] Report tartalmaz multi-sheet példát.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-13 — `jagua_optimizer_t13_sheet_elimination_v1`

**Phase:** Phase 1 / sheet count reduction  
**Cél:** Sheet elimináció V1.  
**Függőség:** JG-12  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Weakest sheet kiválasztási szabály dokumentálva.
- [ ] Sheet ürítési próbák implementálva.
- [ ] Reinsert order determinisztikus.
- [ ] Sikeres elimináció esetén used_sheet_count csökken.
- [ ] Sikertelen elimináció rollbackel.
- [ ] Rollback után a valid layout nem romlik.
- [ ] Mesterséges fixture-ben legalább egy sheet eliminálható.
- [ ] Reportban attempt/success/fail metrikák szerepelnek.
- [ ] Invalid layout nem lehet eliminációs siker.
- [ ] Time limit/stopping policy figyelembe véve.
- [ ] Regression futott JG-12 fixture-ökre.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-14 — `jagua_optimizer_t14_phase1_benchmark_matrix`

**Phase:** Phase 1 / benchmark gate  
**Cél:** Rectangular multi-sheet benchmark matrix.  
**Függőség:** JG-13  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Smoke benchmark fixture fut.
- [ ] Small benchmark fixture fut.
- [ ] Medium benchmark fixture fut.
- [ ] Realistic no-hole fixture fut vagy explicit blockerrel dokumentált.
- [ ] Baseline compare lefut, ahol van értelmes baseline.
- [ ] Minden elfogadott layout exact validator PASS.
- [ ] Invalid layout automatikus FAIL.
- [ ] Metrikák rögzítve: placed, unplaced, used_sheets, utilization, runtime.
- [ ] Seed/profile/rotations/backend meta rögzítve.
- [ ] Summary JSON létrejött.
- [ ] Summary MD report létrejött.
- [ ] Phase 1 gate döntés: PASS / REVISE / STOP dokumentálva.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-15 — `jagua_optimizer_t15_irregular_sheet_capability_spike`

**Phase:** Phase 2 / irregular spike  
**Cél:** Jagua irregular/remnant sheet boundary képesség spike.  
**Függőség:** JG-14  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Phase 2 scope dokumentálva: irregular/remnant sheet, hole nélkül.
- [ ] L-shape / konkáv remnant spike fixture elkészült.
- [ ] Megvizsgálva, hogy jagua natívan tud-e irregular boundaryt.
- [ ] Boundary violation felismerése tesztelve.
- [ ] Item-item collision továbbra is működik.
- [ ] Nincs item hole vagy container hole bekeverve.
- [ ] Döntési ág rögzítve: natív jagua boundary vagy saját boundary validator + jagua item-item collision.
- [ ] Performance/kockázat röviden dokumentálva.
- [ ] NO-GO esetén alternatív terv szerepel.
- [ ] Report konkrét PASS/NO-GO döntéssel zár.
- [ ] Cargo/build/smoke PASS, ahol releváns.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-16 — `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

**Phase:** Phase 2 / irregular provider  
**Cél:** Irregular/remnant sheet provider és margin kezelés.  
**Függőség:** JG-15  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] SheetGeometry modell tartalmaz outer polygon mezőt.
- [ ] Usable polygon / margin policy dokumentálva.
- [ ] Konzervatív margin kezelés implementálva vagy explicit fallbackkel jelölve.
- [ ] L-alakú/remnant input valid.
- [ ] Túl keskeny remnant unsupported státuszt ad.
- [ ] Rectangular provider regresszió nincs.
- [ ] Shape metadata reportolva: area, bbox, usable area.
- [ ] Container hole továbbra sincs engedélyezve.
- [ ] Invalid remnant geometriák kezelése dokumentált.
- [ ] Fixture-ek futnak.
- [ ] Report tartalmaz margin utáni usable region adatokat.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-17 — `jagua_optimizer_t17_irregular_boundary_validation`

**Phase:** Phase 2 / boundary validation  
**Cél:** Irregular exact/proxy boundary validation.  
**Függőség:** JG-16  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Boundary validation policy dokumentálva.
- [ ] Boundary-touch policy dokumentálva.
- [ ] Sheeten belüli item PASS.
- [ ] Konkáv sheetből kilógó item FAIL.
- [ ] Margin-zónába lógó item FAIL vagy explicit policy szerinti státuszt ad.
- [ ] Validator smoke lefut irregular fixture-ön.
- [ ] Rectangular boundary validation regresszió nincs.
- [ ] Proxy és exact boundary check viszonya dokumentált.
- [ ] Invalid boundary layout nem lehet successful.
- [ ] Report tartalmaz negatív és pozitív példát.
- [ ] Automatikus benchmark/gate beépítve, ha releváns.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-18 — `jagua_optimizer_t18_irregular_candidate_generation`

**Phase:** Phase 2 / irregular search  
**Cél:** Boundary-aware candidate generation irregular sheetre.  
**Függőség:** JG-17  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Interior sampling determinisztikus seed alapján.
- [ ] Edge-near candidate generálás implementálva.
- [ ] Vertex-near candidate generálás implementálva.
- [ ] Neighbor-near candidate generálás implementálva vagy dokumentált fallbackkel jelölve.
- [ ] Candidate rejection reason reportolva.
- [ ] Irregular fixture legalább részleges valid elhelyezést ad.
- [ ] Invalid candidate nem kerül final layoutba.
- [ ] Candidate count metrika szerepel.
- [ ] Azonos seed determinisztikus candidate sorrendet ad.
- [ ] Rectangular candidate generation regresszió nincs.
- [ ] Report tartalmaz irregular elhelyezési példát.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-19 — `jagua_optimizer_t19_remnant_score_model_v1`

**Phase:** Phase 2 / remnant scoring  
**Cél:** Remnant/sheet cost score V1.  
**Függőség:** JG-18  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Sheet cost metadata modell dokumentálva.
- [ ] Remnant preferencia súly dokumentálva.
- [ ] Új teljes tábla nyitási büntetés dokumentálva.
- [ ] Usable-area utilization számítás működik.
- [ ] Vegyes rectangular + remnant fixture fut.
- [ ] Score breakdown magyarázható sheet választást ad.
- [ ] Invalid boundary/overlap nem lehet jó score-ral sikeres.
- [ ] Score weight defaultok reportolva.
- [ ] Rectangular-only score regresszió nincs.
- [ ] Döntési példák szerepelnek a reportban.
- [ ] Smoke/benchmark PASS.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-20 — `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

**Phase:** Phase 2 / benchmark gate  
**Cél:** Irregular/remnant benchmark matrix hole nélkül.  
**Függőség:** JG-19  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] L-shape benchmark fut.
- [ ] Konkáv remnant benchmark fut.
- [ ] Vegyes rectangular + remnant benchmark fut.
- [ ] Rectangular Phase 1 regressziós benchmark fut.
- [ ] Minden elfogadott irregular layout exact validator PASS.
- [ ] Invalid boundary layout automatikus FAIL.
- [ ] Metrikák rögzítve: placed, unplaced, used_sheets, utilization, runtime, boundary rejects.
- [ ] Seed/profile/backend meta rögzítve.
- [ ] Summary JSON létrejött.
- [ ] Summary MD report létrejött.
- [ ] Phase 2 gate döntés: PASS / REVISE / STOP dokumentálva.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-21 — `jagua_optimizer_t21_cavity_prepack_integration_audit`

**Phase:** Phase 3 / cavity audit  
**Cél:** Meglévő cavity-prepack pipeline auditja az új optimizerhez.  
**Függőség:** JG-20  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Phase 3 scope dokumentálva: cavity-prepack, nem natív hole solver.
- [ ] `worker/cavity_prepack.py` auditálva.
- [ ] `worker/cavity_validation.py` auditálva.
- [ ] `worker/result_normalizer.py` auditálva.
- [ ] Meglévő smoke_cavity vagy kapcsolódó tesztcsalád auditálva, ha van.
- [ ] Cavity contract rögzítve.
- [ ] Macro/virtual part mapping rögzítve.
- [ ] Expansion pontok rögzítve.
- [ ] Validation pontok rögzítve.
- [ ] Hiányzó bridge-ek külön listában szerepelnek.
- [ ] Kockázatok és split javaslatok szerepelnek.
- [ ] Report nem módosít production cavity logikát, ha audit-only a task.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-22 — `jagua_optimizer_t22_cavity_extraction_and_usability_filter`

**Phase:** Phase 3 / cavity model  
**Cél:** Cavity extraction + usability filter contract.  
**Függőség:** JG-21  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Hole metadata megőrzési szabály dokumentálva.
- [ ] Cavity model tartalmaz parent id, hole contour id, local geometry adatokat.
- [ ] Usable cavity számítás vagy contract elkészült.
- [ ] Min area filter működik.
- [ ] Min dimension filter működik.
- [ ] Invalid/self-problematic cavity ignored/unsupported reasonnel jelölve.
- [ ] Usable/ignored cavity count reportolva.
- [ ] Ignored reason kódok reportolva.
- [ ] Phase 1/2 core nem kap nyers hole-os partot.
- [ ] Nincs silent geometry loss.
- [ ] Fixture hole-os inputtal fut.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-23 — `jagua_optimizer_t23_single_child_cavity_prepack_v1`

**Phase:** Phase 3 / cavity prepack v1  
**Cél:** Single-child cavity-prepack.  
**Függőség:** JG-22, JG-14  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Candidate child matching szabály dokumentálva.
- [ ] Egy child egy cavitybe behelyezhető lokálisan.
- [ ] Local cavity placement validation PASS.
- [ ] Child instance kikerül a globális main solver item listából.
- [ ] Parent macro-part metadata létrejön.
- [ ] Quantity delta auditálható.
- [ ] Ha child nem fér, explicit unprepacked marad.
- [ ] Nincs duplicate child instance.
- [ ] Macro metadata reportolva.
- [ ] Rectangular main solver input outer-only marad.
- [ ] Single-child cavity fixture PASS.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-24 — `jagua_optimizer_t24_macro_part_expansion_and_final_validation`

**Phase:** Phase 3 / expansion  
**Cél:** Macro-part expansion és exact final validation.  
**Függőség:** JG-23  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Parent global transform + child local transform kompozíció implementálva.
- [ ] Expanded layout minden eredeti instance-t pontosan egyszer tartalmaz.
- [ ] No duplicate check működik.
- [ ] No missing check működik.
- [ ] Quantity mismatch FAIL státuszt ad.
- [ ] Child inside cavity validation PASS valid esetben.
- [ ] Child outside cavity validation FAIL invalid esetben.
- [ ] Exact validator PASS nélkül nincs successful report.
- [ ] Expansion bridge result_normalizer/cavity_validation felé ellenőrizve.
- [ ] Report tartalmaz expansion példát.
- [ ] Regression fut single-child fixture-re.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-25 — `jagua_optimizer_t25_cavity_prepack_main_solver_bridge`

**Phase:** Phase 3 / solver bridge  
**Cél:** Cavity-prepack és jagua optimizer end-to-end összekötése.  
**Függőség:** JG-24, JG-20  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Pipeline dokumentálva: prepack → main solver input → solve → expansion → validation.
- [ ] Rectangular + cavity E2E fixture PASS.
- [ ] Irregular + cavity smoke explicit supported/unsupported státuszt ad.
- [ ] Geometry loss nincs.
- [ ] Main solver továbbra is outer-only macro-partokat kap.
- [ ] Expansion után exact validation kötelező.
- [ ] Report tartalmaz cavity_prepack stats mezőket.
- [ ] Usable/used cavity count szerepel.
- [ ] Child placed count szerepel.
- [ ] Unsupported cavity okok szerepelnek.
- [ ] Regression Phase 1/2 fixture-ökre fut.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-26 — `jagua_optimizer_t26_quality_profiles_and_backend_selection`

**Phase:** Phase 4 / integration  
**Cél:** Új backend/profil bekötése a strategy/profile rendszerbe.  
**Függőség:** JG-14 vagy JG-20; cavity flags csak JG-25 után  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Új backend/profil neve dokumentált.
- [ ] Capability flags explicit: rectangular_only, irregular, cavity.
- [ ] Run meta tartalmazza backend nevét.
- [ ] Run meta tartalmazza profile nevét.
- [ ] Run meta tartalmazza capability flags mezőket.
- [ ] Worker backend selector nem töri a régi backendeket.
- [ ] Quality profile registry regresszió ellenőrizve.
- [ ] Cavity flags csak JG-25 után aktívak vagy explicit disabled.
- [ ] How-to-run dokumentáció frissítve.
- [ ] Régi `vrs_solver`/`sparrow`/`nesting_engine` útvonalak smoke PASS.
- [ ] Új profil smoke PASS.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

### JG-27 — `jagua_optimizer_t27_final_benchmark_and_release_closure`

**Phase:** Phase 5 / release gate  
**Cél:** Teljes lánc záró benchmark és release döntési report.  
**Függőség:** JG-26; Phase 3 blokk csak akkor, ha JG-25 kész  

**Státusz:**  
- [ ] Nem indult
- [ ] Folyamatban
- [ ] Kész
- [ ] Blocked

**Ellenőrző lista:**

- [ ] Phase 1 rectangular benchmark újrafuttatva.
- [ ] Phase 2 irregular benchmark újrafuttatva, ha Phase 2 kész.
- [ ] Phase 3 cavity benchmark újrafuttatva, ha JG-25 kész.
- [ ] Régi vrs_solver baseline compare elkészült.
- [ ] Régi nesting_engine NFP összevetés elkészült, ahol releváns és futtatható.
- [ ] Etalon reporttal összevetés dokumentálva, ha az input összevethető.
- [ ] Minden elfogadott layout exact validator PASS.
- [ ] Benchmark logok mentve.
- [ ] Known issues listája blokkoló/nem-blokkoló bontásban szerepel.
- [ ] Döntési report egyértelmű: continue / revise / stop.
- [ ] Következő munkacsomag-javaslat szerepel.
- [ ] Repo verify PASS és log mentve.

**Záró mezők:**

- [ ] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [ ] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [ ] Következő task indíthatósága egyértelműen jelölve van.

---

## Végső átadás előtti ellenőrzés

- [ ] A JG-00…JG-27 listából nincs kihagyott task.
- [ ] Minden task vagy kész, vagy explicit BLOCKED/DEFERRED státuszban van.
- [ ] Minden kész taskhoz tartozik report és verify log.
- [ ] Minden benchmarkhoz tartozik mentett log vagy summary report.
- [ ] Minden elfogadott layout exact validator PASS.
- [ ] A hole/cavity képességek nem szerepelnek támogatottként addig, amíg a megfelelő phase gate nem PASS.
- [ ] Az új backend/profil nem törte el a régi solver útvonalakat.
- [ ] A végső release döntési report elkészült.
- [ ] A következő fejlesztési irány / revise csomag kijelölve.
