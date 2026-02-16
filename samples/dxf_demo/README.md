# Demo DXF készlet

Ez a mappa a `vrs-nesting` pipeline end-to-end teszteléséhez és demonstrálásához szükséges DXF fájlokat tartalmazza.

## Fájlok

1.  `stock_rect_1000x2000.dxf`
    *   **Szerep:** Alapanyag (stock).
    *   **Leírás:** Egy 1000x2000 egység méretű téglalap, amelyre a nesting algoritmus az alkatrészeket helyezi.

2.  `part_arc_spline_chaining_ok.dxf`
    *   **Szerep:** Helyes, komplex alkatrész (part).
    *   **Leírás:** Olyan alkatrészt definiál, amely íveket és spline-okat is tartalmaz. A geometria-feldolgozó réteg (pl. poligonizáció) helyes működését teszteli. A kontúr zárt és feldolgozhatónak kell lennie.

3.  `part_chain_open_fail.dxf`
    *   **Szerep:** Szándékosan hibás alkatrész (part).
    *   **Leírás:** Olyan alkatrészt tartalmaz, amelynek a kontúrja nem zárt. Az importálási és validálási lépcső hibakezelését teszteli. A rendszernek ezt a fájlt hibaként kell azonosítania és elutasítania.
