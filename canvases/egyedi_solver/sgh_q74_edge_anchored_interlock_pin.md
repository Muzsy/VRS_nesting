# SGH-Q74 - Edge-anchored interlock seed + item pinning

## Goal

A felhasznaloi strategia + a nestandcut referencia szerint: a nagy ismetlodo kritikus tipust a
forced/strict latest seed (1) a tabla **szeleihez forgassa/horgonyozza** (true-extreme orientacio),
(2) **mely interlockkal** (bbox-atfedes megengedett, poligon-szintu CDE-clearance) nesztelii, es (3)
a seedelt nagy darabokat **PINNELJE** (fix akadaly), hogy az exploration separator + gravity + a
vegso sanitize NE sodorja el / dobja ki oket — a kis darabok koruluk pakoljanak.

A Q73 tanulsaga: pinning nelkul a (pinneletlen) exploration a nagy darabokat visszaforgatja ~90deg-ra
es kidob — ezert a seed nem maradt meg. A Q74 ezt a pinning-hianyt szunteti meg.

## Context (referencia + sajat elozmenyek)

- Referencia (`2447207_SHEET_001/002` DXF): tabla 3000x1500, a `Lv8_11612` nagy krescensbol **3/tabla
  (6/6)**, vizszintes savokban, **bbox-atfedo mely interlock** (szomszedos parok bbox-y atfedese
  178-530mm), 2 darab a tabla **ellentetes eleihez** (also+felso) horgonyozva, a 3. kozepre nesztelve.
- Sajat: Q51 sp0-nal **3+3 mukodott** (co-movable overlap interlock); spacing 5-nel csak 2/tabla
  (Q52 negativ: a bottleneck a szekvencialis egy-darabos kereses). Q72 no-drop (262), Q73 row-seed
  regresszio (pinning hianya).
- A bbox-atfedo interlock a CDE-mag natív kepessege; a hiany a TIGHT spacing-5 + a seed megorzese.

## Source of truth

- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- `samples/real_work_dxf/0014-01H/lv8jav/Nested/2447207_2026_05_11.zip` (referencia nest DXF-ek)
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (`sheet_local_feasible`, latest-lock seed)
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` (`prepare_shape_native`)
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` (`SparrowState`)

## Scope

- **Pinning infrastruktura:** `SparrowState.locked_items` (instance idxs); a separator worker a locked
  elemeket kihagyja a move-celokbol (fix akadaly); a `gravity_compact_layout` nem csusztatja a locked
  elemeket; a `sanitize_partial` a locked elemeket elsobbseggel tartja (a kolliziozo fillert dobja).
- **Edge-anchored slide-nest seeder** (`edge_anchored_interlock_big_seed`): orientacio-sweep + slide-
  nest lanc (poligon-erintesig csusztat, bbox-atfedes megengedett) + ellentetes-el horgonyzas
  (bal+jobb flush) + bounded 2D kozepso-nest a 3. darabhoz; a be nem fero nagy darabok unplaced-ek
  (nem churn-olnak).
- **Wiring:** forced/strict latest alatt, gate `VRS_EDGE_INTERLOCK_SEED` (default OFF), a nagy tipus
  placementjeit lecsereli a seedre, a locked set a pipeline-on at; Q72 no-drop a maradekra.
- Eredmeny-kozpontu benchmark + **kotelezo vizualis audit**.

## Non-goals

- Nem cel a 6/6 (3/tabla) garantalt elerese, ha a slide-nest nem talalja meg (oszinten rogzitve).
- Nem cel proxy heurisztika, spacing/margin csokkentes, forgatas-kikapcsolas, hardcode.
- Nem cel a default production valtozasa (gate default OFF).

## Required changes

- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` - `SparrowState.locked_items`.
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs` - locked elemek kihagyasa a move-celokbol.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` - seeder + pinning (run_subsolve, gravity)
  + latest-lock wiring + no-drop exclude.
- `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs` - `sanitize_partial` locked-prioritas.
- `rust/vrs_solver/src/io.rs` - Q74 diagnosztikak.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs` - pin-survival regresszios teszt.
- `scripts/bench_sgh_q74_edge_anchored_interlock_pin.py` - Full276 Q74 benchmark.

## Acceptance / Definition of Done

1. **Pinning mukodik:** a seedelt nagy darabok TULELIK a pipeline-t (nem sodrodnak el, nem
   forgatodnak vissza 90deg-ra, nem dobja ki a sanitize). Teszt + render bizonyit.
2. **Edge-anchored + nem-ortogonalis:** a nagy darabok a tabla szeleihez horgonyzottak, valodi
   (nem 0/90/180/270 kenyszer) orientacioval.
3. **Nincs production regresszio:** gate OFF = Q72 viselkedes (262), byte-szinten.
4. **Eredmeny-kozpontu jelentes:** a Full276 run placed_count + nagy-darab/tabla eloszlas + forgatas,
   Q72 osszehasonlitas; a 3/tabla allapota OSZINTEN (ha 2/tabla, az rogzitve, nem meguszva).
5. **Teljeskoru run-rogzites + vizualis audit** a `artifacts/benchmarks/sgh_q74/` alatt.
6. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md` PASS.

## Constraints (nem alkuképes)

- Spacing/margin nem csokken; CDE a vegso igazsag; folyamatos forgatas marad; nincs hardcode; nincs
  csendes regi-logika fallback. Cargo toolchain export a build elott.
