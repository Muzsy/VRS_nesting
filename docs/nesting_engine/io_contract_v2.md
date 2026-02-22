# Nesting Engine IO Contract v2

## 1. Verzió és kontextus

- Contract azonosito: `nesting_engine_v2`
- Cél: a Python runner es a `rust/nesting_engine` kozti stabil JSON hatarfelulet.
- A v2 fuggetlen a v1 contracttol (`docs/solver_io_contract.md`), nem backward kompatibilis.
- A belso geometry SCALE konverzio (`mm <-> i64`) implementacios reszlet, nem jelenik meg a JSON hataron.

## 2. Input contract (`sample_input_v2.json` szerkezet)

| Mezo | Tipus | Kotelezo | Leiras | Egyseg |
|---|---|---|---|---|
| `version` | string | Igen | Contract verzio, erteke mindig `nesting_engine_v2` | - |
| `seed` | integer (`>=0`) | Igen | Determinisztikus futas seedje | - |
| `time_limit_sec` | integer (`>0`) | Igen | Solver ido limit | sec |
| `sheet` | object | Igen | Tabla beallitasok | - |
| `sheet.width_mm` | number (`>0`) | Igen | Tabla szelesseg | mm |
| `sheet.height_mm` | number (`>0`) | Igen | Tabla magassag | mm |
| `sheet.kerf_mm` | number (`>=0`) | Igen | Vagasi res (kerf) | mm |
| `sheet.margin_mm` | number (`>=0`) | Igen | Biztonsagi tabla margó | mm |
| `parts` | array (nem ures) | Igen | Nestelendo alkatresz tipuskeszlet | - |
| `parts[].id` | string | Igen | Egyedi part tipuskod | - |
| `parts[].quantity` | integer (`>0`) | Igen | Gyartando peldanyszam | db |
| `parts[].allowed_rotations_deg` | array&lt;integer&gt; (nem ures) | Igen | Megengedett forgatasok | deg |
| `parts[].outer_points_mm` | array&lt;[number,number]&gt; (`>=3`) | Igen | Kulso kontur pontjai | mm |
| `parts[].holes_points_mm` | array&lt;array&lt;[number,number]&gt;&gt; | Igen | Lyuk konturok listaja, ha nincs lyuk: `[]` | mm |

### Input invariansok

- A koordinatak a tabla helyi koordinatarendszereben vannak.
- `outer_points_mm` kontur: legalabb 3 pont, outer irany CCW.
- `holes_points_mm` konturok: legalabb 3 pont/lyuk, lyuk irany CW.
- Az input geometria nominalis (nem inflated).

## 3. Output contract (`sample_output_v2.json` szerkezet)

| Mezo | Tipus | Kotelezo | Leiras | Egyseg |
|---|---|---|---|---|
| `version` | string | Igen | Contract verzio, erteke mindig `nesting_engine_v2` | - |
| `seed` | integer | Igen | Input seed echo | - |
| `solver_version` | string | Igen | Solver build/verzio azonosito | - |
| `status` | string (`ok` vagy `partial`) | Igen | Teljes vagy reszleges elhelyezes | - |
| `sheets_used` | integer (`>=0`) | Igen | Felhasznalt tablak szama | db |
| `placements` | array | Igen | Elhelyezett peldanyok | - |
| `placements[].part_id` | string | Igen | Part tipus azonosito | - |
| `placements[].instance` | integer (`>=0`) | Igen | 0-bazisu peldany index ugyanazon `part_id`-n belul | - |
| `placements[].sheet` | integer (`>=0`) | Igen | 0-bazisu tabla index | - |
| `placements[].x_mm` | number | Igen | Elhelyezes X koordinata | mm |
| `placements[].y_mm` | number | Igen | Elhelyezes Y koordinata | mm |
| `placements[].rotation_deg` | integer | Igen | Tenyeges forgatas, az inputban engedelyezettek egyike | deg |
| `unplaced` | array | Igen | El nem helyezett peldanyok | - |
| `unplaced[].part_id` | string | Igen | Part tipus azonosito | - |
| `unplaced[].instance` | integer (`>=0`) | Igen | Peldany index | - |
| `unplaced[].reason` | string | Igen | Elhelyezes sikertelensegenek oka | - |
| `objective` | object | Igen | Cel-fuggveny osszegzes | - |
| `objective.sheets_used` | integer (`>=0`) | Igen | Elsoleges cel metrika | db |
| `objective.utilization_pct` | number (`0..100`) | Igen | Tabla-kihasznaltsag | % |
| `meta` | object | Igen | Futasi metaadatok | - |
| `meta.elapsed_sec` | number (`>=0`) | Igen | Futasido | sec |
| `meta.determinism_hash` | string | Igen | Determinisztikus hash ertek | - |
| `_note` | string | Nem | Emberi megjegyzes, illusztracios mintakhoz | - |

## 4. Geometria egyezmenyek (kobe vesett)

```text
1) Koordinata-rendszer: origo = tabla bal-also sarok (0,0), X jobbra, Y felfele.
2) Kontur-irany: outer kontur CCW, hole kontur CW.
3) Egység: JSON hataron kizarolag mm (f64/number).
4) Nominalis vs. inflated: input es output koordinatak nominalis geometriat irnak le.
   A kerf/margin inflate belso solver lepes, nem kulon output mező.
5) Elhelyezesi transzformacio: a part lokal pontjai `rotation_deg` szerint
   forognak, majd `(x_mm, y_mm)` eltolast kapnak.
```

## 5. `unplaced.reason` kodok

| Kod | Jelentes |
|---|---|
| `PART_NEVER_FITS_SHEET` | A part nominalis + belso inflate utan sem fer el a hasznos tabla teruleten. |
| `TIME_LIMIT_EXCEEDED` | A `time_limit_sec` limit elert, mielott minden peldany elhelyezheto lett volna. |

## 6. `determinism_hash` szamitasi mod (normativ hivatkozas)

A `meta.determinism_hash` mezo szamitasi szabalyai normativan itt vannak rogzitve:
`docs/nesting_engine/json_canonicalization.md`.

Ebben a dokumentumban nincs canonicalization-szabaly duplikacio: a hash-kepzeshez a
fenti normativ dokumentum kovetese kotelezo.

## 7. v1 <-> v2 osszehasonlitas

| Aspektus | v1 (`docs/solver_io_contract.md`) | v2 (`docs/nesting_engine/io_contract_v2.md`) |
|---|---|---|
| Contract azonosito | `contract_version: v1` | `version: nesting_engine_v2` |
| Scope | Altalanos solver boundary | Kifejezetten `nesting_engine` boundary |
| Idolimit mezo | `time_limit_s` | `time_limit_sec` |
| Tabla leiras | `stocks[]` (width/height/shape opciok) | `sheet` (width/height/kerf/margin) |
| Part geometria | `outer_points` / `holes_points` (opcionalis) | `outer_points_mm` / `holes_points_mm` (explicit mm) |
| Kimeneti placement mezok | `instance_id`, `sheet_index`, `x`, `y` | `instance`, `sheet`, `x_mm`, `y_mm` |
| Objective | opcionális `metrics` | kotelezo `objective` |
| Determinizmus hash | nincs definialva | kotelezo `meta.determinism_hash` normativ szaballyal |
| Kompatibilitas | aktiv v1 contract | kulonallo v2 contract |
