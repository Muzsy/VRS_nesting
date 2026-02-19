import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, WheelEvent } from "react";
import type { ViewerPlacement } from "../lib/types";

interface ViewerCanvasProps {
  sheetIndex: number;
  svgUrl: string | null;
  placements: ViewerPlacement[];
  onSvgError?: () => void;
}

interface Point {
  x: number;
  y: number;
}

interface PlacementGeometry {
  source: ViewerPlacement;
  corners: Point[];
}

interface ProjectedPlacement {
  source: ViewerPlacement;
  points: Point[];
  center: Point;
}

interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

const VIEW_W = 1000;
const VIEW_H = 700;

function rotatePoint(point: Point, origin: Point, angleDeg: number): Point {
  const angleRad = (angleDeg * Math.PI) / 180;
  const c = Math.cos(angleRad);
  const s = Math.sin(angleRad);
  const dx = point.x - origin.x;
  const dy = point.y - origin.y;
  return {
    x: origin.x + dx * c - dy * s,
    y: origin.y + dx * s + dy * c,
  };
}

function placementToGeometry(item: ViewerPlacement): PlacementGeometry {
  const width = item.width_mm > 0 ? item.width_mm : 10;
  const height = item.height_mm > 0 ? item.height_mm : 10;

  const origin: Point = { x: item.x, y: item.y };
  const rect = [
    { x: item.x, y: item.y },
    { x: item.x + width, y: item.y },
    { x: item.x + width, y: item.y + height },
    { x: item.x, y: item.y + height },
  ];

  const corners = rect.map((point) => rotatePoint(point, origin, item.rotation_deg));
  return { source: item, corners };
}

function computeBounds(items: PlacementGeometry[]): Bounds {
  if (items.length === 0) {
    return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const item of items) {
    for (const point of item.corners) {
      minX = Math.min(minX, point.x);
      minY = Math.min(minY, point.y);
      maxX = Math.max(maxX, point.x);
      maxY = Math.max(maxY, point.y);
    }
  }

  if (minX === maxX) {
    maxX += 1;
  }
  if (minY === maxY) {
    maxY += 1;
  }

  return { minX, minY, maxX, maxY };
}

function projectPoint(point: Point, bounds: Bounds): Point {
  const scaleX = VIEW_W / (bounds.maxX - bounds.minX);
  const scaleY = VIEW_H / (bounds.maxY - bounds.minY);
  return {
    x: (point.x - bounds.minX) * scaleX,
    y: VIEW_H - (point.y - bounds.minY) * scaleY,
  };
}

function pointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;

    const intersect = yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / ((yj - yi) || 1e-9) + xi;
    if (intersect) {
      inside = !inside;
    }
  }
  return inside;
}

function polygonCenter(points: Point[]): Point {
  let sx = 0;
  let sy = 0;
  for (const point of points) {
    sx += point.x;
    sy += point.y;
  }
  return {
    x: sx / points.length,
    y: sy / points.length,
  };
}

