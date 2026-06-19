# Q55D — Szigorított free-space preservation

## Goal

A solver ne csak **valid** pozíciókat keressen, hanem olyanokat, amelyek után **értékes, egybefüggő,
később is pakolható** szabad terület marad. A Q54 area-only free-space score nem elég: nem elég a szabad
terület **mérete**, mérni kell a **használhatóságát** a következő critical/medium alkatrészhez. Kötelező
új fogalom a `FreeSpaceSlot`, és egy szigorú scoring elv: ha egy candidate feldarabolja az utolsó nagy,
critical-fit szabad sávot, **nagy büntetést** kap.

## Háttér

A Q54D rangsor a legnagyobb edge-connected szabad terület **területét** maximalizálja — de a referencia
szerint a kulcs az, hogy a következő critical-nak **beférhető** sáv maradjon (aspektus + befértetés), ne
csak nagy, de szétszabdalt/rossz-arányú terület. A Q55D ezt szigorítja.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs`
  - `largest_edge_connected_free_area` → `FreeSpaceSlot`-okat adó analízis
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `sheet_freespace_score` → szigorított, slot-alapú; a candidate-rangsor sorrendje
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — next-critical min-width / long-span
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- A free-space score **csak rangsoroló proxy** — a CDE a collision truth.
- Ne maximalizáld vakon a legnagyobb téglalapot (a beszélgetés szerinti veszély): a slot-score egy
  komponens, az interlock/density tie-breaker még megmarad.
- Continuous rotation, nincs NFP, nincs bbox-corner primary, nincs hardcoded 3+3.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.

## Feladat

### `FreeSpaceSlot` fogalom

```rust
struct FreeSpaceSlot {
    area: f64,
    bbox_w: f64,
    bbox_h: f64,
    touches_edge: bool,
    touched_edges: Vec<Edge>,
    component_id: usize,
    fragmentation_score: f64,
    can_fit_next_critical_min_width: bool,
    can_fit_next_critical_long_span: bool,
    estimated_next_critical_fit_margin: f64,
}
```

### Candidate ranking sorrend (kötelező)

```
1. CDE feasibility / repairability
2. role suitability
3. next-critical fit potential
4. largest edge-connected free component
5. fragmentation penalty
6. band aspect ratio
7. density/interlock tie-breaker (utolsó)
```

### Szigorú scoring elv

Ha egy candidate elfoglalja/feldarabolja az **utolsó** olyan nagy, egybefüggő szabad sávot, amelybe a
következő critical part még beférhetne → **nagy büntetés**. Jó: valid + meghagy egy nagy, edge-connected,
critical-fit szabad régiót.

### DoD

- Szintetikus teszt: két anchor/interlock elhelyezés — (A) lokálisan sűrűbb, de feldarabolja a szabad
  teret; (B) kissé kevésbé sűrű, de meghagy egy nagy edge-connected critical slotot → a solver **B-t**
  választja.
- LV8 mechanizmus-teszt: az első két nagy után a diagnosztika: `largest_edge_connected_free_slot`,
  `can_fit_next_critical = true`, `estimated_next_critical_fit_margin > 0`. A BandInsert előtt:
  `band_slot_found = true`, `band_slot_can_fit_critical = true`.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml slot`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55d_strict_freespace_preservation.md`

## Rollback

- Ha a szigorított scoring regressziót okoz (rosszabb pakolás), gate off → a Q54D area-only rangsor érintetlen.
- A slot-analízis költsége korlátozott (a Q54D grid felbontásán); ha drága, a critical fázisra szűkítve.
