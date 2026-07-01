# SGH-Q77 - Nagy-darab 3/tábla interlock: NFP-jelöltek (CDE-probing) + beam-keresés

## Goal

A struktúra-meghatározó, ismétlődő NAGY darab-típust (Full276: `Lv8_11612`, 6 db, ~520-csúcsú
konkáv crescent) **3/táblára mélyen egymásba interlockolni** (a referencia nestandcut 6/2-tábla
elrendezése), **generikusan**, a jelenlegi 274/65% ceiling áttörésére (a 2 elhelyezetlen darab
nagy → csak a 3/tábla helyezi el őket, util-ugrás ~78%+).

A mechanizmus a Q76/A/B′ tanulságaira épül: az él-horgony (Q76.1) + a 2D-scan interlock (Q77/B′)
a **2-test mély interlockot már eléri** (sheet0: 503k mm² átfedés, 11mm hézag), de a **3-test
EGYIDEJŰ** elrendezést (szélesség ÉS magasság ÉS páronként CDE-tiszta) a greedy páros keresés nem
oldja meg. Ehhez **NFP-alapú célzott jelölt-generálás + korlátozott beam-keresés** kell — a
referencia/deepnest is így csinálja.

## Context (adatvezérelt indok, Q76/A/B′ mérésekből)

- Q76.1 (useful+inset, mainen): 274/65.07%, 2 nagy/tábla, a nagyok korrektül él-horgonyozva.
- A (overlap-min compaction): `interlock_nested=0` — hideg overlap-min **nem konstruál** mély interlockot.
- B′ (2D-scan interlock, gated `VRS_SKELETON_COMPACT`): sheet0 **mély 2-test interlock ELÉRVE**
  (bbox-átfedés 503 834 mm² ≈ 38%, hézag 11mm), de sheet1 nem (budget) és **3/tábla nem**.
- **Geometriai kulcs (bizonyítva):** 3 nagy x-láncban 38% átfedésnél 1642mm > 1495 usable
  (nem fér); **≥50% átfedés kell** (1466mm). Kompakt (magasságba férő) 2-test páros ~38%-nál telítődik
  → a 3/tábla **3-test egyidejű** kényszer-kielégítést igényel, nem páros greedy-t.
- **Számítási analízis:** a nehéz interlock **1 típus × önmaga, ~6 darab** → NFP leszűkítve (nem 276²),
  decimált kontúron (CDE az igazság), cache-elve relatív szögenként → **sub-second** a seed-időben.

## Source of truth

- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` (`prepare_shape_native`, `polygons_collide` — CDE igazság)
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (`build_skeleton_first_seed`, `slide_nest_candidates`,
  `sheet_local_feasible`, `skeleton_placement_score`, `q74_locked`/pin, residual-fill)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (`largest_contiguous_useful_contour`, decimate_poly)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs` (`anchor_candidates_for_instance` — él-seed)
- Referencia: nestandcut LV8 (3/tábla bizonyíték); Sparrow/jagua-rs (CDE-first filozófia); NFP (Burke et al., deepnest)

## Architektúra (a kulcs döntések)

### Decimált-NFP „CDE-probing"-gal (nem NFP-poligon)
- Az NFP-poligon a 520-csúcsú konkáv kontúrra drága + törékeny. Helyette a **CDE-vel mintavételezzük az
  érintő-pozíciókat**: A körül irányonként B-t kívülről becsúsztatjuk a legmélyebb CDE-tiszta pozícióig
  (deepest-clear). Ez az NFP-határ pontjait adja **NFP-poligon számítása nélkül**, robusztusan (CDE az igazság).
- A **probing-geometria decimált** (~40 csúcs, a meglévő `decimate_poly` 50mm-grid-egyszerűsítéssel); a
  **végső validáció a teljes 520-csúcsú kontúron** (CDE).
- **Cache** relatív szögenként (`θ_rel = θ_B − θ_A`), diszkrét lépés (~3-5°, a Phase 0 ígéretes szögei köré
  fókuszálva), `Rc`-szerű megosztás minden példányra/tábla­ra. Egyszer számolva.

### Beam-keresés az interlock-láncon (nem kimerítő)
- Állapot: k nagy darab részleges elhelyezése egy táblán (k=1,2,3) + a keletkező kontúr.
- Bővítés: a következő nagy darabhoz **NFP-jelöltek** a már lerakott nagyok kontúrjához; szűrés bbox
  szélesség+magasság szerint; CDE-validálás.
- Pontszám: `largest_contiguous_useful` a maradékon + **„fér-e még egy nagy" lookahead** bónusz.
- **Beam-szélesség K (~10-20), mélység = cél nagy/tábla (3);** a top-K részleges láncot tartja.
- Deadline-korlátozott; **graceful fallback** a jelenlegi 2D-scan/él-horgony eredményre (nincs regresszió).

## Scope

### Phase 0 — Feasibility lock-in (adatvezérelt, ÉPÍTÉS ELŐTT)
- Offline (shapely és/vagy egy kis Rust-CDE harness) **3-test kereséssel igazolni**, hogy létezik érvényes
  3-nagy elrendezés 1500×3000-on ehhez a darabhoz (szélesség ≤ 1495, magasság ≤ 2990, páronként
  polygon-tiszta spacing-gel). **Legalább egy konkrét 3-pose** (szögek + offszetek) — ez a cél, amit a beam
  elér. Ha offline sem áll elő, a referencia pontos elrendezését kell kimérni és reprodukálni.
