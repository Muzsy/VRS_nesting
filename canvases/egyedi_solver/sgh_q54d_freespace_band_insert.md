# Q54D — Free-space-preserving score + band-insert + sheet-close guard

## Goal

A makró-stratégia, amely a Q54A–C mikró-mechanizmust **referencia-szerű layout-tervezéssé** teszi: az
anchor és interlock úgy üljön, hogy a **következő** critical-nak maradjon hasznos, edge-connected szabad
tér; a harmadik (`BandInsert`) a megmaradt sávba kerüljön (a tábla aljához/teteéhez igazítva, **nem** az
első kettőhöz); és egy **sheet-close guard** ne engedjen új sheetet/fillert, amíg geometriailag alkalmas
nagy szabad régió maradt egy következő critical-nak.

## Háttér

A felhasználói stratégiai meglátás: a solver jelenleg „csak valahova validan" rak, nem **free-space-
preserving** módon. A referencia LV8-tábla nem interlockot csinál, hanem layout-tervezést: kritikus
alkatrész → élhez/sarokhoz igazítva → hasznos szabad régió megőrizve → következő. A Q54D ezt a hiányzó
döntési réteget adja, **olcsó proxyval** (nem exact free-space dekompozíció, nem NFP). A „használható
üres tér" mindig attól függ, milyen alkatrészt akarunk még elhelyezni → **profil/prioritás-tudatos**.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (Q54A state) — ide kerül a free-space proxy
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `try_admit_critical`, `build_critical_aware_seed` (sheet-close döntés), `density_candidate_score` rangsor
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `PartShapeProfile` (következő critical osztály mérete)
- `rust/vrs_solver/src/optimizer/sparrow/density.rs` — candidate rangsor kiegészítése
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- CDE marad a collision truth; a free-space score **csak rangsoroló proxy**, nem collision/validáció.
- Tilos NFP / pairwise NFP; tilos bbox collision shortcut a CLEARANCE-hez (a free-space proxy durva
  occupancy lehet, de nem helyettesíti a CDE-t).
- Continuous rotation marad continuous.
- Cavity/hole nincs a fő solverben.
- Nincs `part_id` hack, **nincs hardcoded 3+3**, nincs „N db kell egy táblára" előrejelzés — a sheet-close
  guard geometriai alkalmasságot mér, nem darabszámot.
- Ne maximalizáld vakon a legnagyobb üres téglalapot (a beszélgetés szerinti veszély): a free-space score
  egy komponens a candidate rangsorban, nem egyetlen új szabály.
- Gated (`VRS_SHEET_BUILDER_SKELETON`); default off → byte-azonos.

## Feladat

### Olcsó free-space proxy (a sheet_skeleton.rs-ben)

- Durva occupancy (≈25–50 mm cella, env-állítható): a sheet szabad celláiból a legnagyobb **edge-connected**
  szabad komponens; profil-tudatos kérdés: „befér-e a következő critical osztály min-width oriented bbox-a
  ebbe a komponensbe?" (nem exact, csak rangsoroló).
- `free_space_quality(skeleton_state, sheet, next_critical_profile) -> score`.

### Candidate rangsor kiegészítése

- A Q54B/C candidate-ek pontszáma: CDE-clearance (elsődleges) **+** free-space-minőség (másodlagos) —
  edge-anchored/sáv-megőrző jelölt jobb, központi-blokkoló rosszabb. A centroid-közelség önmagában ne
  domináljon.

### BandInsert szerep megvalósítása

- A `BandInsert` szerepű critical a megmaradt edge-connected sávba, táblaélhez igazítva, continuous
  rotation — **nem** az anchor/interlock párhoz illesztve.

### Sheet-close guard

- Új sheet nyitása / structural+filler fázis indítása előtt: ha van geometriailag alkalmas nagy
  edge-connected szabad régió egy **következő** critical-hoz, ne zárd le a critical fázist. A döntés a
  free-space proxyból + a maradék critical queue profiljából adódik; phase-close reason logolva.

### DoD

- Unit teszt: a free-space proxy egy nagy összefüggő szabad sávot magasabbra értékel, mint több apró
  szétszabdalt rést (azonos terület mellett).
- Unit teszt: szintetikus eset, ahol naiv (centroid-közeli) elhelyezés elrontja a harmadik critical
  helyét, free-space score-ral viszont marad neki edge-connected sáv → band-insert sikeres.
- Unit teszt: sheet-close guard nem zár, amíg alkalmas nagy szabad régió van; zár, ha nincs.
- Diagnosztika: `free_space_proxy_before/after`, `largest_free_component`, `band_insert_success`,
  `sheet_close_reason`.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md`

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md
```

## Rollback

- Ha a free-space score vagy a sheet-close guard regressziót okoz, gate off → a Q54A–C és a Q51/Q52 út
  érintetlen.
- Ha a proxy túl drága, csökkentsd a rácsfelbontást vagy korlátozd a critical fázisra; sosem váljon
  collision-igazsággá.
