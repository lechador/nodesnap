"use client";
import { useState, type KeyboardEvent } from "react";
import type { BuildingSnapshot, Units } from "./lib/types";
import { area, areaLabel, length } from "./lib/format";
import { planFrame } from "./lib/plan-frame";
import {
  garageWallFootprints,
  rectangleBounds,
  waterPolygon,
} from "./site-model";
import { PROJECT_BOUNDARY_ID, projectBoundaryPolygon } from "./site-selection";
import Icon from "./components/Icon";

export default function SitePlan({
  snap,
  units,
  selected,
  onSelect,
}: {
  snap: BuildingSnapshot;
  units: Units;
  selected?: string;
  onSelect?: (id: string) => void;
}) {
  const [zoom, setZoom] = useState(1),
    [dimensions, setDimensions] = useState(true);
  const site = snap.site_layout;
  const ground = snap.levels.find((l) => l.name === "ground");
  const footprint =
    snap.envelope_polygon ??
    snap.architecture?.slabs.find((s) => s.level_id === ground?.id)?.polygon ??
    [];
  const boundary = projectBoundaryPolygon(snap);
  const frame = planFrame([...boundary, ...footprint]);
  const { X, Y, H, scale: S, barMetres } = frame;
  const px = (x: number) => X + x * S,
    py = (y: number) => Y + (H - y) * S;
  const ringPath = (ring: number[][]) =>
    `M${ring.map((p) => `${px(p[0])},${py(p[1])}`).join("L")}Z`;
  const surfacePath = (surface: { polygon: number[][]; holes: number[][][] }) =>
    [surface.polygon, ...surface.holes].map(ringPath).join(" ");
  const selectionProps = (id: string, name: string) => ({
    className: `site-plan-feature${selected === id ? " is-selected" : ""}`,
    role: onSelect ? ("button" as const) : undefined,
    tabIndex: onSelect ? 0 : undefined,
    "aria-label": onSelect ? `${name}. View materials and details` : undefined,
    "aria-pressed": onSelect ? selected === id : undefined,
    onClick: onSelect ? () => onSelect(id) : undefined,
    onKeyDown: onSelect
      ? (event: KeyboardEvent<SVGGElement>) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            onSelect(id);
          }
        }
      : undefined,
  });
  const selectionOutline = (id: string, d: string) => (
    <path
      className="site-plan-outline"
      d={d}
      fill="none"
      stroke="#315d42"
      strokeWidth="3"
      strokeLinejoin="round"
      vectorEffect="non-scaling-stroke"
      opacity={selected === id ? 1 : 0}
      pointerEvents="none"
      aria-hidden="true"
    />
  );
  const label = (
    polygon: number[][],
    name: string,
    detail?: string | string[],
  ) => {
    const b = rectangleBounds(polygon),
      lines = [
        name,
        ...(Array.isArray(detail) ? detail : detail ? [detail] : []),
      ];
    const font = Math.min(
      11,
      Math.max(
        7.5,
        (b.width * S - 12) / (Math.max(...lines.map((l) => l.length)) * 0.54),
      ),
    );
    return (
      <text
        x={px(b.x + b.width / 2)}
        y={py(b.y + b.depth / 2) - (lines.length > 1 ? 6 : 0)}
        textAnchor="middle"
        fill="#32493c"
        fontSize={font}
        pointerEvents="none"
      >
        {lines.map((line, i) => (
          <tspan
            x={px(b.x + b.width / 2)}
            dy={i ? font * 1.5 : 0}
            key={line}
            fontWeight={i ? 400 : 500}
          >
            {line}
          </tspan>
        ))}
      </text>
    );
  };
  const dimension = (
    polygon: number[][],
    placement: "above" | "below" = "above",
    side: "left" | "right" = "right",
  ) => {
    const b = rectangleBounds(polygon),
      x1 = px(b.x),
      x2 = px(b.x + b.width),
      y1 = py(b.y + b.depth),
      y2 = py(b.y);
    const y = placement === "above" ? y1 - 14 : y2 + 14;
    const dimensionX = side === "left" ? x1 - 14 : x2 + 14;
    const textX = side === "left" ? x1 - 23 : x2 + 23;
    return (
      <g fill="#536158" stroke="#7b887d" strokeWidth=".65" pointerEvents="none">
        <path
          d={`M${x1} ${y}H${x2}M${x1} ${y - 4}v8M${x2} ${y - 4}v8M${dimensionX} ${y1}V${y2}M${dimensionX - 4} ${y1}h8M${dimensionX - 4} ${y2}h8`}
        />
        <text
          x={(x1 + x2) / 2}
          y={y - 4}
          stroke="none"
          textAnchor="middle"
          fontSize="9"
          paintOrder="stroke"
          style={{ stroke: "#fcfcf8", strokeWidth: 3 }}
        >
          {length(b.width, units)}
        </text>
        <text
          transform={`translate(${textX} ${(y1 + y2) / 2}) rotate(90)`}
          stroke="none"
          textAnchor="middle"
          fontSize="9"
          paintOrder="stroke"
          style={{ stroke: "#fcfcf8", strokeWidth: 3 }}
        >
          {length(b.depth, units)}
        </text>
      </g>
    );
  };
  const garage = site?.garage,
    pool = snap.pool?.location === "outdoor" ? snap.pool : null;
  const poolId = pool?.id ?? "site-pool";
  const yardArea = site?.yard
    ? area(site.yard.polygon) -
      site.yard.holes.reduce((sum, ring) => sum + area(ring), 0)
    : 0;
  return (
    <div className="plan-workspace">
      <div className="drawing-options">
        <button
          className={dimensions ? "active" : ""}
          aria-pressed={dimensions}
          onClick={() => setDimensions(!dimensions)}
        >
          Dimensions
        </button>
        <span>
          {onSelect
            ? "Select a site feature to see materials and details"
            : "Assumed project boundary · not a surveyed parcel"}
        </span>
      </div>
      <div className="plan-scroll">
        <svg
          className="plan-sheet"
          viewBox="0 0 810 740"
          style={{
            width: `${zoom * 100}%`,
            height: `${zoom * 100}%`,
            minWidth: zoom > 1 ? `${zoom * 600}px` : undefined,
          }}
          role="group"
          aria-label={`Site plan with assumed project boundary, house, ${[site?.yard ? "yard" : null, garage ? "garage" : null, pool ? "outdoor pool" : null].filter(Boolean).join(", ") || "no added site features"}; revision ${snap.revision_number}`}
        >
          <rect width="810" height="740" fill="#fcfcf8" />
          <g fontFamily="var(--font-geist-sans),sans-serif">
            <text x="40" y="30" fontSize="10" fill="#536158">
              NODESNAP / SITE DESIGN
            </text>
            <text x="770" y="30" textAnchor="end" fontSize="10" fill="#536158">
              R{String(snap.revision_number).padStart(2, "0")} ·{" "}
              {snap.revision_id.slice(0, 8)}
            </text>
            {boundary.length >= 3 && (
              <g
                {...selectionProps(
                  PROJECT_BOUNDARY_ID,
                  "Project boundary, assumed study extent",
                )}
              >
                <path
                  d={ringPath(boundary)}
                  fill="none"
                  stroke="#627c64"
                  strokeWidth="1.6"
                  strokeDasharray="9 5"
                  vectorEffect="non-scaling-stroke"
                />
                <path
                  d={ringPath(boundary)}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="18"
                  pointerEvents="stroke"
                  aria-hidden="true"
                />
                {selectionOutline(PROJECT_BOUNDARY_ID, ringPath(boundary))}
                <text
                  className="site-plan-boundary-label"
                  x={(frame.left + frame.right) / 2}
                  y={frame.top + 17}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="500"
                  fill="#3d5b44"
                  paintOrder="stroke"
                  stroke="#fcfcf8"
                  strokeWidth="5"
                  strokeLinejoin="round"
                >
                  Project boundary · Assumed
                </text>
              </g>
            )}
            {site?.yard && (
              <g {...selectionProps(site.yard.id, site.yard.name || "Yard")}>
                <path
                  d={surfacePath(site.yard)}
                  fill="#e2ead8"
                  fillRule="evenodd"
                  stroke="#8b9e7a"
                  strokeWidth="1"
                />
                {selectionOutline(site.yard.id, surfacePath(site.yard))}
              </g>
            )}
            {site?.driveway && (
              <g
                {...selectionProps(
                  site.driveway.id,
                  site.driveway.name || "Driveway",
                )}
              >
                <path
                  d={surfacePath(site.driveway)}
                  fill="#e5e3da"
                  fillRule="evenodd"
                  stroke="#abae9f"
                  strokeWidth=".8"
                />
                {selectionOutline(site.driveway.id, surfacePath(site.driveway))}
              </g>
            )}
            {site?.pool_deck && (
              <g
                {...selectionProps(
                  site.pool_deck.id,
                  site.pool_deck.name || "Pool deck",
                )}
              >
                <path
                  d={surfacePath(site.pool_deck)}
                  fill="#f0e9d9"
                  fillRule="evenodd"
                  stroke="#bbb29d"
                  strokeWidth=".8"
                />
                {selectionOutline(
                  site.pool_deck.id,
                  surfacePath(site.pool_deck),
                )}
              </g>
            )}
            <path
              d={ringPath(footprint)}
              fill="#f5f5ee"
              stroke="#394a40"
              strokeWidth="2"
            />
            {label(
              footprint,
              "HOUSE",
              `${areaLabel(area(footprint), units)} footprint`,
            )}
            {dimensions &&
              dimension(
                footprint,
                "below",
                garage?.side === "left" ? "right" : "left",
              )}
            {garage && (
              <g {...selectionProps(garage.id, garage.name || "Garage")}>
                <path
                  d={ringPath(garage.polygon)}
                  fill="#edece4"
                  stroke="#647365"
                  strokeWidth=".8"
                />
                {garageWallFootprints(garage).map((wall, i) => (
                  <rect
                    key={i}
                    x={px(wall.x)}
                    y={py(wall.y + wall.depth)}
                    width={wall.width * S}
                    height={wall.depth * S}
                    fill="#647365"
                  />
                ))}
                <path
                  d={`M${px(garage.vehicle_door_start[0])} ${py(garage.vehicle_door_start[1])}L${px(garage.vehicle_door_end[0])} ${py(garage.vehicle_door_end[1])}`}
                  stroke="#344a3d"
                  strokeWidth="2"
                />
                {label(garage.polygon, "GARAGE", [
                  areaLabel(area(garage.polygon), units),
                  "Detached",
                ])}
                {selectionOutline(garage.id, ringPath(garage.polygon))}
                {dimensions && dimension(garage.polygon)}
              </g>
            )}
            {site?.driveway && label(site.driveway.polygon, "DRIVEWAY")}
            {pool && (
              <g {...selectionProps(poolId, "Outdoor pool")}>
                <path
                  d={ringPath(waterPolygon(pool))}
                  fill="#c8e3dd"
                  stroke="#5a9690"
                  strokeWidth="1.3"
                />
                {label(
                  waterPolygon(pool),
                  "OUTDOOR POOL",
                  `${length(pool.water_length_m, units)} × ${length(pool.water_width_m, units)}`,
                )}
                {selectionOutline(poolId, ringPath(waterPolygon(pool)))}
              </g>
            )}
            {site?.yard &&
              (() => {
                const b = rectangleBounds(site.yard.polygon);
                return (
                  <g>
                    <text
                      x={px(b.x + b.width / 2)}
                      y={py(b.y + b.depth) + 13}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#496440"
                      pointerEvents="none"
                    >
                      YARD · {areaLabel(yardArea, units)} net landscape
                    </text>
                    {dimensions && dimension(site.yard.polygon)}
                  </g>
                );
              })()}
            <path d="M43 100V65l-6 12m6-12 6 12" fill="none" stroke="#354537" />
            <text x="43" y="57" textAnchor="middle" fontSize="10">
              N*
            </text>
            <text x="40" y="625" fontSize="8.5" fill="#687566">
              * Assumed orientation and project boundary. No surveyed property
              boundary is supplied.
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
              x={85 + barMetres * S}
              y="670"
              fontSize="9"
              textAnchor="middle"
            >
              {length(barMetres, units)}
            </text>
            <text x="770" y="655" fontSize="21" textAnchor="end">
              Site plan
            </text>
            <text x="770" y="676" fontSize="9" textAnchor="end" fill="#536158">
              C-101 · Dimensions from saved geometry · Do not scale screen
            </text>
            <path d="M40 690h730" stroke="#d2d7cc" />
            <text x="40" y="711" fontSize="9" fill="#536158">
              CONCEPT DESIGN · Site fit, vehicle access and pool safety require
              professional review
            </text>
          </g>
        </svg>
      </div>
      <div className="drawing-zoom">
        <button
          aria-label="Zoom out site plan"
          disabled={zoom <= 1}
          onClick={() => setZoom(Math.max(1, zoom - 0.25))}
        >
          <Icon name="minus" size={15} />
        </button>
        <span>{Math.round(zoom * 100)}%</span>
        <button
          aria-label="Zoom in site plan"
          disabled={zoom >= 3}
          onClick={() => setZoom(Math.min(3, zoom + 0.25))}
        >
          <Icon name="plus" size={15} />
        </button>
        <button aria-label="Fit site plan" onClick={() => setZoom(1)}>
          <Icon name="fit" size={15} />
        </button>
      </div>
    </div>
  );
}
