#!/usr/bin/env python3
import argparse
import json
import math
import sys
from collections import Counter
from typing import Dict, List, Tuple

EPS = 1e-3  # mm tolerancia
ROT_EPS = 1e-6  # fok tolerancia

def rot_norm_deg(deg: float) -> float:
    # -180 -> 180, 540 -> 180, stb.
    return (deg % 360.0 + 360.0) % 360.0

def transform_points(points: List[List[float]], rot_deg: float, trans: List[float]) -> List[Tuple[float, float]]:
    rad = math.radians(rot_deg)
    c, s = math.cos(rad), math.sin(rad)
    tx, ty = float(trans[0]), float(trans[1])
    out = []
    for p in points:
        x, y = float(p[0]), float(p[1])
        xr = x * c - y * s + tx
        yr = x * s + y * c + ty
        out.append((xr, yr))
    return out

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def require(cond: bool, msg: str):
    if not cond:
        raise ValueError(msg)

def try_overlap_check(placed_polys, area_eps: float):
    try:
        from shapely.geometry import Polygon
        from shapely.affinity import rotate, translate
    except Exception as e:
        raise RuntimeError(
            "Az overlap-check-hez kell a shapely. Telepítés: pip install shapely\n"
            f"Import hiba: {e}"
        )

    overlaps = []
    for i in range(len(placed_polys)):
        (id_a, pts_a, rot_a, tr_a) = placed_polys[i]
        poly_a = Polygon(pts_a)
        poly_a = rotate(poly_a, rot_a, origin=(0, 0), use_radians=False)
        poly_a = translate(poly_a, xoff=tr_a[0], yoff=tr_a[1])

        for j in range(i + 1, len(placed_polys)):
            (id_b, pts_b, rot_b, tr_b) = placed_polys[j]
            poly_b = Polygon(pts_b)
            poly_b = rotate(poly_b, rot_b, origin=(0, 0), use_radians=False)
            poly_b = translate(poly_b, xoff=tr_b[0], yoff=tr_b[1])

            inter = poly_a.intersection(poly_b)
            if (not inter.is_empty) and (inter.area > area_eps):
                overlaps.append((i, j, id_a, id_b, inter.area))

    return overlaps

