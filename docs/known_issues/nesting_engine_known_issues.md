# docs/nesting_engine/known_issues.md

> Élő dokumentum. Az auditok által feltárt, de még nem kezelt problémák
> nyilvántartása. Ez NEM a fejlesztési backlog (`canvases/nesting_engine/
> nesting_engine_backlog.md`), hanem a tech debt és spec drift registry.
>
> Állapotok: OPEN | IN_PROGRESS (task slug) | RESOLVED (task slug, dátum)
> Azonosító-konvenció: KI-NNN (Known Issue, sorszám)

---

## P2 — Közepes prioritás

### KI-007 tolerance_policy integer-only allitas vs aktiv f64 geometriadontesek
**Allapot:** IN_PROGRESS (nfp_concave_integer_union)  
**Forras:** Doc-code drift audit, 2026-02-24  
**Terulet:** `docs/nesting_engine/tolerance_policy.md`, `rust/nesting_engine/src/geometry/offset.rs`, `rust/nesting_engine/src/feasibility/narrow.rs`, `rust/nesting_engine/src/geometry/pipeline.rs`

A policy szoveg szerint az egesz aritmetika integer-determinisztikus, es a
floating-point kerekitesi nemdeterminizmus kizarhato. A kodban ugyanakkor aktiv
f64 alapu geometriai predikatumok futnak (offset winding helper-ek, i_overlay
FloatPredicate overlay containment/intersection, geo sweep-line self-intersection).
Ez specifikacio-kod szintu eltérés.

**Scope update (2026-02-25):** az `nfp_concave_integer_union` task csak a
`rust/nesting_engine/src/nfp/concave.rs` stable baseline union float driftjet
kezeli. Az `offset` / `feasibility` / `pipeline` tovabbi f64 kodutvonalai kulon
feladatban maradnak.

**Reszleges feloldas (2026-02-25, verify PASS):** a concave stable baseline
union utvonalrol a `FloatOverlay` kikerult, integer-only `i_overlay::core::overlay::Overlay`
utvonal aktiv, es a visszacsuszast kulon guard teszt (`nfp_no_float_overlay.rs`)
vedi. A KI-007 tobbi, nem-concave resze tovabbra is nyitott.

**Javasolt DoD:**  
- A policy pontositsa, hogy hol kotelezo integer aritmetika es hol engedett f64.  
- A feasibility/pipeline f64 reszekre explicit determinisztikus policy keruljon
  (platform, epsilon/tolerancia, rendezesi szabalyok).  
- Adjunk dedikalt regresszios tesztet a float erintett kodutvonalakra.

---

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

### KI-008 architecture.md modul-map elavult ("planned"), mikozben modulok aktivak
**Allapot:** OPEN  
**Forras:** Doc-code drift audit, 2026-02-24  
**Terulet:** `docs/nesting_engine/architecture.md`, `rust/nesting_engine/src/{feasibility,placement,multi_bin,export}`

Az architecture dokumentumban a `feasibility/`, `placement/`, `multi_bin/`,
`export/` modulok "planned" allapotban szerepelnek, mikozben a kodban ezek mar
leteznek es aktivan hasznaltak. Ez felrevezeto lehet uj feladatok scope-olasanal.

**Javasolt DoD:**  
- `architecture.md` module map frissitese a tenyleges allapotra.  
- "planned" csak valoban nem implementalt teruletre maradjon.

---

### KI-010 tolerance_policy OffsetError szekcio elter a kodtol
**Allapot:** OPEN  
**Forras:** Doc-code drift audit, 2026-02-24  
**Terulet:** `docs/nesting_engine/tolerance_policy.md`, `rust/nesting_engine/src/geometry/offset.rs`, `rust/nesting_engine/src/geometry/pipeline.rs`

A policy tablazat `SelfIntersection` variansrol es altalanos "minden OffsetError
fatal" viselkedesrol beszel. A kodban az `OffsetError` enum jelenleg
`HoleCollapsed` + `ClipperError`; a self-intersection kezeles pipeline szinten,
status/diagnosztika alapon tortenik. A dokumentacio emiatt pontatlan.

**Javasolt DoD:**  
- `tolerance_policy.md` OffsetError szekcio frissitese a valos enumra es
  pipeline status policy-ra (`ok` / `hole_collapsed` / `self_intersect` / `error`).  
- A policy hivatkozzon a megfelelo unit tesztekre.

---

## Lezárt issue-k (RESOLVED)

### KI-006 `determinism_hash` canonicalization: normativ JCS spec vs jelenlegi implementacio
**Allapot:** RESOLVED (`full_pipeline_determinism_hardening`, 2026-03-08)  
**Eredeti forras:** Doc-code drift audit, 2026-02-24  
**Terulet:** `docs/nesting_engine/json_canonicalization.md`, `rust/nesting_engine/src/export/output_v2.rs`, `scripts/smoke_nesting_engine_determinism.sh`

Lezaras indoka: a normativ canonicalization dokumentacio repo-native contractra lett
igazitva (`nesting_engine.hash_view.v1` hash-view + kompakt, key-sorted JSON byte forma),
determinism evidence tesztekkel es 10-run full-output smoke gate-tel.

### KI-009 json_canonicalization.md hibas hivatkozas nem letezo szerzodes fajlra
**Allapot:** RESOLVED (`full_pipeline_determinism_hardening`, 2026-03-08)  
**Eredeti forras:** Doc-code drift audit, 2026-02-24  
**Terulet:** `docs/nesting_engine/json_canonicalization.md`, `docs/nesting_engine/io_contract_v2.md`

Lezaras indoka: a canonicalization dokumentum hivatkozasa a letezo
`docs/nesting_engine/io_contract_v2.md` fajlra lett zarva.

### KI-002 Stock clearance szabály: margin vs. margin+kerf/2
**Állapot:** RESOLVED (`nesting_engine_spacing_margin_bin_offset_model`, 2026-02-27)  
**Eredeti forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `rust/nesting_engine/src/geometry/pipeline.rs`, `docs/nesting_engine/io_contract_v2.md`

Lezárás indoka: a clearance modell átállt az új kánonra
(`inflate_delta = spacing/2`, `bin_offset = spacing/2 - margin`), a korábbi
`margin + kerf/2` összemosás megszűnt.

### KI-004 tolerance_policy.md és a tényleges HOLE_COLLAPSED kezelés eltér
**Állapot:** RESOLVED (`nesting_engine_spacing_margin_bin_offset_model`, 2026-02-27)  
**Eredeti forrás:** Fázis 1 audit, 2026-02-23  
**Terület:** `docs/nesting_engine/tolerance_policy.md`, `rust/nesting_engine/src/geometry/pipeline.rs`

Lezárás indoka: a policy dokumentáció már explicit tartalmazza a
`HOLE_COLLAPSED` diagnosztika + outer-only fallback viselkedést, valamint a
`self_intersect` pipeline-szintű, fatal kezelést.

---

## Karbantartási szabály

Amikor egy issue canvas+yaml feladattá válik, az állapota `IN_PROGRESS (task_slug)`-ra
vált. Amikor a task reportja PASS státuszú és a verify.sh gate zöld, az issue
`RESOLVED (task_slug, dátum)`-ra vált, és átkerül a "Lezárt" szekcióba.
