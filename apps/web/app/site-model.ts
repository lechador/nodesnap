/** Render adapter for saved site geometry; local XY metres map to XZ/Y-up. */
import type { BoxPart } from "./scene-model";

export interface SiteSurface {
  id: string;
  name: string;
  polygon: number[][];
  holes: number[][][];
  elevation_m: number;
  material: string;
}
export interface GarageGeometry {
  id: string;
  name: string;
  polygon: number[][];
  elevation_m: number;
  height_m: number;
  wall_thickness_m: number;
  slab_thickness_m: number;
  roof_thickness_m: number;
  vehicle_door_width_m: number;
  vehicle_door_height_m: number;
  vehicle_door_start: number[];
  vehicle_door_end: number[];
  side?: "left" | "right";
}
export interface SiteGeometry {
  revision_id: string;
  context_polygon: number[][];
  yard: SiteSurface | null;
  garage: GarageGeometry | null;
  driveway: SiteSurface | null;
  pool_deck: SiteSurface | null;
}
export function rectangleBounds(polygon: number[][]) {
  const xs = polygon.map((p) => p[0]),
    ys = polygon.map((p) => p[1]);
  const x = Math.min(...xs),
    y = Math.min(...ys);
  return { x, y, width: Math.max(...xs) - x, depth: Math.max(...ys) - y };
}
export function waterPolygon(pool: {
  origin_x_m: number;
  origin_y_m: number;
  water_length_m: number;
  water_width_m: number;
}) {
  const x = pool.origin_x_m,
    y = pool.origin_y_m;
  return [
    [x, y],
    [x + pool.water_length_m, y],
    [x + pool.water_length_m, y + pool.water_width_m],
    [x, y + pool.water_width_m],
    [x, y],
  ];
}
export function garageWallFootprints(garage: GarageGeometry) {
  const b = rectangleBounds(garage.polygon),
    t = garage.wall_thickness_m;
  const doorLeft = Math.min(
    garage.vehicle_door_start[0],
    garage.vehicle_door_end[0],
  );
  const doorRight = Math.max(
    garage.vehicle_door_start[0],
    garage.vehicle_door_end[0],
  );
  return [
    { x: b.x, y: b.y, width: t, depth: b.depth },
    { x: b.x + b.width - t, y: b.y, width: t, depth: b.depth },
    { x: b.x + t, y: b.y + b.depth - t, width: b.width - 2 * t, depth: t },
    { x: b.x + t, y: b.y, width: doorLeft - b.x - t, depth: t },
    { x: doorRight, y: b.y, width: b.x + b.width - t - doorRight, depth: t },
  ].filter((p) => p.width > 1e-8 && p.depth > 1e-8);
}
/** Shared edges have one owner; no opaque boxes occupy overlapping wall volumes. */
export function garageParts(
  garage: GarageGeometry,
  cutaway = false,
): BoxPart[] {
  const b = rectangleBounds(garage.polygon),
    t = garage.wall_thickness_m;
  const base = garage.elevation_m,
    h = cutaway ? Math.min(1.15, garage.height_m) : garage.height_m;
  const doorX = (garage.vehicle_door_start[0] + garage.vehicle_door_end[0]) / 2;
  const doorY = (garage.vehicle_door_start[1] + garage.vehicle_door_end[1]) / 2;
  const parts: BoxPart[] = garageWallFootprints(garage).map((p) => ({
    position: [p.x + p.width / 2, base + h / 2, -p.y - p.depth / 2],
    size: [p.width, h, p.depth],
    yaw: 0,
    surface: "stone",
  }));
  if (h > garage.vehicle_door_height_m)
    parts.push({
      position: [
        doorX,
        base + (h + garage.vehicle_door_height_m) / 2,
        -doorY - t / 2,
      ],
      size: [garage.vehicle_door_width_m, h - garage.vehicle_door_height_m, t],
      yaw: 0,
      surface: "stone",
    });
  parts.push({
    position: [
      b.x + b.width / 2,
      base - garage.slab_thickness_m / 2,
      -b.y - b.depth / 2,
    ],
    size: [b.width, garage.slab_thickness_m, b.depth],
    yaw: 0,
    surface: "concrete",
  });
  if (!cutaway)
    parts.push({
      position: [
        b.x + b.width / 2,
        base + h + garage.roof_thickness_m / 2,
        -b.y - b.depth / 2,
      ],
      size: [b.width, garage.roof_thickness_m, b.depth],
      yaw: 0,
      surface: "concrete",
    });
  // Recess the overhead door inside its canonical opening. Panel grooves are
  // presentation joinery, like the house window frames, never measurements.
  const doorHeight = Math.min(h, garage.vehicle_door_height_m);
  parts.push({
    position: [doorX, base + doorHeight / 2, -doorY - t * 0.55],
    size: [garage.vehicle_door_width_m, doorHeight, 0.045],
    yaw: 0,
    surface: "metal",
  });
  for (let z = 0.38; z < doorHeight - 0.08; z += 0.38)
    parts.push({
      position: [doorX, base + z, -doorY - t * 0.55 + 0.03],
      size: [garage.vehicle_door_width_m - 0.06, 0.012, 0.014],
      yaw: 0,
      surface: "concrete",
    });
  return parts;
}
