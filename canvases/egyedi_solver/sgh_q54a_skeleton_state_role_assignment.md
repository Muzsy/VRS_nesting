# Q54A — Skeleton state + critical role assignment

## Goal

A critical sheet-building vázának alaprétege: egy `SheetSkeletonState`, amely sheetenként követi a már
admittált critical alkatrészeket és a maradék edge-connected szabad régió durva leírását, plusz egy
**szerep-hozzárendelő** függvény, amely a következő critical jelöltnek `Anchor` / `Interlock` /
`BandInsert` szerepet ad — **darabszám-hardcode nélkül**, kizárólag a sheet aktuális geometriájából és
a part Q47-profiljából. Ez a réteg még **nem változtat placementet**; csak állapotot és besorolást ad,
amelyre a Q54B–E épül.

## Háttér

A Q53 audit (306 generált / 0 elfogadott feature candidate) megmutatta, hogy a feature-candidate
mikró-réteg önmagában nem elég: hiányzik a **referencia-szerű váz** (anchor → interlock → band-insert),
amely eldönti, *milyen* candidate-et keressünk és *hova*. A referencia LV8-táblán a három nagy darab
nem egy kaotikus közös mozgással kerül a helyére, hanem: (1) első nagy a tábla éléhez/sarkához
igazítva, (2) második beleforgatva ~180°, (3) harmadik a megmaradt alsó szabad sávba. A szerep tehát a
sheet állapotából adódik, nem abból, hogy „3 darab kell".

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs`
  - `PartShapeProfile`, `CriticalityTier` (`Critical` / `Structural` / `Filler`), `priority_score`
  - `contour_features()`
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `build_critical_aware_seed`, `build_criticality_queues`, `try_admit_critical`, `sheet_centroid`
- `rust/vrs_solver/src/optimizer/sparrow/model.rs`
  - `SPInstance`, `SheetShape`, `SparrowLayout`, `SparrowPlacement`
- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs`
  - `ContourFeatureSet` (dominant edges, sheet-edge alignment angles)
- `rust/vrs_solver/src/io.rs`, `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs`
  - optimizer diagnostics export

## Globális guardrailek

- Valós repo alapján dolgozz: először olvasd el az `AGENTS.md`, `docs/codex/overview.md`,
  `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, valamint a Q47–Q53 canvas/report
  fájlokat és a Q53 audit megállapításait.
- CDE marad a collision truth; tilos bbox/AABB collision shortcut.
- Tilos NFP vagy pairwise NFP-kompatibilitási mátrix.
- Continuous rotation nem váltható ki diszkrét foklistával; seed lehet, de refine/final nem snappelhet.
- Cavity/hole nincs a fő solverben; csak külső kontúr.
- Nincs `part_id`-specifikus hack, **nincs hardcoded `3 big per sheet`** szabály; a szerep a geometriából
  és a profilból adódik.
- Minden új viselkedés **opt-in/gated** (`VRS_SHEET_BUILDER_SKELETON`), default off, amíg a
  regressziómentesség nincs bizonyítva.
- **Scope-fegyelem (Q53 tanulság):** az új logika **új modulban** (`sheet_skeleton.rs`); a reportban
  touched-file lista; ne ömöljön szét a core search/separator fájlokba.

## Feladat

Hozz létre egy `sheet_skeleton.rs` modult.

### `SheetSkeletonState`

- Per sheet követi: az admittált critical placementek listáját (instance_idx + role), és a maradék
  **edge-connected** szabad régió durva leírását (Q54A-ban elég egy egyszerű reprezentáció: a sheet
  bbox-ból kivont admittált bbox-ok uniója, vagy egy durva occupancy flag — a tényleges free-space
  proxy a Q54D-ben jön; itt csak az állapot-hordozó struktúra kell).
- API: `new(sheet)`, `record_admission(instance_idx, role, placement)`, lekérdezők.

### `assign_role(profile, instance, skeleton_state, sheet) -> SkeletonRole`

- `Anchor`: a sheet még üres critical-ra nézve (nincs admittált critical), VAGY a leg-kritikusabb
  jelölt a friss sheeten.
- `Interlock`: van már `Anchor`, és a jelölt feature-szinten illeszthető hozzá (dominant edge / concave
  zone jelenléte alapján; a tényleges illesztést a Q54B/C végzi — itt a besorolás dönt).
- `BandInsert`: van anchor(+interlock), és maradt nagy, edge-connected szabad sáv (durva küszöb alapján).
- A döntés determinisztikus, instance_idx tiebreak.

### Kötelező viselkedés

- A szerep-hozzárendelés **nem** placement; a Q54A nem mozgat semmit, csak állapotot és role-t ad.
- Gated: a skeleton state/role csak `VRS_SHEET_BUILDER_SKELETON=1` mellett épül; default off → a Q51/Q52
  viselkedés byte-azonos marad.

### DoD

- Unit teszt: szintetikus 3-critical szekvencián a szerepek `Anchor → Interlock → BandInsert` sorrendben,
  determinisztikusan rendelődnek; üres sheeten az első mindig `Anchor`.
- Unit teszt: a darabszám **nem** befolyásolja a szerepet (ugyanaz a geometria → ugyanaz a szerep,
  függetlenül attól, hány part van a queue-ban).
- Diagnosztika: `skeleton_role_per_admission`, `skeleton_anchor/interlock/bandinsert_counts`.
- Default off → meglévő multisheet/builder suite byte-azonos (no-regression).

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_builder`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md
```

(A `check.sh` mostantól futtatja a teljes `vrs_solver` cargo suite-ot — minden részfeladat zöld
suite-tal záruljon.)

## Rollback

- Ha a skeleton state bármilyen módon megváltoztatja a default (gate-off) viselkedést, a state-építést
  szigorúan a gate mögé kell zárni.
- A modul tisztán additív: ha IO-regressziót okoz, a diagnosztikai mezők optional/additive exportja.
