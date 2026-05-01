import { useEffect, useRef, useState } from "react";
import type { MouseEvent, WheelEvent } from "react";
import type { ViewerPlacement } from "../lib/types";

interface ViewerCanvasProps {
  sheetIndex: number;
  svgUrl: string | null;
  placements: ViewerPlacement[];
  sheetWidthMm?: number;
  sheetHeightMm?: number;
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
  corners: Point[];
  center: Point;
}

function rotatePoint(point: Point, origin: Point, angleDeg: number): Point {
  const rad = (angleDeg * Math.PI) / 180;
  const c = Math.cos(rad);
  const s = Math.sin(rad);
  const dx = point.x - origin.x;
  const dy = point.y - origin.y;
  return { x: origin.x + dx * c - dy * s, y: origin.y + dx * s + dy * c };
}

function placementToGeometry(item: ViewerPlacement): PlacementGeometry {
  const w = item.width_mm > 0 ? item.width_mm : 10;
  const h = item.height_mm > 0 ? item.height_mm : 10;
  const origin: Point = { x: item.x, y: item.y };
  const rect: Point[] = [
    { x: item.x, y: item.y },
    { x: item.x + w, y: item.y },
    { x: item.x + w, y: item.y + h },
    { x: item.x, y: item.y + h },
  ];
  return { source: item, corners: rect.map((p) => rotatePoint(p, origin, item.rotation_deg)) };
}

function polygonCenter(corners: Point[]): Point {
  let sx = 0;
  let sy = 0;
  for (const p of corners) {
    sx += p.x;
    sy += p.y;
  }
  return { x: sx / corners.length, y: sy / corners.length };
}

