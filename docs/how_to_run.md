# Hogyan Futtassuk a VRS-Nesting Rendszert?

Ez az útmutató bemutatja, hogyan lehet a `vrs-nesting` alkalmazást telepíteni, beállítani és futtatni a mellékelt demo DXF fájlokkal.

## 1. Előfeltételek

A rendszer futtatásához a következő eszközökre van szükség:

*   **Python:** Verzió: 3.10 vagy újabb.
*   **Rust & Cargo (Opcionális, de ajánlott):** A Sparrow nesting solver fordításához. Ha ez nem érhető el, a rendszer megpróbálja letölteni a már lefordított binárist.

## 2. Telepítés és Beállítás

Kövesd az alábbi lépéseket a környezet előkészítéséhez:

### 1. Klónozd a Repozitóriumot

```bash
git clone <repo_url>
cd vrs-nesting
```

### 2. Hozz létre egy Virtuális Környezetet

Ajánlott egy dedikált Python virtuális környezetet használni a függőségek izolálásához.

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Telepítsd a Függőségeket

A projekthez tartozó Python csomagok telepítése a `pip-tools` segítségével történik, ami biztosítja a rögzített függőségeket.

```bash
pip install pip-tools
pip-sync requirements.txt requirements-dev.txt
```

### 4. Sparrow Nesting Solver Telepítése

A Sparrow a központi nesting motor. Az alábbi szkript letölti és/vagy lefordítja a megfelelő verziót.

```bash
./scripts/ensure_sparrow.sh
```

Sikeres futás esetén a `vendor/sparrow/bin/sparrow` binárisnak léteznie kell.

## 3. Demo Futtatása

A rendszer képességeit a `samples/dxf_demo` mappában található fájlokkal tudod tesztelni. A következő parancs egy teljes, end-to-end futtatást indít:

*   Importálja a DXF fájlokat.
*   Kinyeri a geometriákat.
*   Meghívja a Sparrow solvert az optimális elrendezés kiszámításához.
*   DXF formátumba exportálja a végeredményt.

### Futtatási Parancs

```bash
python -m vrs_nesting.cli run-solver-pipeline \
    --project-file samples/project_rect_1000x2000_with_examples.json \
    --output-dir run_artifacts/demo_run
```

### Várt Kimenet

A parancs sikeres lefutása után a kimeneti fájlok a `run_artifacts/demo_run` mappába kerülnek. A mappa tartalma a következőképpen néz ki:

*   **`input_geometry.json`**: A bemeneti DXF-ekből kinyert, egységesített geometriai adatok.
*   **`sparrow_input.json`**: A Sparrow solver számára generált bemeneti JSON.
*   **`sparrow_output.json`**: A Sparrow solver által visszaadott nyers eredmény.
*   **`nesting_solution.json`**: A feldolgozott, validált nesting eredmény.
*   **`output/`**: Ez a mappa tartalmazza a végső, vizuálisan is ellenőrizhető DXF fájlokat, táblánként csoportosítva (pl. `SHEET_1.dxf`, `SHEET_2.dxf` stb.).

## 4. Ellenőrzés

A teljes projekt minőségét és a demo helyes működését a `./scripts/check.sh` paranccsal ellenőrizheted. Ennek sikeresen le kell futnia, ha a telepítés és a futtatás rendben volt.

```bash
./scripts/check.sh
```
