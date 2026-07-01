# SGH-Q76 - Skeleton-first seed + residual-fill (contour residual-space objective)

## Goal

A generikus (default) solver-utat **skeleton-first** strategiara allitani: a struktura-meghatarozo
(nehez/nagy) darabokat eloszor, a tabla szeleihez horgonyozva, a **kitoltheto osszefuggo maradekteret
maximalizalva** helyezzuk el es **pinneljuk**, majd a maradek darabokat a felszabadult terbe toltjuk
(residual-fill = a hianyzo re-inszercio). A maradekter-objektiv **valodi KONTUR-alapu** (nem bbox), igy
a konkav obloket es a tight interlockot is helyesen ertekeli.

Ez a Q72(no-drop)+Q74(el-horgony+pin) bizonyitott mechanikajanak **altalanositasa a default utra**,
elvi particioval es valodi residual-fill-lel — NEM LV8-hardcode.

## Context (adatvezerelt indok)

A/B (Full276, 2 tabla, m5/sp5, default ut):
- default: **244/276, util 42.6%**, 101s-nal konvergal;
- +density / +density+compress: **ugyanaz a 244/42.6%** (csak budgetet eget). A compaction **surit, de
  nem inszertal** (362 elfogadott mozgas, 0 placed-lift) -> a compaction NEM a lever.
- 42.6% util = a 2 tabla **57%-a ures, megis 32 darab elhelyezetlen** -> van hely, de **semmi nem teszi
  vissza** a kiesett darabokat (hianyzo re-inszercio), es a seed (nagy darabok elhelyezese) fragmentalja
  a teret.

Tehat a lever a **seed-minoseg + re-inszercio**, a kettot **egyutt** kell kezelni, a kozos valuta az
**osszefuggo hasznos maradekter**.

## Source of truth

- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` (`criticality_tier`, `is_critical`)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (`largest_edge_connected_free_area/_slot`)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs` (`anchor_candidates_for_instance`)
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (`direct_insert_on_sheet`, `edge_anchored_interlock_big_seed`, `q74_locked`/`SparrowState.locked_items`)

## Scope

### Kontur-alapu maradekter-objektiv (additiv)
- A `sheet_skeleton.rs`-ben uj **`largest_edge_connected_free_area_contour(polys, sheet_bounds, cell)`**
  es **`largest_edge_connected_free_slot_contour(...)`**: az occupancy-jeloles **scanline poligon-raszter**
  (a darab valodi kontúrja, nem a bboxa), a flood-fill kozos helperbe kiemelve.
- A **bbox-verziok valtozatlanok** (meglevo hivok erintetlenek). Magas-csucsu kontúr a 50mm-gridhez
  egyszerusitve. Unit teszt: konkav darab obleje a kontur-verzioban SZABAD, a bbox-verzioban foglalt.

### Skeleton-first seed (uj `build_skeleton_first_seed`, gate `VRS_SKELETON_FIRST`, default OFF)
1. **Particio:** skeleton = `criticality_tier()==Critical`, **kapacitas-sapkaval** (Σ skeleton-area ≤
   `VRS_SKELETON_FRAC × Σ solver_sheets.area`, default 0.5, priority_score szerint csokkenobe valogatva).
   Maradek = fill-pool.
2. **Skeleton-elhelyezes (greedy):** csokkeno meretben; jeloltek `anchor_candidates_for_instance` (el/sarok,
   folytonos rotacio) + a mar lerakott skeletonhoz slide-nest (`edge_anchored_interlock_big_seed`
   **altalanositva**: barmely tipus, **per-tabla koordinata**). Pontszam = **kontur-free-area** az
   elhelyezes utan; a legnagyobb maradek-regiot hagyo valid jelolt nyer (tie-break: sarok/el-kontakt).
   Commit + **pin** (`locked_items`).
3. **Residual-fill:** fill-pool csokkeno meretben (Structural→Filler); tablakat a legnagyobb szabad szoba
   szerint rendezve **`direct_insert_on_sheet`** (CDE-tiszta legsurubb pozicio, a konkav obloket is); be nem
   fert -> unplaced.
4. **Integracio:** a seed-blokkban `if skeleton_first_enabled()` ag, `q74_locked = skeleton`. A meglevo
   pipeline finomit (exploration a pinnelt skeletonnal + gravity + sanitize Q74-vedelemmel).

## Non-goals
- Nincs feedback/outer-loop (Decision 3) — ez kulon fazis (F3), csak ha az F1 adat indokolja.
- Nincs compaction-erlelés (az A/B szerint zsakutca).
- Nincs spacing/margin csokkentes, forgatas-kikapcsolas, part-id/koordinata hardcode.
- Default production valtozatlan (gate OFF).

## Required changes
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — kontur-free-area/_slot + scanline raszter + kozos flood-fill helper.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `build_skeleton_first_seed`, `skeleton_first_enabled`, residual-fill loop, edge-seeder altalanositas, wiring.
- `rust/vrs_solver/src/io.rs` — F1 diagnosztikak.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs` — F1 regresszios teszt; `sheet_skeleton` unit teszt a kontur-objektivre.
- `scripts/bench_sgh_q76_skeleton_first_residual_fill.py` — A/B runner (default vs skeleton-first), Full276 + 2. csomag.

## Acceptance / Definition of Done
1. **Kontur-objektiv** bevezetve additivan; unit teszt bizonyitja (konkav obol SZABAD a kontur-verzioban).
2. **Skeleton particio** (`criticality_tier==Critical` + `VRS_SKELETON_FRAC` sapka) + **el-horgonyzott,
   kontur-free-area-maximalizalo elhelyezes** + **pin**.
3. **Residual-fill** (`direct_insert_on_sheet` loop) a kieso darabokat is visszateszi.
4. Gate `VRS_SKELETON_FIRST` default OFF -> production byte-azonos.
5. **A/B eredmeny-kozpontu:** Full276 ÉS 1 mas (kis/kozepes-darabos, domináns nagy nelkul) csomag;
   skeleton-first vs default (244/42.6%); placed_count + util + kontur-free-area + validitas (final_pairs=0).
   **ACCEPT:** generikusan veri a defaultot mindket csomagon. **EXIT (oszinte):** ha nem, rogzitve + F3/ujragondolas.
6. F1 regresszios teszt + sheet_skeleton kontur unit teszt zold; 550+ lib + integracios teszt zold.
7. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md` PASS.

## Constraints
- Minimal-invaziv; meglevo (production) mukodest nem rontunk (gate OFF = byte-azonos).
- CDE a vegso utkozes/hatar igazsag; folytonos forgatas megmarad; nincs hardcode.
- Cargo toolchain export a build elott (RUSTUP_HOME/CARGO_HOME/toolchain bin).
