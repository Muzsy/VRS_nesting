# Q54C — Overlap-toleráns critical separation (continuous rotation)

## Goal

A Q53C refine pótlása, amely not-clear seednél **azonnal feladta** (`seed_not_clear`, 0 iteráció). A
Q54C-ben a Q54B clearance-aware (vagy kontrollált-overlap) seedből indulva a **critical set együtt
mozog/forog** CDE-clear állapotig, **valódi continuous rotation**-nel. Ez köti össze a Q52
`density_biased_separate` (rotation-correct) építőelemet a skeleton-admissionnel.

## Háttér

A Q53 audit szerint a `refine_feature_candidates` (feature_candidate_generator.rs:518) a seedet azonnal
elveti, ha nem clear (`seed_not_clear`, 306/306). A valódi interlockhoz a seed lehet overlapos
indulóállapot, amit a solvernek **közösen kell kitisztítania** — a több critical part együtt mozog és
forog. Ez pontosan a Q52 `density_biased_separate` képessége (lexikografikus clear-first, density
ranking, spacing-collision gap-tartó shape, continuous rotation a `density_rotation_candidates`-szel),
amelyet a critical admission co-movable lépésére kell alkalmazni — most a feature-seedekből indítva.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `density_biased_separate` (Q52, rotation-correct), `density_rotation_candidates`, `try_admit_critical`
    (co-movable lépés), `sheet_local_feasible`
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs`
  - `refine_feature_candidates` (Q53C — leváltandó/megkerülendő not-clear feladás)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (Q54A role)
- `rust/vrs_solver/src/optimizer/sparrow/density.rs` — `density_candidate_score`
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- CDE marad a collision truth; a final acceptance csak CDE-valid (0 collision, 0 boundary/spacing).
- Tilos NFP / pairwise NFP mátrix; tilos bbox collision shortcut.
- **Continuous rotation marad continuous** — a separation a `density_rotation_candidates` continuous
  finomítását használja; nincs snapping fix listára. (Q52 tanulság: a density-samplerek korábban
  befagytak 90/270-re; ez tilos.)
- Cavity/hole nincs a fő solverben.
- Nincs `part_id` hack, nincs hardcoded 3+3.
- Gated (`VRS_SHEET_BUILDER_SKELETON`); a Q52/Q51 fallback érintetlen, default off → byte-azonos.
- Budgetelt: a separation idő/iteráció-korlátos; ne starve-olja a builder fallbackot.

## Feladat

### Overlap-toleráns separation a feature-seedből

- A Q54B seed (clearance-aware vagy kontrollált overlap) → `density_biased_separate` a target sheet
  critical setjén, a Q54A szerepeket figyelembe véve (az anchor mozoghat, de erős inertia; az interlock +
  band aktívan mozog/forog).
- A `refine_feature_candidates` not-clear-azonnal-feladás lecserélése: ha a seed nem clear, **szeparálj**
  (a critical set együtt), ne dobj.
- Continuous rotation a teljes separation alatt (88–92° finomítás is, nem 90/270 snap).

### Co-movable critical set

- A `try_admit_critical` co-movable lépésében a Q54B feature-seed legyen az indulóállapot (a jelenlegi
  overlapping-centroid seed helyett/mellett), majd `density_biased_separate` tisztít.
- A final acceptance csak `final_validation_tracker().is_feasible()`.

### DoD

- Unit teszt: overlapos **2-critical** szintetikus konkáv pár CDE-clear interlockba oldódik (nem szétszór);
  a végállapot rotation **nem** kényszerül fix listára.
- Unit teszt (szintetikus, LV8-szerű): overlapos **3-critical** seed → CDE-clear vagy dokumentált
  `fail_reason` (a Q53 azonnali-feladás helyett valódi separation-kísérlet, mérhető iterációkkal).
- Diagnosztika: `separation_iterations`, `seed_overlap`, `seed_rotation`/`refined_rotation`,
  `final_clear`, `separation_fail_reason`.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml separation`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml density_biased`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md`

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
```

## Rollback

- Ha a separation regressziót/instabilitást okoz, gate off → a Q52 `density_biased_separate` és a Q51
  fallback érintetlen.
- Ha a continuous rotation guardrail sérül, azonnali revert; a rotation-set forrása maradjon a
  `density_rotation_candidates`.
