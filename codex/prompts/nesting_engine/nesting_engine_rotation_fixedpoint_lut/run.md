# codex/prompts/nesting_engine/nesting_engine_rotation_fixedpoint_lut/run.md

Szerep: **VRS_nesting task runner (canvas+YAML+verify fegyelmezett végrehajtás)**

Feladat:
A `rust/nesting_engine` baseline placer rotációjából ki kell venni a nem-ortogonális `f64 sin/cos` ágat, és helyette fixed-point LUT rotációt kell bevezetni.
Mellé platformközi determinism smoke + CI workflow kell, ami ugyanarra a fix inputra ugyanazt az `output_sha256`-t kéri mind x86_64, mind arm64 platformon.

Kötelező szabályok:
- Kövesd az AGENTS.md + codex szabályokat.
- Ne találgass: csak a repó valós fájlstruktúrája és konvenciói alapján dolgozz.
- Csak a YAML step `outputs` listájában szereplő fájlokat hozhatod létre/módosíthatod.
- Minden lépés után tartsd a változtatásokat konzisztenseknek (format/lint/test).
- A végén kötelezően zöld: `./scripts/verify.sh --report ...`

Inputok:
- Canvas: `canvases/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`
- Goal: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_rotation_fixedpoint_lut.yaml`

Végrehajtás:
1) Olvasd be a canvas-t és a YAML-t, majd hajtsd végre a step-eket sorrendben.
2) LUT modul:
   - Hozd létre `rust/nesting_engine/src/geometry/trig_lut.rs`-t konstans táblákkal.
   - A táblákat egyszer generáld (dev futásban), majd forrásként commitold.
   - Implementálj determinisztikus integer round-div helpert.
3) `rotate_point()` átállítás:
   - Nem-ortogonális ágban nulla f64 trig / mm konverzió.
   - i128 köztes számolás, majd i64 kimenet.
4) Rust unit test:
   - nem-ortogonális fok (pl. 17°), fix bemenet -> fix i64 kimenet.
5) Platform smoke:
   - Hozd létre a `scripts/smoke_platform_determinism_rotation.sh` scriptet.
   - A script elején legyen egy `EXPECTED_OUTPUT_SHA256=...` konstans.
   - Először futtasd a scriptet úgy, hogy kiírd a kapott hash-t, majd rögzítsd az EXPECTED értéket.
6) CI workflow:
   - `platform-determinism-rotation.yml` két jobbal (x86_64 + arm64).
   - Mindkettő futtassa a smoke scriptet.
7) Checklist + report:
   - DoD pipák, reportban a döntések és a rögzített hash.
8) Futass verify-t:
   `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`
   és mentsd a logot:
   `codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.verify.log`

Kimenetek:
- `canvases/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`
- `rust/nesting_engine/src/geometry/trig_lut.rs`
- `rust/nesting_engine/src/geometry/mod.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `docs/nesting_engine/architecture.md`
- `scripts/smoke_platform_determinism_rotation.sh`
- `.github/workflows/platform-determinism-rotation.yml`
- `codex/codex_checklist/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`
- `codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`
- `codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.verify.log`

Ha az arm64 hosted runner nem elérhető a repo-nak, akkor a workflow jobban legyen egyértelmű, hogy miért skip/fail (ne legyen néma zöldítés).