- Kimenet: a konkrét 3-pose (vagy a referencia mért elrendezése) mint verifikációs célpont.

### Phase 1 — NFP-jelölt motor (`nfp_touch_candidates`, CDE-probing, cache)
- `nfp_touch_candidates(inst, θ_new, placed_shapes, dirs) -> Vec<[dx,dy]>` a decimált kontúron, CDE-probing.
- Relatív-szög cache; deadline-bounded; a jelölteket a teljes kontúron CDE-validáljuk.
- Unit teszt: két crescent ismert mélységig (≥ a Phase 0 mélység) nesteltethető, polygon-tiszta.

### Phase 2 — Beam-lánc (`interlock_beam`)
- `interlock_beam(big_idxs, sheet, K, depth, deadline) -> Vec<SparrowPlacement>` (a legjobb 3-lánc/tábla).
- Pontszám `largest_contiguous_useful` + lookahead; top-K; graceful fallback.
- Unit teszt: szintetikus crescenten a beam 3-láncot talál, ahol a páros greedy csak 2-t.

### Phase 3 — Integráció + pin + refine
- Bekötés `build_skeleton_first_seed`-be (a nagy típusra a beam adja a seedet, gate mögött); pin (`q74_locked`);
  residual-fill + no-drop + Sparrow exploration refine (meglévő).
- Diagnosztikák (io.rs): `bpp_q77_beam_big_per_sheet`, `bpp_q77_nfp_candidates`, `bpp_q77_beam_nodes`,
  `bpp_q77_interlock_depth_mm2`.

### Phase 4 — A/B + validáció
- Full276 (default vs skeleton+NFP-beam): placed (cél 276 / ≥274+2), util (cél ~78%+), final_pairs=0,
  **big/tábla=3**. 2. csomag (generikussag): nincs regresszió. Vizuális audit (3 interlock/tábla, öblök befelé).

### Phase 5 — Report + verify
- Eredmény-központú report (placed/util/big-per-sheet/interlock-depth vs baseline 274/65), őszinte ACCEPT/EXIT.
- `./scripts/verify.sh` gate.

## Non-goals
- NINCS teljes 276² NFP (csak a nagy típus × önmaga). NINCS NFP-poligon (CDE-probing helyette).
- NINCS spacing/margin csökkentés, forgatás-kikapcsolás, part-id/koordináta hardcode, geometriai
  lehetetlenség-kijelentés (a referencia bizonyítja a 3/táblát).
- Default production változatlan (gate OFF = byte-azonos).

## Required changes
- `rust/vrs_solver/src/optimizer/sparrow/nfp_probe.rs` (ÚJ) — `nfp_touch_candidates` + relatív-szög cache.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `interlock_beam`, bekötés a seedbe, gate.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — (ha kell) segéd a lookahead-hez.
- `rust/vrs_solver/src/io.rs` — Q77 diagnosztikák.
- `rust/vrs_solver/tests/sparrow_sheet_builder.rs` — NFP + beam unit/integrációs tesztek.
- `scripts/bench_sgh_q77_big_interlock_nfp_beam.py` — A/B runner + Phase 0 feasibility harness.

## Acceptance / Definition of Done
1. **Phase 0**: konkrét, CDE-tiszta 3-nagy pose igazolva (offline) — a beam célpontja rögzítve.
2. **NFP-motor** (CDE-probing, decimált, cache) + unit teszt (2 crescent ≥ Phase 0 mélységig nestel).
3. **Beam** 3-láncot talál (unit teszt szintetikus crescenten, ahol a páros greedy csak 2-t).
4. **Integráció**: Full276 skeleton+NFP-beam → **3 nagy/tábla**, valid (final_pairs=0), pinnelt, refine túléli.
5. **A/B eredmény**: placed ≥ 276 (vagy a max feasible, > 274), util materiálisan fel (~78%+); 2. csomagon
   nincs regresszió. **ACCEPT**: 3/tábla + darabszám-emelés generikusan; **EXIT (őszinte)**: ha nem, a
   Phase 0 célponttal + a gap-elemzéssel rögzítve.
6. Gate default OFF → production byte-azonos; tesztek zöldek (lib + integrációs + NFP + beam).
7. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q77_big_interlock_nfp_beam.md` PASS.

## Számítási költségvetés (a döntés-analízisből)
- NFP-probing: ~50 szög × ~64 irány × slide(~18 CDE) ≈ ~57k CDE, **cache-elve egyszer** (~<1s).
- Beam: K(15) × mélység(3) × jelölt(~100) × CDE ≈ ~7k CDE ≈ **~0.2s** (sheet_local_feasible ~30μs).
- A drága rész (276-darabos szeparáció ~90s) **változatlan**. Deadline + graceful fallback → nincs
  robbanó-compute/regresszió.

## Constraints
- Minimal-invaziv; gate OFF = byte-azonos production; CDE a végső ütközés/határ igazság; folytonos forgatás
  megmarad; nincs hardcode; nincs csendes fallback a régi logikára.
- Cargo toolchain export a build előtt (RUSTUP_HOME/CARGO_HOME/toolchain bin).
- Commit/push csak explicit kérésre; magyar kommunikáció (kód/azonosítók angolul).
