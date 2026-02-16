# Hogyan futtasd a VRS-Nesting projektet

Ez az útmutató bemutatja, hogyan telepítsd, konfiguráld és futtasd a DXF-alapú nesting pipeline-t a mellékelt demo készlettel.

## 1. Előfeltételek

- **Python:** 3.10 vagy újabb.
- **Rust Toolchain (opcionális, de ajánlott):** A Sparrow nesting szoftver fordításához szükséges a `cargo` és a `rustc`. Ha ez nem áll rendelkezésre, a rendszer megpróbálja letölteni a `vendor/` mappába.

## 2. Telepítés és beállítás

1.  **Virtuális környezet létrehozása:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Függőségek telepítése:**

    A projekt `pip-tools` segítségével kezeli a függőségeket a reprodukálhatóság érdekében.

    ```bash
    pip install pip-tools
    pip-sync requirements.txt requirements-dev.txt
    ```

3.  **Sparrow Nesting Engine beszerzése:**

    A beágyazott nesting szoftver biztosításához futtasd a következő parancsot. Ez letölti vagy lefordítja a Sparrow-t a `vendor/sparrow/` mappába.

    ```bash
    ./scripts/ensure_sparrow.sh
    ```

## 3. Demo futtatása

A projekt CLI-n keresztül futtatható. Az alábbi parancs elindítja a teljes pipeline-t a `samples/dxf_demo` mappában található DXF fájlokkal.

- **Alapanyag:** `stock_rect_1000x2000.dxf`
- **Alkatrészek:** `part_arc_spline_chaining_ok.dxf` (20 db)
- **Hibaellenőrzés:** A pipeline a futás során validálja a bemeneteket.

```bash
python -m vrs_nesting.cli run-solver-pipeline \
  --stock-dxf samples/dxf_demo/stock_rect_1000x2000.dxf \
  --part-dxf samples/dxf_demo/part_arc_spline_chaining_ok.dxf \
  --part-quantity 20
```

## 4. Várt kimenet

A futás eredménye a `run_artifacts/` mappában jön létre, egyedi időbélyeggel ellátott alkönyvtárban. Például:
`run_artifacts/run_20240520_143000/`

**A kimeneti mappában található kulcsfontosságú fájlok:**

- `in/`: A feldolgozott, egységesített bemeneti adatok.
- `out/`: Az optimalizált kiosztás eredménye.
  - `layouts.dxf`: A végső, táblákra rendezett DXF kimenet.
  - `summary.json`: A futás összegzése (felhasznált táblák, hulladék stb.).
- `logs/`: A futással kapcsolatos logok.
- `run_command.sh`: A futtatást előidéző parancs.

## 5. Hibakezelés

Ha hibás geometriát (pl. nyitott kontúrt) tartalmazó DXF-et adsz meg, a rendszer hibát fog jelezni, és a futás leáll. Példa hibás futtatásra:

```bash
python -m vrs_nesting.cli run-solver-pipeline \
  --stock-dxf samples/dxf_demo/stock_rect_1000x2000.dxf \
  --part-dxf samples/dxf_demo/part_chain_open_fail.dxf \
  --part-quantity 1
```
