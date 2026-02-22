# nesting_engine_rotation_fixedpoint_lut

## 🎯 Funkció

A `rust/nesting_engine` baseline placer rotációja (jelenleg `f64 sin/cos` a nem ortogonális szögeknél) platformfüggő ULP-eltéréseket okozhat.
Ezt kiváltjuk **fixed-point trigonometrikus LUT**-tal, hogy a rotáció **bit-azonos** legyen különböző CPU architektúrákon (x86_64 vs arm64).

Kötelező: mellé kerül egy **platformközi determinism teszt**, ami ugyanarra a fix inputra mindkét platformon azonos, előre rögzített hash-t követel meg.

## 🧠 Fejlesztési részletek

### Érintett kód (valós fájlok)
- `rust/nesting_engine/src/placement/blf.rs`
  - `rotate_point()` jelenleg: 0/90/180/270 egész művelet, egyébként `f64` trig + `mm_to_i64`.
  - Cél: a nem-ortogonális ágban se legyen `f64`, hanem integer/fixed-point rotáció.
- `rust/nesting_engine/src/geometry/scale.rs`
  - SCALE = 1_000_000; a koordináták µm-ben i64.
- `vrs_nesting/runner/nesting_engine_runner.py`
  - `output_sha256` a `nesting_output.json` nyers byte-hash-e.
  - A nyers output tartalmaz `meta.elapsed_sec` mezőt, ezért futásidőfüggő lehet; a platform smoke emiatt normalizált hash-t ellenőriz.
- CI workflow-k:
  - már létezik `nesttool-smoketest.yml`, `repo-gate.yml` stb.
  - ehhez új, célzott cross-arch workflow kerül be.

### Megoldás: fixed-point LUT
- Új modul: `rust/nesting_engine/src/geometry/trig_lut.rs`
- LUT: 0..=359 fokhoz **(cos, sin)** értékek egész számmal:
  - `TRIG_SCALE = 1_000_000_000` (Q=1e9)
  - `COS_Q[deg]`, `SIN_Q[deg]` i64
- Rotáció integerben (p.x, p.y már i64 SCALE-ben):
  - `x' = round_div(p.x * cos - p.y * sin, TRIG_SCALE)`
  - `y' = round_div(p.x * sin + p.y * cos, TRIG_SCALE)`
  - műveletek i128-ben, végül i64.
- Rounding: determinisztikus, explicit (“half away from zero” vagy “ties to nearest away”) – a szabály legyen kódolva saját helperrel, ne a nyelv defaultjára hagyva.
- Ortogonális ág maradhat gyors, tiszta integer (0/90/180/270).

### LUT generálás
- A LUT táblát egyszer generáljuk és forrásként commitoljuk (nem runtime számoljuk).
- Generálás módja:
  - Codex a task futás során generálja a táblát egy egyszeri scriptből (pl. Python a repo-ban ideiglenesen), majd a végleges LUT a `trig_lut.rs`-be kerül.
  - A build-ben nincs szükség extra build.rs-re (egyszerűbb).

### Platformközi determinism teszt
- Új script: `scripts/smoke_platform_determinism_rotation.sh`
  - Buildeli a `rust/nesting_engine` release binárist.
  - Lefuttatja a `nesting_engine` pipeline-t egy fix inputon, ahol `allowed_rotations_deg` tartalmaz **nem ortogonális** szöget (pl. 17°), hogy biztosan a LUT ág fusson.
  - Kiolvassa `runner_meta.json`-ból a nyers `output_sha256`-t (debug információként).
  - `nesting_output.json`-ból egy normalizált, kanonikus hash-t számol ( `meta.elapsed_sec = 0.0` normalizálás + rendezett JSON dump), és ezt veti össze az `EXPECTED_OUTPUT_SHA256` konstanssal.
- Új GitHub workflow: `.github/workflows/platform-determinism-rotation.yml`
  - két job / matrix:
    - `ubuntu-latest` (x86_64)
    - `ubuntu-24.04-arm64` (arm64 GitHub-hosted) – ha a repo eddig nem használ ilyet, akkor a YAML-ben legyen fallback/clear failure message.
  - mindkettő futtatja ugyanazt a scriptet.

### DoD (elfogadási kritérium)
- `rotate_point()` nem használ `f64 sin/cos` nem-ortogonális esetben.
- LUT modul létezik, és a rotáció i128 köztes szorzatokkal overflow-biztos.
- Van unit teszt Rust oldalon, ami egy nem-ortogonális fokra fix pontokat elforgat és **egzakt** i64 eredményt vár (platformfüggetlen).
- A platform smoke script rögzített, normalizált output hash-t ellenőriz.
- CI workflow fut legalább x86_64-en; ha arm64 runner elérhető, ott is. (A cél az, hogy mindkettő zöld.)
- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md` zöld.

## 🧪 Tesztállapot

- Rust unit test: LUT determinisztikus rotáció (nem trig approximáció ellenőrzése, hanem “kód útvonal és integer output stabil”).
- Platform smoke: `scripts/smoke_platform_determinism_rotation.sh`

## 🌍 Lokalizáció

Nincs UI szöveg. Script/CI log angol, rövid, stabil.

## 📎 Kapcsolódások

- `rust/nesting_engine/src/placement/blf.rs` (rotate_point)
- `rust/nesting_engine/src/export/output_v2.rs` (determinism_hash, placement serializáció)
- `vrs_nesting/runner/nesting_engine_runner.py` (output hash meta)
- `.github/workflows/nesttool-smoketest.yml` (minták build+run)
- `docs/nesting_engine/json_canonicalization.md` (determinism koncepció)
