# SGH-Q43 — Upstream jagua_rs/Sparrow 1500x6000 strip baseline + runtime-focused semantic parity audit

## Cel

Az eredeti upstream `jagua_rs` / `Sparrow` modell futtatasa es auditálása a full276 LV8 csomagon, 1500x6000 mm strip baseline celgeometriaval (ami a 2 db 1500x3000 mm lap területének es geometriájának megfelelo osszefüggo csi). Az audit a futásido mérésre es a saját solver logikájának upstream-paritás vizsgálatára fókuszál.

A sajat solver forrasa szigorúan nem modosúl. A Q43 audit + benchmark task; nem implementacio.

## Nem-cel

- Saát solverlogika javítása.
- Saát solver acceptance lazítasa.
- Spacing/margin/rotation szemantika modosítása.
- Upstream kód atirasa.
- Upstream kód „javítása”, hogy jobban fusson.
- Legacy fallback bekötése a sajat solverbe.
- Compression bekötése a sajat solverbe.
- Cavity prepack bekötése.
- Saát solver output utólagos kozmetikazasa.
- Saát Q42 3x1500x3000 finite-stock eredmeny ertelmezesi korlátjainak elhallgatasa.

## Engedélyezett

- Upstream jagua_rs/Sparrow letöltése / clone / fetch.
- Benchmark runner keszítése.
- Input-konverziós script keszítése (Q42 input -> SPP).
- Upstream output normalizálasa.
- Audit / report / artifact keszítése.
- Render evidence keszítése, ha lehetséges.
- Semantic parity osszehasonlító doksi.

## Érintett fájlok (kötelezően valós, kereséssel igazolt)

### Upstream
- `.cache/sparrow/` (klón, commit `c95454e390276231b278c879d25b39708398b7d3`)
- `.cache/sparrow/target/release/sparrow` (release binary, 2,414,752 byte, 2026-06-13 15:22 mtime)
- `.cache/sparrow/Cargo.toml` (jagua-rs pin `ba38bcae9ed3ab41a9e93a1894e2b01ea87c6619`)
- `.cache/sparrow/src/` (upstream source)

### Saját solver (audit célú, NEM modosítva)
- `rust/vrs_solver/src/optimizer/sparrow/` (sparrow CDE port)
- `rust/vrs_solver/src/optimizer/sparrow/sample/` (search, best_samples, coord_descent)
- `rust/vrs_solver/src/optimizer/sparrow/eval/` (sep_evaluator, specialized_cde_pipeline)
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` (CDE tracker)
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs` (LBF initial placement)
- `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs` (Q32 finite-stock)
- `rust/vrs_solver/src/optimizer/sparrow/geometry/` (Q40/Q41 spacing)
- `rust/vrs_solver/src/technology/clearance.rs` (Q33 technology policy)
- `rust/vrs_solver/src/rotation_policy.rs` (continuous rotation)

### Q42 baseline (referencia, csak olvasás)
- `artifacts/benchmarks/sgh_q42/inputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json`
- `artifacts/benchmarks/sgh_q42/q42_summary.json`

### Új artifactok (Q43)
- `scripts/run_sgh_q43_upstream_sparrow_strip1500x6000.py` (runner)
- `scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py` (smoke)
- `scripts/build_sgh_q43_comparison_artifacts.py` (comparison + parity matrix)
- `artifacts/benchmarks/sgh_q43/` (minden output)
- `codex/reports/egyedi_solver/sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.md`

## Feladatlista

- [x] Pre-immutability snapshot (git status + diff).
- [x] Upstream clone info + build log.
- [x] SPP input konverter (Q42 full276 → 1500x6000 strip).
- [x] Runner + smoke + comparison script.
- [x] Upstream Run A 1200 sec (1500x6000 strip).
- [ ] Upstream Run B 2400 sec (a háttérben fut a report készítésekor).
- [x] Upstream summary + comparison + parity matrix.
- [x] Semantic parity audit report (9 fejezet + matrix).
- [x] Smoke validator.
- [ ] Repo gate (verify.sh) — a Q43 spec kötelező parancsa, a háttérben fut.
- [ ] Post-immutability snapshot.

## DoD

