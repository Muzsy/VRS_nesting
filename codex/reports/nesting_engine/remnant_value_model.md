# Codex Report — remnant_value_model

**Status:** PASS

---

## 1) Meta

- **Task slug:** `remnant_value_model`
- **Kapcsolodo canvas:** `canvases/nesting_engine/remnant_value_model.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_remnant_value_model.yaml`
- **Futas datuma:** `2026-03-08`
- **Branch / commit:** `main@e709c8f`
- **Fokusz terulet:** `Mixed (Rust engine + docs + gate)`

## 2) Scope

### 2.1 Cel

1. F3-3 proxy remnant model bevezetese integer-only ppm score komponensekkel.
2. Objective sorrend rögzítése: `unplaced -> sheets_used -> remnant_value_ppm`.
3. SA cost encoding átvezetése az új P2 remnant tie-breakre.
4. Output v2 objective blokk bővítése remnant mezőkkel.
5. Targeted tesztek + gate integráció és dokumentációs szinkron.

### 2.2 Nem-cel (explicit)

1. Exact polygon-remnant topológia számítás.
2. Determinism hash canonicalization contract módosítása.
3. Új placer/search mód bevezetése.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `canvases/nesting_engine/remnant_value_model.md`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `rust/nesting_engine/src/export/output_v2.rs`
- `docs/nesting_engine/architecture.md`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/check.sh`
- `codex/codex_checklist/nesting_engine/remnant_value_model.md`
- `codex/reports/nesting_engine/remnant_value_model.md`

### 3.2 Miert valtoztak?

- A greedy réteg kapta meg a determinisztikus, integer-only proxy remnant score számítást és aggregációt.
- Az SA lexikografikus cost most explicit a remnant értéket használja a sheets tie esetén.
- Az output contract kiegészült a remnant objective mezőkkel, hash contract változtatása nélkül.
- A repo gate explicit `remnant_` targeted futással bővült.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/remnant_value_model.md` -> PASS

### 4.2 Task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml remnant_` -> PASS
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_` -> PASS
- `rust/nesting_engine/target/debug/nesting_engine nest < poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` -> PASS
  - `objective.sheets_used=2`
  - `objective.remnant_value_ppm=1402171`
  - `objective.remnant_area_score_ppm=1253800`
  - `objective.remnant_compactness_score_ppm=1797574`
  - `objective.remnant_min_width_score_ppm=1180000`

## 5) F3-3 modell nyilatkozat

Ez a szallitott F3-3 implementacio **proxy remnant model, nem exact polygon remnant**.

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| `MultiSheetResult` kiterjesztve remnant objective mezőkkel | PASS | `rust/nesting_engine/src/multi_bin/greedy.rs:183` | A result struct megkapta a `remnant_*_ppm` mezőket. | `cargo test ... remnant_` |
| Remnant score integer-only, determinisztikus, ppm skálán számol | PASS | `rust/nesting_engine/src/multi_bin/greedy.rs:215`, `rust/nesting_engine/src/multi_bin/greedy.rs:225`, `rust/nesting_engine/src/multi_bin/greedy.rs:269` | A score számítás i128/u128 aritmetikán fut, `ppm_ratio` és weighted ppm aggregációval. | `remnant_score_is_integer_and_deterministic` |
| SA objective: equal unplaced + equal sheets_used esetén remnant dönt | PASS | `rust/nesting_engine/src/search/sa.rs:353`, `rust/nesting_engine/src/search/sa.rs:388`, `rust/nesting_engine/src/search/sa.rs:798` | A cost encoding remnant-penaltyt használ, és test igazolja a remnant-preferenciát tie esetben. | `sa_prefers_higher_remnant_value_when_sheets_tie` |
| `objective` JSON blokk tartalmazza az új remnant mezőket | PASS | `rust/nesting_engine/src/export/output_v2.rs:61`, `rust/nesting_engine/src/export/output_v2.rs:214` | Az output objective blokk explicit exportálja a 4 új mezőt és külön teszt lefedi. | `remnant_objective_is_exposed_in_output_v2` |
| Targeted `remnant_` Rust tesztek PASS | PASS | `rust/nesting_engine/src/multi_bin/greedy.rs:560`, `rust/nesting_engine/src/multi_bin/greedy.rs:607`, `rust/nesting_engine/src/export/output_v2.rs:214`, `rust/nesting_engine/src/search/sa.rs:798` | Kötelező remnant fókuszú tesztek implementálva és futtatva. | `cargo test ... remnant_` |
| `scripts/check.sh` futtat targeted `remnant_` teszteket is | PASS | `scripts/check.sh:288` | A standard gate flow explicit `remnant_` futást kapott. | `./scripts/verify.sh ...` |
| `./scripts/verify.sh --report ...` PASS | PASS | `codex/reports/nesting_engine/remnant_value_model.verify.log` | A kötelező gate futás eredményét az AUTO_VERIFY blokk és log rögzíti. | `./scripts/verify.sh ...` |

## 7) Doksi szinkron

- `docs/nesting_engine/architecture.md`: SA objective sor és F3-3 proxy remnant szekció.
- `docs/nesting_engine/io_contract_v2.md`: objective mezők bővítése + normatív objective sorrend.

## 8) Advisory notes

- A proxy modell szándékosan konzervatív: sheet AABB + occupied envelope alapján számol, nem free-space polygon kivonással.
- A per-sheet komponensek 0..=1_000_000 ppm tartományúak; aggregált output több sheet esetén 1_000_000 fölé nőhet.
- A determinism hash továbbra is placement canonical view-alapú, objective bővítés nem része a hash inputnak.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-08T01:06:53+01:00 → 2026-03-08T01:10:00+01:00 (187s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/remnant_value_model.verify.log`
- git: `main@e709c8f`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .../fill_canvas_part_in_part_pipeline.yaml         |   2 +
 docs/nesting_engine/architecture.md                |  14 +-
 docs/nesting_engine/io_contract_v2.md              |  18 +-
 rust/nesting_engine/src/export/output_v2.rs        |  36 ++-
 rust/nesting_engine/src/multi_bin/greedy.rs        | 248 ++++++++++++++++++++-
 rust/nesting_engine/src/placement/blf.rs           |  18 ++
 rust/nesting_engine/src/search/sa.rs               |  46 +++-
 scripts/check.sh                                   |   3 +
 8 files changed, 368 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/goals/canvases/nesting_engine/fill_canvas_part_in_part_pipeline.yaml
 M docs/nesting_engine/architecture.md
 M docs/nesting_engine/io_contract_v2.md
 M rust/nesting_engine/src/export/output_v2.rs
 M rust/nesting_engine/src/multi_bin/greedy.rs
 M rust/nesting_engine/src/placement/blf.rs
 M rust/nesting_engine/src/search/sa.rs
 M scripts/check.sh
?? canvases/nesting_engine/remnant_value_model.md
?? codex/codex_checklist/nesting_engine/remnant_value_model.md
?? codex/goals/canvases/nesting_engine/fill_canvas_remnant_value_model.yaml
?? codex/prompts/nesting_engine/remnant_value_model/
?? codex/reports/nesting_engine/remnant_value_model.md
?? codex/reports/nesting_engine/remnant_value_model.verify.log
```

<!-- AUTO_VERIFY_END -->
