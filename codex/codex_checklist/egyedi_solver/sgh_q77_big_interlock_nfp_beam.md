# SGH-Q77 Checklist - Nagy-darab 3/tábla interlock (NFP-probing + beam)

## Phase 0 - feasibility lock-in
- [ ] Q77 canvas/YAML/checklist/report váz elkészült
- [ ] Offline 3-body kereső (shapely és/vagy Rust-CDE harness) kész
- [ ] Konkrét, CDE/polygon-tiszta 3-nagy pose igazolva (szélesség ≤1495, magasság ≤2990, spacing) — VAGY
      a referencia (nestandcut LV8) 3-nagy elrendezése kimérve
- [ ] A 3-pose célpont rögzítve (`artifacts/benchmarks/sgh_q77/phase0_feasibility.json`)

## Phase 1 - NFP-jelölt motor
- [ ] `nfp_touch_candidates` (CDE-probing, deepest-clear, NFP-poligon NÉLKÜL) bevezetve (nfp_probe.rs)
- [ ] Decimált (~40 csúcs) probing-geometria; végső CDE-validáció a TELJES kontúron
- [ ] Relatív-szög cache (θ_rel, ~3-5° lépés, Phase 0 szögek köré fókuszálva), Rc-megosztás
- [ ] Unit teszt: 2 crescent a Phase 0 mélységig (≥50% x-átfedés kompaktan) nestel, polygon-tiszta

## Phase 2 - beam-lánc
- [ ] `interlock_beam` (állapot=k nagy+kontúr; bővítés=NFP-jelöltek+bbox-szűrés+CDE; pontszám=
      largest_contiguous_useful + lookahead; beam K~10-20, mélység 3)
- [ ] Graceful fallback a 2D-scan/él-horgony eredményre (deadline-bounded, nincs regresszió)
- [ ] Unit teszt: szintetikus crescenten a beam 3-láncot talál, ahol a páros greedy csak 2-t

## Phase 3 - integráció + pin + refine
- [ ] Bekötés `build_skeleton_first_seed`-be a nagy típusra (gate mögött)
- [ ] Pin (`q74_locked`); residual-fill + no-drop + Sparrow exploration refine (meglévő)
- [ ] Q77 diagnosztikák (io.rs): beam_big_per_sheet, nfp_candidates, beam_nodes, interlock_depth_mm2

## Phase 4 - A/B + validáció
- [ ] Full276 A/B lefutott: default vs skeleton+NFP-beam
- [ ] **3 nagy/tábla** elérve, valid (final_pairs=0), pinnelt, a refine túléli
- [ ] placed ≥ 276 (vagy a max feasible, > 274); util materiálisan fel (~78%+)
- [ ] 2. csomag (kis/közepes) A/B: nincs regresszió (generikussag)
- [ ] q77_summary.json + q77_report.md eredmény-központú (placed + util + big/tábla + interlock-depth vs 274/65)
- [ ] Vizuális audit rögzítve (3 interlock/tábla, öblök befelé, sűrű fill)

## Phase 5 - lezárás + gate
- [ ] ACCEPT (3/tábla + darabszám-emelés generikusan) — VAGY őszinte EXIT (Phase 0 célpont + gap-elemzés)
- [ ] Gate default OFF = byte-azonos production; tesztek zöldek (lib + integrációs + NFP + beam)
- [ ] Codex report DoD → Evidence Matrix kitöltve path+line bizonyítékkal
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q77_big_interlock_nfp_beam.md` PASS
