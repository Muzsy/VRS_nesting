import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, WheelEvent } from "react";
import type { ViewerPlacement } from "../lib/types";

interface ViewerCanvasProps {
  sheetIndex: number;
  svgUrl: string | null;
  placements: ViewerPlacement[];
}

interface ProjectedPlacement {
  source: ViewerPlacement;
  px: number;
  py: number;
}

interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

const VIEW_W = 1000;
const VIEW_H = 700;

function computeBounds(items: ViewerPlacement[]): Bounds {
  if (items.length === 0) {
    return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
  }
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const item of items) {
    minX = Math.min(minX, item.x);
    minY = Math.min(minY, item.y);
    maxX = Math.max(maxX, item.x);
    maxY = Math.max(maxY, item.y);
  }
  if (minX === maxX) {
    maxX += 1;
  }
  if (minY === maxY) {
    maxY += 1;
  }
  return { minX, minY, maxX, maxY };
}

function projectPoint(item: ViewerPlacement, bounds: Bounds): { px: number; py: number } {
  const scaleX = VIEW_W / (bounds.maxX - bounds.minX);
  const scaleY = VIEW_H / (bounds.maxY - bounds.minY);
  return {
    px: (item.x - bounds.minX) * scaleX,
    py: VIEW_H - (item.y - bounds.minY) * scaleY,
  };
}

export function ViewerCanvas({ sheetIndex, svgUrl, placements }: ViewerCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState<ProjectedPlacement | null>(null);
  const [selected, setSelected] = useState<ProjectedPlacement | null>(null);
  const [dragOrigin, setDragOrigin] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderMode: "svg" | "canvas" = placements.length > 300 ? "canvas" : "svg";
  const bounds = useMemo(() => computeBounds(placements), [placements]);

  const projected = useMemo<ProjectedPlacement[]>(
    () =>
      placements.map((item) => {
        const point = projectPoint(item, bounds);
        return { source: item, px: point.px, py: point.py };
      }),
    [placements, bounds]
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
      ctx.arc(item.px, item.py, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = "#0284c7";
      ctx.fill();
    }

    if (selected) {
      ctx.beginPath();
      ctx.arc(selected.px, selected.py, 7, 0, Math.PI * 2);
      ctx.strokeStyle = "#dc2626";
      ctx.lineWidth = 2;
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

  function handleMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (dragging && dragOrigin) {
      const dx = event.clientX - dragOrigin.x;
      const dy = event.clientY - dragOrigin.y;
      setPan({ x: dragOrigin.panX + dx, y: dragOrigin.panY + dy });
      return;
    }

    if (renderMode !== "canvas") {
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const localX = (event.clientX - rect.left - pan.x) / zoom;
    const localY = (event.clientY - rect.top - pan.y) / zoom;

    let nearest: ProjectedPlacement | null = null;
    let nearestDistance = 14;
    for (const point of projected) {
      const distance = Math.hypot(point.px - localX, point.py - localY);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    }
    setHovered(nearest);
  }

  function handleCanvasClick(event: MouseEvent<HTMLDivElement>) {
    if (renderMode !== "canvas") {
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const localX = (event.clientX - rect.left - pan.x) / zoom;
    const localY = (event.clientY - rect.top - pan.y) / zoom;

    let nearest: ProjectedPlacement | null = null;
    let nearestDistance = 14;
    for (const point of projected) {
      const distance = Math.hypot(point.px - localX, point.py - localY);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    }
    setSelected(nearest);
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
                  return (
                    <circle
                      cx={item.px}
                      cy={item.py}
                      fill={isSelected ? "#dc2626" : "#0284c7"}
                      key={item.source.instance_id}
                      onClick={() => setSelected(item)}
                      onMouseEnter={() => setHovered(item)}
                      onMouseLeave={() => setHovered(null)}
                      r={isSelected ? 6 : 4}
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
            </div>
          )}
        </div>
      </div>

      <aside className="rounded-xl border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Selection details</h3>
        {!selected && <p className="mt-2 text-sm text-slate">Click a part marker to inspect placement properties.</p>}
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
              <dt className="text-slate">Rotation</dt>
              <dd className="font-medium text-ink">{selected.source.rotation_deg.toFixed(1)} deg</dd>
            </div>
          </dl>
        )}
      </aside>
    </div>
  );
}