export function ViewerCanvas({ sheetIndex, svgUrl, placements, onSvgError }: ViewerCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState<ProjectedPlacement | null>(null);
  const [selected, setSelected] = useState<ProjectedPlacement | null>(null);
  const [dragOrigin, setDragOrigin] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderMode: "svg" | "canvas" = placements.length > 300 ? "canvas" : "svg";

  const geometries = useMemo(() => placements.map(placementToGeometry), [placements]);
  const bounds = useMemo(() => computeBounds(geometries), [geometries]);

  const projected = useMemo<ProjectedPlacement[]>(
    () =>
      geometries.map((item) => {
        const points = item.corners.map((point) => projectPoint(point, bounds));
        return {
          source: item.source,
          points,
          center: polygonCenter(points),
        };
      }),
    [geometries, bounds]
  );

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setHovered(null);
    setSelected(null);
    setDragging(false);
    setDragOrigin(null);
  }, [sheetIndex]);

  useEffect(() => {
    if (renderMode !== "canvas") {
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    ctx.clearRect(0, 0, VIEW_W, VIEW_H);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    ctx.strokeStyle = "#e2e8f0";
    ctx.strokeRect(0.5, 0.5, VIEW_W - 1, VIEW_H - 1);

    for (const item of projected) {
      ctx.beginPath();
      ctx.moveTo(item.points[0].x, item.points[0].y);
      for (let i = 1; i < item.points.length; i += 1) {
        ctx.lineTo(item.points[i].x, item.points[i].y);
      }
      ctx.closePath();
      const isSelected = selected?.source.instance_id === item.source.instance_id;
      ctx.fillStyle = isSelected ? "rgba(220,38,38,0.35)" : "rgba(2,132,199,0.32)";
      ctx.strokeStyle = isSelected ? "#dc2626" : "#0f172a";
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.fill();
      ctx.stroke();
    }
  }, [projected, renderMode, selected]);

  function fitToScreen() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const delta = event.deltaY > 0 ? -0.1 : 0.1;
    setZoom((prev) => Math.min(4, Math.max(0.4, Number((prev + delta).toFixed(2)))));
  }

  function handleMouseDown(event: MouseEvent<HTMLDivElement>) {
    setDragging(true);
    setDragOrigin({ x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y });
  }

  function handleMouseUp() {
    setDragging(false);
    setDragOrigin(null);
  }

  function pickPlacementAt(localPoint: Point): ProjectedPlacement | null {
    for (let i = projected.length - 1; i >= 0; i -= 1) {
      if (pointInPolygon(localPoint, projected[i].points)) {
        return projected[i];
      }
    }
    return null;
  }

  function handleMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (dragging && dragOrigin) {
      const dx = event.clientX - dragOrigin.x;
      const dy = event.clientY - dragOrigin.y;
      setPan({ x: dragOrigin.panX + dx, y: dragOrigin.panY + dy });
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const localPoint = {
      x: (event.clientX - rect.left - pan.x) / zoom,
      y: (event.clientY - rect.top - pan.y) / zoom,
    };
    setHovered(pickPlacementAt(localPoint));
  }

  function handleCanvasClick(event: MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const localPoint = {
      x: (event.clientX - rect.left - pan.x) / zoom,
      y: (event.clientY - rect.top - pan.y) / zoom,
    };
    setSelected(pickPlacementAt(localPoint));
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
      <div>
        <div className="mb-2 flex items-center justify-between text-sm text-slate">
          <div className="flex items-center gap-2">
            <span>Sheet #{sheetIndex + 1}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">mode: {renderMode}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">parts: {placements.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={() => setZoom((z) => Math.min(4, z + 0.1))} type="button">
              +
            </button>
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))} type="button">
              -
            </button>
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={fitToScreen} type="button">
              Fit
            </button>
          </div>
        </div>

        <div
          className="relative h-[540px] overflow-hidden rounded-xl border border-mist bg-slate-100"
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseLeave={handleMouseUp}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          role="presentation"
        >
          <div
            className="absolute left-1/2 top-1/2"
            style={{
              width: VIEW_W,
              height: VIEW_H,
              transform: `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${zoom})`,
              transformOrigin: "center center",
            }}
          >
            {svgUrl ? (
              <img
                alt={`Sheet ${sheetIndex + 1}`}
                className="absolute inset-0 h-full w-full object-contain opacity-85"
                draggable={false}
                onError={onSvgError}
                src={svgUrl}
              />
            ) : (
              <div className="absolute inset-0 border border-dashed border-slate-400 bg-slate-50" />
            )}

            {renderMode === "canvas" ? (
              <canvas className="absolute inset-0 h-full w-full" height={VIEW_H} ref={canvasRef} width={VIEW_W} />
            ) : (
              <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}>
                {projected.map((item) => {
                  const isSelected = selected?.source.instance_id === item.source.instance_id;
                  const pointsAttr = item.points.map((point) => `${point.x},${point.y}`).join(" ");
                  return (
                    <polygon
                      fill={isSelected ? "rgba(220,38,38,0.36)" : "rgba(2,132,199,0.30)"}
                      key={item.source.instance_id}
                      onClick={() => setSelected(item)}
                      onMouseEnter={() => setHovered(item)}
                      onMouseLeave={() => setHovered(null)}
                      points={pointsAttr}
                      stroke={isSelected ? "#dc2626" : "#0f172a"}
                      strokeWidth={isSelected ? 2 : 1}
                    />
                  );
                })}
              </svg>
            )}
          </div>

          {hovered && (
            <div className="pointer-events-none absolute right-3 top-3 rounded-md border border-mist bg-white/95 px-3 py-2 text-xs shadow-sm">
              <p>
                <strong>{hovered.source.part_id}</strong>
              </p>
              <p>Instance: {hovered.source.instance_id}</p>
              <p>
                X/Y: {hovered.source.x.toFixed(2)} / {hovered.source.y.toFixed(2)}
              </p>
              <p>
                W/H: {hovered.source.width_mm.toFixed(2)} / {hovered.source.height_mm.toFixed(2)}
              </p>
            </div>
          )}
        </div>
      </div>

      <aside className="rounded-xl border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Selection details</h3>
        {!selected && <p className="mt-2 text-sm text-slate">Click a part geometry to inspect placement properties.</p>}
        {selected && (
          <dl className="mt-2 space-y-2 text-sm">
            <div>
              <dt className="text-slate">Part</dt>
              <dd className="font-medium text-ink">{selected.source.part_id}</dd>
            </div>
            <div>
              <dt className="text-slate">Instance</dt>
              <dd className="font-medium text-ink">{selected.source.instance_id}</dd>
            </div>
            <div>
              <dt className="text-slate">Coordinates</dt>
              <dd className="font-medium text-ink">
                {selected.source.x.toFixed(3)} / {selected.source.y.toFixed(3)}
              </dd>
            </div>
            <div>
              <dt className="text-slate">Size</dt>
              <dd className="font-medium text-ink">
                {selected.source.width_mm.toFixed(3)} / {selected.source.height_mm.toFixed(3)}
              </dd>
            </div>
            <div>
              <dt className="text-slate">Rotation</dt>
              <dd className="font-medium text-ink">{selected.source.rotation_deg.toFixed(1)} deg</dd>
            </div>
            <div>
              <dt className="text-slate">Center (projected)</dt>
              <dd className="font-medium text-ink">
                {selected.center.x.toFixed(1)} / {selected.center.y.toFixed(1)}
              </dd>
            </div>
          </dl>
        )}
      </aside>
    </div>
  );
}
