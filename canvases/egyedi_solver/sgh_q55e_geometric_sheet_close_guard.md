# Q55E — Valódi (geometriai) sheet-close guard

## Goal

A solver ne váltson új sheetre, és ne kezdjen filler/medium phase-be, amíg az aktuális sheeten **reális
critical slot** van. A Q54 frontier-emelése (4) nem elég — **geometriai indok** kell: a sheet-close
előtt kötelező kiszámolni a free-space slotokat, és ha bármelyikbe a következő critical beférhet, akkor
**kötelező** band-insertet próbálni a sheet lezárása előtt.

## Háttér

A Q54 sheet-close guard csak a fail-limit (frontier) emelése volt — nincs geometriai garancia, hogy a
band-insert ténylegesen megtörtént a sheet lezárása előtt. A Q55E ezt geometriaivá teszi: a close
döntés a `FreeSpaceSlot` analízisből (Q55D) + a band-insert kísérletből (Q55C) adódik.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `build_critical_aware_seed` (a critical phase close logikája, `bpp_critical_phase_close_reason`)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — `FreeSpaceSlot` (Q55D)
- a Q55C `band_insert_candidates` / a Q55B BandInsert ág
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- Continuous rotation, nincs NFP, nincs bbox-corner primary, nincs hardcoded 3+3.
- **Nincs darabszám-előrejelzés** — a guard a free-space geometriából + a maradék critical profilból dönt.
- CDE a collision truth; final acceptance csak CDE-valid.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.

## Feladat

### Geometriai close guard

```
sheet-close (vagy filler/medium phase indítás) előtt, ha remaining_critical_exists:
    compute free-space slots (Q55D)
    if any slot can fit next critical:
        must_try_band_insert_before_sheet_close  (Q55C)
```

### Diagnosztika (kötelező)

```
sheet_close_reason
critical_slot_found_before_close
band_insert_attempted_before_close
band_insert_success
band_insert_rejection_reason
```

### Tiltott close reason a primary critical phase-ben

`frontier_fail_limit` vagy `deadline` **nem** lehet a close reason anélkül, hogy előtte szerepelne:

```
band_insert_attempted = true
VAGY
critical_slot_found_before_close = false
```

### DoD

- Szintetikus teszt: van beférő critical slot → a guard band-insertet próbál a close előtt
  (`band_insert_attempted_before_close = true`); nincs slot → `critical_slot_found_before_close = false`,
  és csak ekkor zárhat frontier/deadline okból.
- LV8 mechanizmus-teszt: a sheet-close reason a primary critical phase-ben nem `frontier_fail_limit` /
  `deadline` band-insert kísérlet nélkül.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_close`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md`

## Rollback

- Ha a geometriai guard végtelen ciklust/lassulást okoz, gate off → a Q54 frontier-guard érintetlen.
- A band-insert kísérlet budgetelt (deadline); a guard nem starve-olhatja a fallbackot.