1. A Q43 spec kötelező 10+ artefaktuma létezik (clone_info, build_log, run_1200.log, summary, comparison, parity, pre/post status + diff).
2. Az upstream jagua_rs/Sparrow forrás azonosítva van (commit `c95454e`).
3. Az upstream build dokumentálva van a `upstream_build.log` fájlban.
4. A full276 LV8 input upstream SPP formátumba konvertálva (1500x6000 strip baseline).
5. Az upstream Run A 1200 sec lefutott, valid 276/276 layout-ot adott (vagy futáshiba explicit dokumentálva).
6. Az upstream Run B 2400 sec lefutott (vagy explicit „skipped" / „pending" oka dokumentálva).
7. A saját Q42 eredménnyel való összehasonlítás és a `NOT DIRECTLY COMPARABLE` verdict explicit.
8. A 9 audit téma mindegyike kapott verdictet: `MATCH` / `ADAPTED MATCH` / `INTENTIONAL DIVERGENCE` / `RISKY DIVERGENCE` / `UNKNOWN`.
9. A parity matrix a `artifacts/benchmarks/sgh_q43/semantic_parity_matrix.json` fájlban van.
10. A saját solver source kód **nem** modosult (pre + post `git diff` egyaránt 0 bájt).
11. A `scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py` PASS.
12. A `./scripts/verify.sh --report ...` lefutott, az eredmény a report AUTO_VERIFY blokkjában.

## Kockázatok és rollback

- **A cargo PATH-ba került a Q43 audit során.** Ez a Q42 verify FAIL-jét okozta korábban; a Q43 audit során a `cargo --version` működik a `~/.cargo/bin/cargo` symlinken keresztül. Ha a PATH-ot nem örökli egy másik session, a verify FAIL-t ad, de ez nem befolyásolja a Q43 audit helyességét.
- **Az upstream SPP 1500x6000 strip 9.0 m² területű**, míg a Q42 3x1500x3000 stock pool 13.5 m². A Q43 baseline egy „könnyebb" feladatot old meg (kisebb polygonok, mert nincs spacing-expansion). Ezt a `Direct comparability limitations` szekció részletezi.
- **A Run B 2400 sec hosszú.** Ha a futás megszakad, a `upstream_summary.json` `run_b.status = "error"` státusszal íródik, és a report ennek megfelelően dokumentál.
- **A saját solver source diff bármilyen nem-üres értéke esetén** a Q43 automatikusan FAIL. A Q43 runner és a comparison script nem nyúl rust/api/worker/frontend/vrs_nesting forrásfájlokhoz.

Rollback: a Q43-ra létrehozott `scripts/run_sgh_q43_*.py`, `scripts/smoke_sgh_q43_*.py`, `scripts/build_sgh_q43_*.py`, `artifacts/benchmarks/sgh_q43/`, `canvases/egyedi_solver/sgh_q43_*.md`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q43_*.yaml`, `codex/codex_checklist/egyedi_solver/sgh_q43_*.md`, `codex/reports/egyedi_solver/sgh_q43_*.md` törlésével a repo Q43 előtti állapota áll vissza.

## Teszt terv

- `python3 scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py` → PASS
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.md` → PASS vagy FAIL (a cargo PATH elérhetőségétől függően)
- `git diff -- rust/vrs_solver/src api worker frontend vrs_nesting` → 0 bájt (pre és post)
- `python3 scripts/build_sgh_q43_comparison_artifacts.py` → comparison_summary + parity_matrix kiírva
- Upstream Run A és Run B futás a `scripts/run_sgh_q43_upstream_sparrow_strip1500x6000.py` által

## Elfogadási kritérium (Q43 spec acceptance)

A Q43 akkor tekinthető késznek, ha:

- Upstream jagua_rs/Sparrow forrás azonosítva / lehúzva.
- Upstream commit hash rögzítve.
- Upstream build dokumentált.
- Full276 LV8 benchmark upstreammel 1500x6000 strip célon lefutott vagy környezeti okból explicit dokumentáltan nem futott.
- 1200 sec runtime mérés elkészült.
- Ha kellett, 2400 sec runtime mérés elkészült.
- Optimalizációs minőség dokumentálva.
- Saját Q42 eredménnyel összehasonlítás készült.
- Direct comparability limitation explicit dokumentálva.
- Semantic parity audit elkészült.
- Parity matrix elkészült.
- Saját solver source nem módosult.
- Smoke lefutott.
- Verify eredmény dokumentált.
