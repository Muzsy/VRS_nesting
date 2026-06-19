# Q55A — Sheet-aware edge-anchor rotation

## Goal

Az `Anchor` szerepű nagy critical alkatrész tábla-élhez/sarokhoz igazítása **sheet-aware** rotációval:
ne egyetlen seed-szöget adjon (a jelenlegi sheet-edge candidate egyetlen tengelyhez igazít, a sheet
arányát/hosszú irányát figyelmen kívül hagyva), hanem **rangsorolt rotációs jelölthalmazt** — a domináns
hosszú élt a sheet long/short edge-éhez igazítva, 180° flip variánsokkal, **valódi continuous lokális
finomítással** (nincs 90/270 snapping).

## Háttér

A Q54E proof megmutatta: a skeleton út a spacing-0 3/tábla-t reprodukálja, de a tight spacing (5)
3-way packing nem oldódik meg, részben mert az anchor-rotáció nem sheet-aware. A referencia LV8-táblán
a nagy alkatrész ~88.3°-kal van elforgatva (nem 90), hogy az oldalsó nyúlványok párhuzamosak legyenek a
tábla hosszú élével — ez a sheet-aware edge-anchor. A Q55A ezt a rotáció-generálást javítja.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs`
  - `sheet_edge_candidates`, `resolve_seed_rotation`, `sheet_edge_alignment_angles` használat
- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs`
  - `ContourFeatureSet` (dominant_edges, sheet_edge_alignment_angles, edge angle/normal)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (Q54 — SkeletonRole)
- `rust/vrs_solver/src/sheet.rs` — `SheetShape` (width/height → long/short edge irány)
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- Valós repo alapján: `AGENTS.md`, `docs/codex/*`, a Q47–Q54 canvas/report fájlok elolvasva.
- **Continuous rotation marad continuous** — a seed rangsorolt jelölthalmaz, de a refine/final nem
  snappel 90/270/45-re; az anchor-szög folytonos (pl. ~88.3°).
- Nincs NFP, nincs bbox-corner shortcut primary critical pathként, nincs hardcoded `Lv8_11612`/3+3.
- CDE a collision truth; final acceptance csak CDE-valid.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.
- Scope-fegyelem: a változás a `feature_candidate_generator.rs` sheet-edge ágára + diagnosztikára
  korlátozódjon; a reportban touched-file lista.

## Feladat

### Sheet-aware rotation seed halmaz

- A domináns hosszú él igazítása **mindkét** sheet-irányhoz: a sheet **long edge** (a hosszabb dimenzió)
  irányához ÉS a **short edge** irányához, **180° flip** variánsokkal.
- Minden seed-hez **continuous lokális finomítás** (±kis valós szögek, a Q52 `density_rotation_candidates`
  mintájára), nem fix lista.
- A kimenet **rangsorolt** rotációs jelölthalmaz (nem egyetlen seed), a sheet-aspektus + él-hossz alapján
  pontozva.

### Diagnosztika (kötelező)

```
seed_rotation
refined_rotation
edge_distance
sheet_edge_anchor_side
cde_result (clear / not)
```

### DoD

- Lv8 nagy critical part, 1500×3000 sheet: generálódjon **legalább egy CDE-clear sheet-edge anchor**
  candidate, sheet-edge anchored, a rotáció **nem** fix snapping eredménye (a refined ≠ a fix
  0/90/180/270, ha a continuous optimum eltér).
- Unit teszt: a sheet-aware seed-halmaz tartalmazza a long-edge ÉS short-edge igazítást + flip variánst;
  a refined rotáció continuous (nem snapping).
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_edge`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml edge_anchor`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md`

## Rollback

- Ha a sheet-aware rotáció regressziót okoz, gate off → a Q54 sheet-edge candidate érintetlen.
- Ha continuous rotation guardrail sérül (snapping), azonnali revert.
