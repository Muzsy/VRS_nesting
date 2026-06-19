# Q55C — BandInsert candidate generator

## Goal

A harmadik nagy critical alkatrészt **nem** szomszéd-feature-höz kell illeszteni, hanem a megőrzött,
értékes, edge-connected **szabad sávba** kell helyezni — táblaélhez igazítva, finom continuous rotációval.
Ez a Q54E által azonosított pontos lever: szerep-specifikus band-insert generátor.

## Háttér

A Q54 free-space proxyja (`largest_edge_connected_free_area`) megméri a legnagyobb edge-connected szabad
komponens **területét**, de nem ad **pozíciót/orientációt** a 3. nagy partnak. A Q55C a band-insert
generátort adja: a legértékesebb szabad sávot megtalálja, ellenőrzi a befértetést a part
min-width/long-span proxyja alapján, és edge-aligned pozíciókat generál a sáv mentén.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs`
  - `largest_edge_connected_free_area` (Q54D) → kibővítés: a legjobb sáv **bbox + élek** visszaadása
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs`
  - új `band_insert_candidates(...)` (role-specifikus, a Q55B routingból hívva)
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — a BandInsert ág bekötése
- `rust/vrs_solver/src/sheet.rs` — `SheetShape`
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- Continuous rotation marad continuous (a band-aligned pozíció finom continuous rotációval refine-olt).
- Nincs NFP, nincs bbox-corner primary, nincs hardcoded `Lv8`/3+3.
- CDE a collision truth; final acceptance csak CDE-valid.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.
- A free-space sáv **proxy** (occupancy grid) — nem collision igazság; a CDE dönt.

## Feladat

### Band-insert generátor

1. Keresse meg az aktuális sheet legértékesebb **edge-connected szabad sávját** (a Q54D occupancy grid
   legnagyobb border-érintő komponensének **bbox-a + érintett élei**).
2. Vizsgálja, hogy a következő critical part **min-width / long-span proxy** alapján beférhet-e (a sáv
   bbox vs a part oriented bbox).
3. Generáljon **edge-aligned pozíciókat** a sáv mentén (a part hosszú éle a sáv hosszú éléhez / a
   táblaélhez igazítva), 180° flip variánsokkal.
4. **Continuous local rotation refine** (a Q52 `density_rotation_candidates` mintára).
5. **CDE final validation** — csak CDE-clear/feasible eredmény fogadható el.

### Diagnosztika (kötelező)

```
band_slot_found
band_slot_bbox (w, h)
band_slot_can_fit_critical
band_insert_candidates_generated / accepted
band_insert_rejection_reason
```

### DoD

- Unit teszt: adott szabad sáv + egy beférő part → a generátor edge-aligned candidate-eket ad a sáv
  mentén (nem szomszéd-feature illesztés); a refined rotáció continuous.
- LV8 mechanizmus-teszt (a fő gate, a Q55F-fel közös): 6-big spacing 5 → legalább egy sheeten
  `Anchor + Interlock + BandInsert`, `max_big_per_sheet >= 3`, CDE-valid.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md`

## Rollback

- Ha a band-insert generátor regressziót okoz, gate off → a Q54 viselkedés érintetlen.
- Ha a befértetés-proxy téved (CDE elveti), az csak rangsoroló — a CDE a végső szűrő; a generátor
  fallbackel a meglévő feature-pathra.