def main():
    ap = argparse.ArgumentParser(description="Sparrow IO contract validator")
    ap.add_argument("--input", required=True, help="Sparrow input JSON (pl. swim.json)")
    ap.add_argument("--output", required=True, help="Sparrow final output JSON (pl. final_swim.json)")
    ap.add_argument("--overlap-check", action="store_true", help="Poligon átfedés ellenőrzés (shapely kell)")
    ap.add_argument("--overlap-area-eps", type=float, default=1e-6, help="Átfedés area küszöb")
    args = ap.parse_args()

    inp = load_json(args.input)
    out = load_json(args.output)

    # --- Input szerkezet ---
    require("items" in inp and isinstance(inp["items"], list), "Input: hiányzik items[]")
    require("strip_height" in inp, "Input: hiányzik strip_height")
    strip_h = float(inp["strip_height"])

    item_map: Dict[str, dict] = {}
    for it in inp["items"]:
        require("id" in it, "Input item: hiányzik id")
        require("demand" in it, f"Input item {it.get('id')}: hiányzik demand")
        require("allowed_orientations" in it, f"Input item {it.get('id')}: hiányzik allowed_orientations")
        require("shape" in it and isinstance(it["shape"], dict), f"Input item {it.get('id')}: hiányzik shape")
        require(it["shape"].get("type") == "simple_polygon", f"Input item {it.get('id')}: shape.type nem simple_polygon")
        require("data" in it["shape"] and isinstance(it["shape"]["data"], list), f"Input item {it.get('id')}: shape.data hiányzik")

        item_id = str(it["id"])
        require(item_id not in item_map, f"Input: duplikált item id: {item_id}")
        item_map[item_id] = {
            "demand": int(it["demand"]),
            "allowed": [rot_norm_deg(float(a)) for a in it["allowed_orientations"]],
            "poly": it["shape"]["data"],
        }

    demand_sum = sum(v["demand"] for v in item_map.values())

    # --- Output szerkezet ---
    require("solution" in out and isinstance(out["solution"], dict), "Output: hiányzik solution")
    sol = out["solution"]
    require("strip_width" in sol, "Output: hiányzik solution.strip_width")
    strip_w = float(sol["strip_width"])
    require("layout" in sol and isinstance(sol["layout"], dict), "Output: hiányzik solution.layout")
    layout = sol["layout"]
    require("placed_items" in layout and isinstance(layout["placed_items"], list), "Output: hiányzik solution.layout.placed_items[]")

    placed = layout["placed_items"]
    require(len(placed) == demand_sum, f"Darabszám mismatch: placed_items={len(placed)} vs demand_sum={demand_sum}")

    # --- Darabszám per item_id ---
    counts = Counter()
    placed_polys = []  # overlap-check-hez

    for pi in placed:
        require("item_id" in pi, "placed_item: hiányzik item_id")
        require("transformation" in pi and isinstance(pi["transformation"], dict), "placed_item: hiányzik transformation")
        tr = pi["transformation"]
        require("rotation" in tr and "translation" in tr, "placed_item.transformation: kell rotation + translation")

        item_id = str(pi["item_id"])
        require(item_id in item_map, f"placed_item: ismeretlen item_id: {item_id}")

        rot_raw = float(tr["rotation"])
        rot = rot_norm_deg(rot_raw)
        allowed = item_map[item_id]["allowed"]
        is_allowed_rotation = any(math.isclose(rot, a, rel_tol=0.0, abs_tol=ROT_EPS) for a in allowed)
        require(
            is_allowed_rotation,
            f"Rotáció nem engedélyezett: item={item_id} rot_raw={rot_raw} rot_norm={rot} allowed={allowed}",
        )

        trans = tr["translation"]
        require(isinstance(trans, list) and len(trans) == 2, f"Translation invalid: item={item_id} translation={trans}")

        pts = item_map[item_id]["poly"]
        pts_t = transform_points(pts, rot_raw, trans)  # rot_raw-val (előjeles) is jó, de boundsnál mindegy
        xs = [p[0] for p in pts_t]
        ys = [p[1] for p in pts_t]

        require(min(xs) >= -EPS, f"Kilóg balra: item={item_id} min_x={min(xs)}")
        require(min(ys) >= -EPS, f"Kilóg alulra: item={item_id} min_y={min(ys)}")
        require(max(xs) <= strip_w + EPS, f"Kilóg jobbra: item={item_id} max_x={max(xs)} strip_w={strip_w}")
        require(max(ys) <= strip_h + EPS, f"Kilóg felülre: item={item_id} max_y={max(ys)} strip_h={strip_h}")

        counts[item_id] += 1
        placed_polys.append((item_id, pts, rot_raw, [float(trans[0]), float(trans[1])]))

    for item_id, meta in item_map.items():
        require(counts[item_id] == meta["demand"], f"Demand mismatch item={item_id}: placed={counts[item_id]} demand={meta['demand']}")

    # --- Opcionális átfedés check ---
    if args.overlap_check:
        overlaps = try_overlap_check(placed_polys, area_eps=args.overlap_area_eps)
        require(len(overlaps) == 0, f"Átfedés van: {overlaps[:5]} ... (összesen {len(overlaps)})")

    print("PASS ✅")
    print(f" strip_height={strip_h}")
    print(f" strip_width ={strip_w}")
    print(f" placed_items={len(placed)} (demand_sum={demand_sum})")
    if args.overlap_check:
        print(" overlap-check: PASS")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"FAIL ❌ {e}")
        sys.exit(2)