function pointInPolygon(pt: Point, poly: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i, i += 1) {
    const xi = poly[i].x, yi = poly[i].y;
    const xj = poly[j].x, yj = poly[j].y;
    if (yi > pt.y !== yj > pt.y && pt.x < ((xj - xi) * (pt.y - yi)) / ((yj - yi) || 1e-9) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

export function ViewerCanvas({ sheetIndex, svgUrl, placements, sheetWidthMm, sheetHeightMm, onSvgError }: ViewerCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragOrigin, setDragOrigin] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [hovered, setHovered] = useState<ProjectedPlacement | null>(null);
  const [selected, setSelected] = useState<ProjectedPlacement | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const mmW = sheetWidthMm && sheetWidthMm > 0 ? sheetWidthMm : 0;
  const mmH = sheetHeightMm && sheetHeightMm > 0 ? sheetHeightMm : 0;
  const hasSheetDims = mmW > 0 && mmH > 0;
  const hasSvgArtifact = Boolean(svgUrl);

  const renderMode: "svg" | "canvas" = hasSvgArtifact || placements.length <= 300 ? "svg" : "canvas";

  const geometries: PlacementGeometry[] = placements.map(placementToGeometry);
  const projected: ProjectedPlacement[] = geometries.map((g) => ({
    source: g.source,
    corners: g.corners,
    center: polygonCenter(g.corners),
  }));

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setHovered(null);
    setSelected(null);
    setDragging(false);
    setDragOrigin(null);
  }, [sheetIndex, svgUrl]);

  // Fallback canvas mode: draw using mm-to-px scaled coordinates when no sheet SVG artifact exists.
  useEffect(() => {
    if (renderMode !== "canvas") return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cW = canvas.width;
    const cH = canvas.height;
    const scaleX = mmW > 0 ? cW / mmW : 1;
    const scaleY = mmH > 0 ? cH / mmH : 1;

    ctx.clearRect(0, 0, cW, cH);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, cW, cH);
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(0.5, 0.5, cW - 1, cH - 1);

    for (const item of projected) {
      const isSel = selected?.source.instance_id === item.source.instance_id;
      ctx.beginPath();
      for (let i = 0; i < item.corners.length; i += 1) {
        const px = item.corners[i].x * scaleX;
        const py = item.corners[i].y * scaleY;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = isSel ? "rgba(220,38,38,0.35)" : "rgba(2,132,199,0.32)";
      ctx.strokeStyle = isSel ? "#dc2626" : "#0f172a";
      ctx.lineWidth = isSel ? 2 : 1;
      ctx.fill();
      ctx.stroke();
    }
  }, [projected, renderMode, selected, mmW, mmH]);

  function fitToScreen() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const delta = event.deltaY > 0 ? -0.1 : 0.1;
    setZoom((prev) => Math.min(8, Math.max(0.3, Number((prev + delta).toFixed(2)))));
  }

  function handleMouseDown(event: MouseEvent<HTMLDivElement>) {
    setDragging(true);
    setDragOrigin({ x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y });
  }

  function handleMouseUp() {
    setDragging(false);
    setDragOrigin(null);
  }

  // Convert screen coords to mm coordinates (the SVG viewBox coordinate space)
  function screenToMm(event: MouseEvent<HTMLDivElement>): Point {
    const rect = event.currentTarget.getBoundingClientRect();
    const cW = rect.width;
    const cH = rect.height;
    const pxPerMmX = mmW > 0 ? cW / mmW : 1;
    const pxPerMmY = mmH > 0 ? cH / mmH : 1;
    return {
      x: (event.clientX - rect.left - cW / 2 - pan.x) / zoom / pxPerMmX + mmW / 2,
      y: (event.clientY - rect.top - cH / 2 - pan.y) / zoom / pxPerMmY + mmH / 2,
    };
  }

  function pickAt(pt: Point): ProjectedPlacement | null {
    for (let i = projected.length - 1; i >= 0; i -= 1) {
      if (pointInPolygon(pt, projected[i].corners)) return projected[i];
    }
    return null;
  }

  function handleMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (dragging && dragOrigin) {
      setPan({ x: dragOrigin.panX + event.clientX - dragOrigin.x, y: dragOrigin.panY + event.clientY - dragOrigin.y });
      return;
    }
    if (!hasSheetDims || hasSvgArtifact) return;
    setHovered(pickAt(screenToMm(event)));
  }

  function handleClick(event: MouseEvent<HTMLDivElement>) {
    if (!hasSheetDims || hasSvgArtifact) return;
    setSelected(pickAt(screenToMm(event)));
  }

  const containerStyle: React.CSSProperties = hasSvgArtifact
    ? { width: "100%", height: "min(70vh, 720px)", minHeight: "360px" }
    : hasSheetDims
    ? { width: `min(100%, ${650 * (mmW / mmH)}px)`, aspectRatio: `${mmW} / ${mmH}` }
    : { width: "100%", height: "480px" };

  // Canvas pixel size for canvas mode: measure container (approximate with max)
  const MAX_CANVAS_PX = 960;
  const canvasPxW = hasSheetDims ? Math.round(Math.min(MAX_CANVAS_PX, 650 * (mmW / mmH))) : MAX_CANVAS_PX;
  const canvasPxH = hasSheetDims ? Math.round(canvasPxW * (mmH / mmW)) : 480;

  const svgViewBox = hasSheetDims ? `0 0 ${mmW} ${mmH}` : "0 0 100 100";

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
      <div>
        <div className="mb-2 flex items-center justify-between text-sm text-slate">
          <div className="flex items-center gap-2">
            <span>Sheet #{sheetIndex + 1}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">mode: {renderMode}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">parts: {placements.length}</span>
            {hasSheetDims && (
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                {mmW.toFixed(0)}×{mmH.toFixed(0)} mm
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={() => setZoom((z) => Math.min(8, z + 0.25))} type="button">+</button>
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={() => setZoom((z) => Math.max(0.3, z - 0.25))} type="button">−</button>
            <button className="rounded border border-mist px-2 py-1 hover:bg-slate-100" onClick={fitToScreen} type="button">Fit</button>
          </div>
        </div>

        {/* Outer container */}
        <div
          className="relative overflow-hidden rounded-xl border border-mist bg-slate-200"
          onClick={handleClick}
          onMouseDown={handleMouseDown}
          onMouseLeave={handleMouseUp}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          ref={containerRef}
          role="presentation"
          style={containerStyle}
        >
          {/* Pan/zoom wrapper — centered, transforms applied here */}
          <div
            className="absolute left-1/2 top-1/2 h-full w-full"
            style={{
              transform: `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${zoom})`,
              transformOrigin: "center center",
            }}
          >
            {/* Primary visual truth: final sheet SVG artifact */}
            {svgUrl ? (
              <img
                alt={`Sheet ${sheetIndex + 1}`}
                className="absolute inset-0 h-full w-full object-contain"
                draggable={false}
                onError={onSvgError}
                src={svgUrl}
              />
            ) : (
              <div className="absolute inset-0 border border-slate-400 bg-slate-50" />
            )}

            {/* Fallback overlay: only used when the final sheet SVG artifact is absent. */}
            {!hasSvgArtifact && renderMode === "canvas" ? (
              <canvas
                className="absolute inset-0 h-full w-full"
                height={canvasPxH}
                ref={canvasRef}
                width={canvasPxW}
              />
            ) : !hasSvgArtifact ? (
              <svg
                className="absolute inset-0 h-full w-full"
                preserveAspectRatio="none"
                viewBox={svgViewBox}
              >
                {!svgUrl && hasSheetDims && (
                  <rect fill="none" height={mmH} stroke="#0f172a" strokeWidth={mmW * 0.002} width={mmW} x={0} y={0} />
                )}
                {projected.map((item) => {
                  const isSel = selected?.source.instance_id === item.source.instance_id;
                  const isHov = hovered?.source.instance_id === item.source.instance_id;
                  const pts = item.corners.map((p) => `${p.x},${p.y}`).join(" ");
                  const polyFill = isSel
                    ? "rgba(220,38,38,0.36)"
                    : isHov
                    ? "rgba(2,132,199,0.22)"
                    : "rgba(2,132,199,0.28)";
                  const polyStroke = isSel
                    ? "#dc2626"
                    : isHov
                    ? "#0284c7"
                    : "#1e293b";
                  return (
                    <polygon
                      fill={polyFill}
                      key={item.source.instance_id}
                      onClick={() => setSelected(item)}
                      onMouseEnter={() => setHovered(item)}
                      onMouseLeave={() => setHovered(null)}
                      points={pts}
                      pointerEvents="all"
                      stroke={polyStroke}
                      strokeWidth={mmW > 0 ? mmW * 0.002 : 1}
                    />
                  );
                })}
              </svg>
            ) : null}
          </div>

          {/* Hover tooltip — stays in screen space (outside the transform wrapper) */}
          {hovered && (
            <div className="pointer-events-none absolute right-3 top-3 rounded-md border border-mist bg-white/95 px-3 py-2 text-xs shadow-sm">
              <p><strong>{hovered.source.part_id}</strong></p>
              <p>Instance: {hovered.source.instance_id}</p>
              <p>X/Y: {hovered.source.x.toFixed(1)} / {hovered.source.y.toFixed(1)} mm</p>
              <p>W/H: {hovered.source.width_mm.toFixed(1)} / {hovered.source.height_mm.toFixed(1)} mm</p>
              <p>Rot: {hovered.source.rotation_deg.toFixed(0)}°</p>
            </div>
          )}
        </div>
      </div>

      <aside className="rounded-xl border border-mist bg-white p-4">
        <h3 className="text-sm font-semibold text-ink">Selection details</h3>
        {!selected && <p className="mt-2 text-sm text-slate">Click a part to inspect placement properties.</p>}
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
              <dt className="text-slate">Position (mm)</dt>
              <dd className="font-medium text-ink">{selected.source.x.toFixed(2)} / {selected.source.y.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-slate">Size (mm)</dt>
              <dd className="font-medium text-ink">{selected.source.width_mm.toFixed(2)} × {selected.source.height_mm.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-slate">Rotation</dt>
              <dd className="font-medium text-ink">{selected.source.rotation_deg.toFixed(1)}°</dd>
            </div>
          </dl>
        )}
      </aside>
    </div>
  );
}
