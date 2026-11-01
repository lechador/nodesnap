import type { RenderSnapshot } from "./scene-model";
import type { GarageGeometry } from "./site-model";

export const PROJECT_BOUNDARY_ID = "project-boundary";
export type SiteFeatureKind =
  "boundary" | "yard" | "garage" | "driveway" | "pool_deck" | "pool";
export interface SiteFeature {
  id: string;
  kind: SiteFeatureKind;
  label: string;
  polygon: number[][];
}

function isPolygon(polygon: number[][] | undefined): polygon is number[][] {
  return (
    !!polygon &&
    polygon.length >= 3 &&
    polygon.every(
      (point) =>
        point.length >= 2 &&
        Number.isFinite(point[0]) &&
        Number.isFinite(point[1]),
    )
  );
}

function polygonArea(polygon: number[][]) {
  return (
    Math.abs(
      polygon.reduce((sum, point, index) => {
        const next = polygon[(index + 1) % polygon.length];
        return sum + point[0] * next[1] - next[0] * point[1];
      }, 0),
    ) / 2
  );
}

/** Quantities of the canonical ring; width/depth are local X/Y extents. */
export function polygonQuantities(polygon: number[][]) {
  if (!isPolygon(polygon))
    return { width_m: 0, depth_m: 0, area_m2: 0, perimeter_m: 0 };
  const xs = polygon.map((point) => point[0]),
    ys = polygon.map((point) => point[1]);
  return {
    width_m: Math.max(...xs) - Math.min(...xs),
    depth_m: Math.max(...ys) - Math.min(...ys),
    area_m2: polygonArea(polygon),
    perimeter_m: polygon.reduce((sum, point, index) => {
      const next = polygon[(index + 1) % polygon.length];
      return sum + Math.hypot(next[0] - point[0], next[1] - point[1]);
    }, 0),
  };
}

/** Holes belong to other site features and must not be counted as lawn/paving. */
export function surfaceQuantities(surface: {
  polygon: number[][];
  holes?: number[][][];
}) {
  const polygon = polygonQuantities(surface.polygon);
  const excluded_area_m2 = (surface.holes ?? []).reduce(
    (sum, hole) => sum + polygonQuantities(hole).area_m2,
    0,
  );
  return {
    width_m: polygon.width_m,
    depth_m: polygon.depth_m,
    gross_area_m2: polygon.area_m2,
    excluded_area_m2,
    net_area_m2: Math.max(0, polygon.area_m2 - excluded_area_m2),
  };
}

/** The current canonical garage is rectangular, dimensioned to exterior faces. */
export function garageQuantities(
  garage: Pick<GarageGeometry, "polygon" | "wall_thickness_m">,
) {
  const polygon = polygonQuantities(garage.polygon);
  const clear_width_m = Math.max(
    0,
    polygon.width_m - 2 * garage.wall_thickness_m,
  );
  const clear_depth_m = Math.max(
    0,
    polygon.depth_m - 2 * garage.wall_thickness_m,
  );
  return {
    width_m: polygon.width_m,
    depth_m: polygon.depth_m,
    gross_area_m2: polygon.area_m2,
    clear_width_m,
    clear_depth_m,
    clear_area_m2: clear_width_m * clear_depth_m,
  };
}

function outdoorFeatures(snap: RenderSnapshot): SiteFeature[] {
  const features: SiteFeature[] = [];
  for (const kind of ["yard", "garage", "driveway", "pool_deck"] as const) {
    const feature = snap.site_layout?.[kind];
    if (feature && isPolygon(feature.polygon))
      features.push({
        id: feature.id,
        kind,
        label: feature.name,
        polygon: feature.polygon,
      });
  }
  const pool = snap.pool;
  if (pool?.location === "outdoor") {
    const x = pool.origin_x_m,
      y = pool.origin_y_m;
    const polygon = [
      [x, y],
      [x + pool.water_length_m, y],
      [x + pool.water_length_m, y + pool.water_width_m],
      [x, y + pool.water_width_m],
      [x, y],
    ];
    if (isPolygon(polygon))
      features.push({
        id: pool.id ?? "site-pool",
        kind: "pool",
        label: "Outdoor pool",
        polygon,
      });
  }
  return features;
}

/** A modeled study extent, never a cadastral/property boundary or legal setback. */
export function projectBoundaryPolygon(snap: RenderSnapshot): number[][] {
  const saved = snap.site_layout?.context_polygon;
  if (isPolygon(saved)) return saved;
  // Older revisions have no saved site context. Frame all authoritative geometry
  // with the same 3 m display margin as domain.site.coordinate_site.
  const polygons = [
    ...(snap.architecture?.slabs ?? []).map((slab) => slab.polygon),
    ...snap.spaces.map((space) => space.polygon),
    ...outdoorFeatures(snap).map((feature) => feature.polygon),
  ].filter(isPolygon);
  const points = polygons.flat();
  if (!points.length) return [];
  const xs = points.map((point) => point[0]),
    ys = points.map((point) => point[1]);
  const minX = Math.min(...xs) - 3,
    maxX = Math.max(...xs) + 3;
  const minY = Math.min(...ys) - 3,
    maxY = Math.max(...ys) + 3;
  return [
    [minX, minY],
    [maxX, minY],
    [maxX, maxY],
    [minX, maxY],
    [minX, minY],
  ];
}

export function siteFeatures(snap: RenderSnapshot): SiteFeature[] {
  const polygon = projectBoundaryPolygon(snap);
  const features = outdoorFeatures(snap);
  return polygon.length
    ? [
        {
          id: PROJECT_BOUNDARY_ID,
          kind: "boundary",
          label: "Project boundary",
          polygon,
        },
        ...features,
      ]
    : features;
}

export function findSiteFeature(
  snap: RenderSnapshot,
  id: string,
): SiteFeature | undefined {
  return siteFeatures(snap).find((feature) => feature.id === id);
}
