# Demo DXF Készlet (`dxf_demo`)

Ez a mappa tartalmazza a hivatalos demo és smoke test DXF fájlokat, amelyek a `vrs-nesting` rendszer képességeit hivatottak bemutatni és validálni.

## Fájlok és Szerepük

A demo készlet három kulcsfontosságú fájlból áll, amelyek különböző felhasználási eseteket fednek le:

1.  **`stock_rect_1000x2000.dxf`**
    *   **Szerep:** Alapanyag (tábla) definíció.
    *   **Leírás:** Egy egyszerű, 1000x2000 mm méretű téglalap, amely a `CUT_OUTER` rétegen helyezkedik el. Ezen a táblán kerülnek elhelyezésre az alkatrészek.

2.  **`part_arc_spline_chaining_ok.dxf`**
    *   **Szerep:** Komplex, de helyes alkatrész.
    *   **Leírás:** Ez a fájl egy olyan alkatrészt definiál, amelynek külső kontúrja több, egymáshoz kapcsolódó elemből (vonal, ív) áll. Tartalmaz egy belső furatot is (spline-ból), demonstrálva a rendszer geometriai láncolási (`chaining`) és furatfelismerési képességeit. A feldolgozásának sikeresnek kell lennie.

3.  **`part_chain_open_fail.dxf`**
    *   **Szerep:** Szándékosan hibás alkatrész.
    *   **Leírás:** Olyan alkatrészt tartalmaz, amelynek külső kontúrja nincs bezárva (nyitott poligon). Ez a fájl a rendszer hibakezelésének tesztelésére szolgál; a DXF importnak `DXF_OPEN_OUTER_PATH` hibával kell elszállnia.

## Használat

A demo futtatásához és a rendszer ellenőrzéséhez a következő parancsok használhatók:

*   **Gyors smoke teszt (csak import):**
    ```bash
    python3 scripts/smoke_real_dxf_fixtures.py
    ```
*   **Teljes, end-to-end pipeline teszt (import, nesting, export):**
    ```bash
    python3 scripts/smoke_real_dxf_sparrow_pipeline.py
    ```
