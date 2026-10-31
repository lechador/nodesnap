"use client";
import { useRef, useState } from "react";
import type { BuildingSnapshot, Point, Units } from "./lib/types";
import { area, areaLabel, bounds, length } from "./lib/format";
import Icon from "./components/Icon";
import { planFrame } from "./lib/plan-frame";
import { doorSwing, roomLabelLines, stairPlan } from "./lib/plan-details";

type Props = {
  snap: BuildingSnapshot;
  level: string;
  selected: string;
  onSelect: (id: string) => void;
  onMove: (id: string, dx: number, dy: number) => void;
  units: Units;
  busy?: boolean;
};
type Frame = ReturnType<typeof planFrame>;
function Furniture({
  use,
  name,
  polygon,
  frame,
}: {
  use: string;
  name: string;
  polygon: Point[];
  frame: Frame;
}) {
  const { X, Y, H, scale: S } = frame;
  const b = bounds(polygon),
    x = X + (b.x + b.w / 2) * S,
    y = Y + (H - b.y - b.h / 2) * S;
  const common = { fill: "#f5f3ec", stroke: "#c7c9bf", strokeWidth: 1 };
  if (b.w < 2 || b.h < 2) return null;
  if (use.includes("bedroom"))
    return (
      <g
        transform={`translate(${x} ${y}) scale(${S / 35}) translate(-30 -42)`}
        {...common}
      >
        <rect width="60" height="72" rx="2" />
        <path d="M0 24h60M5 5h23v15H5Zm27 0h23v15H32Z" />
        <path d="M-15 0h11v16h-11Zm79 0h11v16H64Z" />
      </g>
    );
  if (
    use.includes("living") ||
    use.includes("lounge") ||
    use.includes("family")
  )
    return (
      <g
        transform={`translate(${x} ${y}) scale(${S / 35}) translate(-44 -36)`}
        {...common}
      >
        <rect width="88" height="31" rx="3" />
        <path d="M7 0v24h74V0M31 0v24m27-24v24" />
        <rect x="25" y="45" width="42" height="26" rx="10" />
        <rect x="-3" y="43" width="18" height="25" rx="3" />
      </g>
    );
  if (use.includes("dining"))
    return (
      <g
        transform={`translate(${x} ${y}) scale(${S / 35}) translate(-26 -42)`}
        {...common}
      >
        <rect width="52" height="84" rx="6" />
        {[8, 34, 60].map((n) => (
          <g key={n}>
            <rect x="-14" y={n} width="11" height="18" rx="2" />
            <rect x="55" y={n} width="11" height="18" rx="2" />
          </g>
        ))}
      </g>
    );
  if (use.includes("kitchen"))
    return (
      <g {...common}>
        <rect
          x={X + (b.x + 0.35) * S}
          y={Y + (H - b.y - b.h + 0.35) * S}
          width={(b.w - 0.7) * S}
          height={(22 * S) / 35}
        />
        <g transform={`translate(${x} ${y}) scale(${S / 35})`}>
          <rect x="-34" y="-18" width="68" height="36" rx="2" />
          <circle cx="-15" cy="0" r="7" />
          <circle cx="15" cy="0" r="7" />
        </g>
      </g>
    );
  if (
    /\b(wcs?|toilets?|restrooms?|washrooms?|lavator(?:y|ies))\b/.test(
      `${use} ${name}`.toLowerCase().replaceAll("_", " "),
    )
  )
    return (
      <g transform={`translate(${x} ${y}) scale(${S / 35})`} {...common}>
        <ellipse cx="0" cy="4" rx="7" ry="9" />
        <ellipse cx="0" cy="4" rx="4.5" ry="6.5" fill="none" />
        <rect x="-8" y="-11" width="16" height="8" rx="1" />
      </g>
    );
  if (use.includes("bath") || use.includes("changing"))
    return (
      <g
        transform={`translate(${x} ${y}) scale(${S / 35}) translate(-20 -25)`}
        {...common}
      >
        <rect width="40" height="65" rx="4" />
        <rect x="5" y="5" width="30" height="55" rx="12" />
      </g>
    );
  if (
    use.includes("study") ||
    use.includes("office") ||
    use.includes("library")
  )
    return (
      <g
        transform={`translate(${x} ${y}) scale(${S / 35}) translate(-36 -28)`}
        {...common}
      >
        <rect width="72" height="32" />
        <rect x="24" y="6" width="25" height="16" />
        <rect x="26" y="38" width="22" height="22" rx="5" />
      </g>
    );
  return null;
}
export default function Plan2D({
  snap,
  level,
  selected,
  onSelect,
  onMove,
  units,
  busy,
}: Props) {
  const [zoom, setZoom] = useState(1),
    [furnished, setFurnished] = useState(true),
    [dimensions, setDimensions] = useState(true);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; x: number; y: number } | null>(null);
  const [preview, setPreview] = useState<{
    id: string;
    dx: number;
    dy: number;
  } | null>(null);
  const lvl = snap.levels.find((l) => l.name === level) ?? snap.levels[0];
  const spaces = snap.spaces.filter((s) => s.level_id === lvl?.id),
    arch = snap.architecture;
  const walls = arch?.walls.filter((w) => w.level_id === lvl?.id) ?? [];
  const stairDrawing = stairPlan(arch?.stairs ?? [], lvl.id);
  const rings =
    arch?.slabs
      .filter((s) => s.level_id === lvl.id)
      .flatMap((s) => s.polygon) ?? [];
  if (!rings.length && !spaces.length)
    return (
      <div className="view-loading">This level has no drawing geometry.</div>
    );
  const frame = planFrame(
    rings.length ? rings : spaces.flatMap((s) => s.polygon),
  );
  const {
    scale: S,
    X,
    Y,
    H,
    left,
    top,
    width,
    depth,
    right,
    bottom,
    barMetres,
  } = frame;
  const pts = (p: Point[]) =>
    p.map(([x, y]) => `${X + x * S},${Y + (H - y) * S}`).join(" ");
  function endDrag(e: React.PointerEvent) {
    if (!drag.current) return;
    const d = preview;
    drag.current = null;
    setPreview(null);
    if (d && (d.dx || d.dy)) onMove(d.id, d.dx, d.dy);
    e.currentTarget.releasePointerCapture(e.pointerId);
  }
  return (
    <div className="plan-workspace">
      <div className="drawing-options">
        <button
          className={furnished ? "active" : ""}
          onClick={() => setFurnished(!furnished)}
        >
          <Icon name="grid" size={15} /> Furniture
        </button>
        <button
          className={dimensions ? "active" : ""}
          onClick={() => setDimensions(!dimensions)}
        >
          Dimensions
        </button>
        <span>Furniture is illustrative</span>
      </div>
      <div className="plan-scroll">
        <svg
          ref={svg}
          className="plan-sheet"
          viewBox="0 0 810 740"
          style={{
            width: `${zoom * 100}%`,
            height: `${zoom * 100}%`,
            minWidth: zoom > 1 ? `${zoom * 600}px` : undefined,
          }}
          role="group"
          aria-label={`${lvl?.label} architectural plan, revision ${snap.revision_number}`}
        >
          <defs>
            <pattern
              id="terrace-hatch"
              width="12"
              height="12"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M0 0h12v12"
                stroke="#e1e2d7"
                strokeWidth=".6"
                fill="none"
              />
            </pattern>
          </defs>
          <rect width="810" height="740" fill="#fcfcf8" />
          <g fontFamily="var(--font-geist-sans), sans-serif">
            <text x="40" y="30" fontSize="10" fill="#536158">
              NODESNAP / ARCHITECTURE
            </text>
            <text x="770" y="30" textAnchor="end" fontSize="10" fill="#536158">
              R{String(snap.revision_number).padStart(2, "0")} ·{" "}
              {snap.revision_id.slice(0, 8)}
            </text>
            {arch?.slabs
              .filter(
                (slab) =>
                  slab.level_id === lvl.id &&
                  Math.abs(
                    (slab.elevation_m ?? lvl.elevation_m) - lvl.elevation_m,
                  ) < 0.05,
              )
              .map((slab) => (
                <path
                  key={slab.id}
                  d={[slab.polygon, ...slab.holes]
                    .map((ring) => `M${pts(ring).replaceAll(" ", " L")} Z`)
                    .join(" ")}
                  fill="#eeeee6"
                  fillRule="evenodd"
                  stroke="#849085"
                  strokeWidth="1"
                />
              ))}
            {spaces.map((s) => {
              const m = arch?.space_metrics.find((m) => m.space_id === s.id);
              const b = bounds(m?.clear_polygon ?? s.polygon);
              const labels = roomLabelLines({
                name: s.name,
                key: `R${spaces.indexOf(s) + 1}`,
                area: areaLabel(m?.net_area_m2 ?? area(s.polygon), units),
                dimensions:
                  dimensions && s.classification === "principal"
                    ? `${length(m?.clear_width_m ?? b.w, units)} × ${length(m?.clear_depth_m ?? b.h, units)}`
                    : undefined,
                width: b.w * S,
                height: b.h * S,
              });
              return (
                <g
                  key={s.id}
                  transform={
                    preview?.id === s.id
                      ? `translate(${preview.dx * S} ${-preview.dy * S})`
                      : undefined
                  }
                >
                  <polygon
                    points={pts(s.polygon)}
                    fill={
                      s.id === selected
                        ? "#d8e7d9"
                        : s.use === "roof_terrace"
                          ? "url(#terrace-hatch)"
                          : s.classification === "principal"
                            ? "#f5f3ed"
                            : "#efefe7"
                    }
                    stroke={s.id === selected ? "#2f6e52" : "#dadbd0"}
                    strokeWidth={s.id === selected ? 1.5 : 0.5}
                    tabIndex={0}
                    role="button"
                    aria-label={`Select ${s.name}, ${areaLabel(m?.net_area_m2 ?? area(s.polygon), units)}`}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(s.id);
                      }
                    }}
                    onPointerDown={(e) => {
                      onSelect(s.id);
                      if (busy || selected !== s.id) return;
                      drag.current = { id: s.id, x: e.clientX, y: e.clientY };
                      e.currentTarget.setPointerCapture(e.pointerId);
                    }}
                    onPointerMove={(e) => {
                      if (!drag.current || !svg.current) return;
                      const matrix = svg.current.getScreenCTM();
                      if (!matrix) return;
                      const inverse = matrix.inverse();
                      const a = new DOMPoint(
                          drag.current.x,
                          drag.current.y,
                        ).matrixTransform(inverse),
                        b = new DOMPoint(e.clientX, e.clientY).matrixTransform(
                          inverse,
                        );
                      setPreview({
                        id: s.id,
                        dx: Math.round(((b.x - a.x) / S) * 10) / 10,
                        dy: -Math.round(((b.y - a.y) / S) * 10) / 10,
                      });
                    }}
                    onPointerUp={endDrag}
                    onPointerCancel={() => {
                      drag.current = null;
                      setPreview(null);
                    }}
                    className="room-hit"
                  />
                  <g pointerEvents="none">
                    <defs>
                      <clipPath id={`furnish-${s.id}`}>
                        <polygon points={pts(m?.clear_polygon ?? s.polygon)} />
                      </clipPath>
                    </defs>
                    {furnished && (
                      <g clipPath={`url(#furnish-${s.id})`}>
                        <Furniture
                          use={s.use}
                          name={s.name}
                          polygon={m?.clear_polygon ?? s.polygon}
                          frame={frame}
                        />
                      </g>
                    )}
                    <g clipPath={`url(#furnish-${s.id})`}>
                      {labels.map((line) => (
                        <text
                          key={line.kind}
                          x={X + (b.x + b.w / 2) * S}
                          y={Y + (H - b.y - b.h) * S + line.y}
                          textAnchor="middle"
                          fontSize={line.size}
                          fill={line.kind === "name" ? "#28372e" : "#536158"}
                          fontWeight={line.kind === "name" ? "600" : "400"}
                        >
                          {line.text}
                        </text>
                      ))}
                    </g>
                  </g>
                </g>
              );
            })}
            <g pointerEvents="none">
              {walls.map((w) => (
                <line
                  key={w.id}
                  x1={X + w.start[0] * S}
                  y1={Y + (H - w.start[1]) * S}
                  x2={X + w.end[0] * S}
                  y2={Y + (H - w.end[1]) * S}
                  stroke="#414c42"
                  strokeWidth={w.thickness_m * S}
                  strokeLinecap="butt"
                />
              ))}
              {arch?.openings.map((o) => {
                const w = walls.find((w) => w.id === o.wall_id);
                if (!w) return null;
                const dx = w.end[0] - w.start[0],
                  dy = w.end[1] - w.start[1],
                  l = Math.hypot(dx, dy),
                  angle = (-Math.atan2(dy, dx) * 180) / Math.PI,
                  x = X + (w.start[0] + (dx / l) * o.offset_m) * S,
                  y = Y + (H - w.start[1] - (dy / l) * o.offset_m) * S,
                  v = o.width_m * S;
                const swing =
                  o.kind === "door" ? doorSwing(w, o, spaces) : null;
                return (
                  <g
                    key={o.id}
                    transform={`translate(${x} ${y}) rotate(${angle})`}
                  >
                    <rect
                      x="0"
                      y={(-w.thickness_m * S) / 2 - 0.5}
                      width={v}
                      height={w.thickness_m * S + 1}
                      fill="#fcfcf8"
                    />
                    {o.kind === "window" ? (
                      <g stroke="#8b9e95" strokeWidth=".8">
                        <path d={`M0 -2H${v}M0 2H${v}M0 -5v10M${v} -5v10`} />
                      </g>
                    ) : o.kind === "door" ? (
                      <g stroke="#687668" strokeWidth=".8" fill="none">
                        <path
                          d={`M${swing!.hingeX * S} 0V${swing!.leafY * S}M${swing!.hingeX * S} ${swing!.leafY * S}A${v} ${v} 0 0 ${swing!.sweep} ${swing!.closedX * S} 0`}
                        />
                      </g>
                    ) : null}
                  </g>
                );
              })}
              {(stairDrawing ? [stairDrawing] : []).map(
                ({ stair: s, direction }) => {
                  const b = bounds(s.polygon),
                    half = Math.floor(s.riser_count / 2),
                    north = s.orientation === "north",
                    py = (y: number) =>
                      Y + (H - (north ? 2 * b.y + b.h - y : y)) * S,
                    px = (x: number) => X + x * S,
                    arrow = north ? -5 : 5;
                  return (
                    <g
                      key={s.id}
                      stroke="#879081"
                      strokeWidth=".65"
                      fill="none"
                    >
                      <rect
                        x={px(b.x)}
                        y={Y + (H - b.y - b.h) * S}
                        width={b.w * S}
                        height={b.h * S}
                      />
                      <path
                        d={`M${px(b.x)} ${py(b.y + s.landing_depth_m)}h${b.w * S}`}
                      />
                      {Array.from({ length: half }, (_, i) => (
                        <line
                          key={`a${i}`}
                          x1={px(b.x)}
                          x2={px(b.x + s.width_m)}
                          y1={py(b.y + b.h - i * s.tread_depth_m)}
                          y2={py(b.y + b.h - i * s.tread_depth_m)}
                        />
                      ))}
                      {Array.from({ length: s.riser_count - half }, (_, i) => (
                        <line
                          key={`b${i}`}
                          x1={px(b.x + b.w - s.width_m)}
                          x2={px(b.x + b.w)}
                          y1={py(b.y + s.landing_depth_m + i * s.tread_depth_m)}
                          y2={py(b.y + s.landing_depth_m + i * s.tread_depth_m)}
                        />
                      ))}
                      <path
                        d={`M${px(b.x + s.width_m / 2)} ${py(b.y + b.h - 0.3)}V${py(b.y + s.landing_depth_m / 2)}H${px(b.x + b.w - s.width_m / 2)}V${py(b.y + b.h - 0.3)}m-3 ${arrow} 3 ${-arrow} 3 ${arrow}`}
                      />
                      <text
                        x={px(b.x + b.w / 2)}
                        y={py(b.y + b.h - 0.5)}
                        textAnchor="middle"
                        stroke="none"
                        fill="#536158"
                        fontSize={Math.min(
                          7,
                          (b.w * S - 4) / (direction.length * 0.8),
                        )}
                      >
                        {direction}
                      </text>
                    </g>
                  );
                },
              )}
              {snap.pool && snap.pool.level_id === lvl.id && (
                <g>
                  <rect
                    x={X + snap.pool.origin_x_m * S}
                    y={
                      Y +
                      (H - snap.pool.origin_y_m - snap.pool.water_width_m) * S
                    }
                    width={snap.pool.water_length_m * S}
                    height={snap.pool.water_width_m * S}
                    fill="#d6e9e5"
                    stroke="#729b97"
                    strokeWidth="2"
                  />
                  <text
                    x={
                      X +
                      (snap.pool.origin_x_m + snap.pool.water_length_m / 2) * S
                    }
                    y={
                      Y +
                      (H - snap.pool.origin_y_m - snap.pool.water_width_m / 2) *
                        S
                    }
                    textAnchor="middle"
                    fontSize="10"
                    fill="#315e5a"
                  >
                    POOL · {length(snap.pool.water_length_m, units)} ×{" "}
                    {length(snap.pool.water_width_m, units)}
                  </text>
                </g>
              )}
              {dimensions && (
                <g fill="#59665c" stroke="#849084" strokeWidth=".6">
                  <path
                    d={`M${left} ${top - 24}H${right}M${left} ${top - 30}v18M${right} ${top - 30}v18M${right + 26} ${top}V${bottom}m-6 0h12M${right + 20} ${top}h12`}
                  />
                  <text
                    x={(left + right) / 2}
                    y={top - 30}
                    textAnchor="middle"
                    stroke="none"
                    fontSize="10"
                  >
                    {length(width, units)} · outside envelope
                  </text>
                  <text
                    transform={`translate(${right + 40} ${(top + bottom) / 2}) rotate(90)`}
                    textAnchor="middle"
                    stroke="none"
                    fontSize="10"
                  >
                    {length(depth, units)}
                  </text>
                </g>
              )}
            </g>
            <path
              d="M43 100V65l-6 12m6-12 6 12"
              fill="none"
              stroke="#354537"
              strokeWidth="1"
            />
            <text x="43" y="57" textAnchor="middle" fontSize="10">
              N
            </text>
            <path
              d={`M85 650h${barMetres * S}M85 645v10m${(barMetres * S) / 2}-10v10m${(barMetres * S) / 2}-10v10`}
              stroke="#354537"
              fill="none"
            />
            <text x="85" y="670" fontSize="9">
              0
            </text>
            <text
              x={85 + (barMetres * S) / 2}
              y="670"
              fontSize="9"
              textAnchor="middle"
            >
              {length(barMetres / 2, units)}
            </text>
            <text
              x={85 + barMetres * S}
              y="670"
              fontSize="9"
              textAnchor="middle"
            >
              {length(barMetres, units)}
            </text>
            <text
              x="770"
              y="655"
              textAnchor="end"
              fontSize="21"
              fontWeight="500"
            >
              {lvl?.label}
            </text>
            <text x="770" y="676" textAnchor="end" fontSize="9" fill="#536158">
              A-{101 + snap.levels.findIndex((l) => l.id === lvl?.id)} ·
              Diagrammatic furnishings · Do not scale screen
            </text>
            <path d="M40 690h730" stroke="#d2d7cc" />
            <text x="40" y="711" fontSize="9" fill="#536158">
              DEMONSTRATION DESIGN · Assumed assemblies · Professional
              verification required
            </text>
          </g>
        </svg>
      </div>
      <div className="drawing-zoom">
        <button
          title="Zoom out"
          aria-label="Zoom out"
          onClick={() => setZoom((z) => Math.max(0.7, z - 0.2))}
        >
          <Icon name="minus" />
        </button>
        <span>{Math.round(zoom * 100)}%</span>
        <button
          title="Zoom in"
          aria-label="Zoom in"
          onClick={() => setZoom((z) => Math.min(2.2, z + 0.2))}
        >
          <Icon name="plus" />
        </button>
        <button
          title="Fit plan"
          aria-label="Fit plan"
          onClick={() => setZoom(1)}
        >
          <Icon name="fit" />
        </button>
      </div>
    </div>
  );
}
