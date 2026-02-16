# Hogyan futtasd a VRS-Nesting demót?

Ez az útmutató bemutatja, hogyan telepítsd, konfiguráld és futtasd a `vrs-nesting` projekt demo pipeline-ját helyi környezetben.

## 1. Előfeltételek

-   **Python:** 3.10 vagy újabb.
-   **Rust/Cargo:** Opcionális, de erősen ajánlott. A `./scripts/ensure_sparrow.sh` szkript megpróbálja automatikusan letölteni a Sparrow binárist, de ha ez nem sikerül, a Rust toolchain segítségével helyben is lefordítható.

## 2. Telepítés és beállítás

1.  **Hozd létre és aktiváld a virtuális környezetet:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Telepítsd a függőségeket:**

    A projekt `pip-tools` segítségével kezeli a függőségeket a reprodukálhatóság érdekében. A `pip-sync` parancs biztosítja, hogy a virtuális környezeted pontosan megegyezzen a `requirements.txt` és `requirements-dev.txt` fájlokban rögzített verziókkal.

    ```bash
    pip install pip-tools
    pip-sync requirements.txt requirements-dev.txt
    ```

3.  **Győződj meg a Sparrow Nesting Solver elérhetőségéről:**

    A Sparrow egy külső, Rust-alapú nesting algoritmus. A következő parancs letölti vagy lefordítja a megfelelő binárist a `vendor/` mappába.

    ```bash
    ./scripts/ensure_sparrow.sh
    ```

## 3. Demo futtatása

A `vrs_nesting` csomag futtatható modulként is működik. A következő parancs elindítja a teljes DXF-to-DXF pipeline-t a `samples/dxf_demo/` mappában található fájlokkal.

```bash
python -m vrs_nesting.cli run_solver_pipeline \
    --project-file samples/project_rect_1000x2000_with_examples.json \
    --dxf-input-dir samples/dxf_demo \
    --output-dir run_artifacts/mvp_demo_run
```

Ez a parancs:

1.  Beolvassa a projekt definíciót (`project_rect_1000x2000_with_examples.json`).
2.  Importálja a DXF fájlokat a `samples/dxf_demo` mappából.
3.  Futtatja a Sparrow nesting algoritmust.
4.  A végeredményt (a nestingelt terítékrajzot) a `run_artifacts/mvp_demo_run` mappába menti DXF formátumban.

## 4. Várt kimenet

A sikeres futás után a `run_artifacts/mvp_demo_run` mappa jön létre, amely tartalmazza a futás közbeni állapotokat (pl. `geometry_pipeline_out.json`) és a végső, optimalizált DXF-et (`final_nesting_result.dxf`).

A parancssori kimenetnek `INFO` és `DEBUG` üzeneteket kell mutatnia a feldolgozás lépéseiről, hibaüzenet nélkül (kivéve a `part_chain_open_fail.dxf` szándékolt hibáját, amit a rendszernek jeleznie kell).
