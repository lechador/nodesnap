import type { SiteGeometry } from "./site-model";
/** Canonical XY/Z-up to the renderer's XZ/Y-up adapter. All dimensions are SI.
 * Presentation joinery/furniture never participates in measurements or analysis.
 */
export interface RenderSpace {
  id: string;
  level_id: string;
  name: string;
  use: string;
  classification: string;
  polygon: number[][];
}
export interface RenderLevel {
  id: string;
  name: string;
  label: string;
  elevation_m: number;
}
export interface RenderWall {
  id: string;
  level_id: string;
  start: number[];
  end: number[];
  thickness_m: number;
  height_m: number;
  exterior: boolean;
  material: string;
  role: string;
  space_ids: string[];
}
export interface RenderOpening {
  id: string;
  wall_id: string;
  kind: string;
  offset_m: number;
  width_m: number;
  height_m: number;
  sill_height_m: number;
  space_ids: string[];
  hinge?: string;
}
export interface RenderSlab {
  id: string;
  level_id: string;
  polygon: number[][];
  holes: number[][][];
  thickness_m: number;
  kind: string;
  material?: string;
  elevation_m?: number | null;
}
export interface RenderStair {
  id: string;
  lower_level_id: string;
  upper_level_id: string;
  polygon: number[][];
  width_m: number;
  riser_count: number;
  riser_height_m: number;
  tread_depth_m: number;
  flight_run_m: number;
  landing_depth_m: number;
  lower_space_id: string;
  upper_space_id: string;
  orientation?: "north" | "south";
}
export interface RenderSnapshot {
  revision_id: string;
  revision_number: number;
  levels: RenderLevel[];
  spaces: RenderSpace[];
  site_layout?: SiteGeometry | null;
  material_palette?: "limestone_oak" | "warm_concrete" | "white_stucco";
  pool?: {
    id?: string;
    location?: "indoor" | "outdoor";
    level_id: string;
    origin_x_m: number;
    origin_y_m: number;
    water_length_m: number;
    water_width_m: number;
    water_depth_m: number;
  } | null;
  architecture?: {
    revision_id: string;
    walls: RenderWall[];
    openings: RenderOpening[];
    slabs: RenderSlab[];
    stairs: RenderStair[];
    space_metrics: { space_id: string; clear_polygon: number[][] }[];
  } | null;
}
export type Surface =
  | "stone"
  | "plaster"
  | "concrete"
  | "glass"
  | "metal"
  | "timber"
  | "linen"
  | "water"
  | "cap"
  | "grass"
  | "ground";
export type Point3 = [number, number, number];
export interface BoxPart {
  position: Point3;
  size: Point3;
  yaw: number;
  surface: Surface;
  objectId?: string;
}
export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  width: number;
  depth: number;
  cx: number;
  cy: number;
}

export function boundsOf(points: number[][]): Bounds {
  const xs = points.map((p) => p[0]),
    ys = points.map((p) => p[1]);
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minY = Math.min(...ys),
    maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    minY,
    maxY,
    width: maxX - minX,
    depth: maxY - minY,
    cx: (maxX + minX) / 2,
    cy: (maxY + minY) / 2,
  };
}

export function modelBounds(
  snapshot: RenderSnapshot,
  includeSite = true,
): Bounds {
  const rings =
    snapshot.architecture?.slabs.map((s) => s.polygon) ??
    snapshot.spaces.map((s) => s.polygon);
  return boundsOf([
    ...rings.flat(),
    ...(includeSite && snapshot.site_layout
      ? [
          snapshot.site_layout.yard,
          snapshot.site_layout.garage,
          snapshot.site_layout.driveway,
          snapshot.site_layout.pool_deck,
        ].flatMap((feature) => feature?.polygon ?? [])
      : []),
  ]);
}

/** Actual displayed heights, including raised roofs, stair covers and exploded offsets. */
export function sceneVerticalBounds(
  snapshot: RenderSnapshot,
  mode: "building" | "cutaway" | "exploded",
  levelId: string,
) {
  const levels = [...snapshot.levels].sort(
    (a, b) => a.elevation_m - b.elevation_m,
  );
  let min = Infinity,
    max = -Infinity;
  levels.forEach((level, index) => {
    if (
      mode === "cutaway"
        ? level.id !== levelId
        : mode === "building" && level.elevation_m < 0
    )
      return;
    const offset = mode === "exploded" ? index * 3.5 : 0;
    const base = level.elevation_m + offset;
    min = Math.min(min, base - 0.25);
    max = Math.max(max, base + 1);
    if (!snapshot.architecture)
      max = Math.max(
        max,
        base +
          ((levels[index + 1]?.elevation_m ?? level.elevation_m + 2.6) -
            level.elevation_m),
      );
    for (const wall of snapshot.architecture?.walls ?? []) {
      if (wall.level_id === level.id)
        max = Math.max(
          max,
          base +
            (mode === "cutaway" && wall.role !== "guard"
              ? Math.min(1.15, wall.height_m)
              : wall.height_m),
        );
    }
    for (const slab of snapshot.architecture?.slabs ?? []) {
      if (slab.level_id !== level.id) continue;
      const top = slab.elevation_m ?? level.elevation_m;
      if (mode === "cutaway" && top > level.elevation_m + 1.15) continue;
      min = Math.min(min, top + offset - slab.thickness_m);
      max = Math.max(max, top + offset);
    }
    for (const stair of snapshot.architecture?.stairs ?? []) {
      if (stair.lower_level_id === level.id)
        max = Math.max(max, base + stair.riser_count * stair.riser_height_m);
    }
    if (
      snapshot.pool?.location !== "outdoor" &&
      snapshot.pool?.level_id === level.id
    )
      min = Math.min(min, base - snapshot.pool.water_depth_m);
  });
  const showSite =
    mode !== "cutaway" ||
    snapshot.levels.find((l) => l.id === levelId)?.name === "ground";
  if (showSite && snapshot.site_layout) {
    const garage = snapshot.site_layout.garage;
    if (garage) {
      min = Math.min(min, garage.elevation_m - garage.slab_thickness_m);
      max = Math.max(
        max,
        garage.elevation_m +
          (mode === "cutaway"
            ? Math.min(1.15, garage.height_m)
            : garage.height_m + garage.roof_thickness_m),
      );
    }
    if (snapshot.pool?.location === "outdoor") {
      const datum =
        snapshot.levels.find((l) => l.id === snapshot.pool?.level_id)
          ?.elevation_m ?? 0;
      min = Math.min(min, datum - snapshot.pool.water_depth_m);
    }
  }
  if (!Number.isFinite(min)) return { min: 0, max: 1, height: 1 };
  return { min, max, height: max - min };
}

/** Project the model bounds onto the initial orthographic camera axes. */
export function orthographicFrame(
  bounds: Bounds,
  vertical: { min: number; max: number; height: number },
  width: number,
  height: number,
) {
  const horizontal = Math.hypot(27, 32),
    distance = Math.hypot(horizontal, 24);
  const projectedWidth = (bounds.width * 32 + bounds.depth * 27) / horizontal;
  const projectedHeight =
    (((bounds.width * 27 + bounds.depth * 32) / horizontal) * 24) / distance +
    (vertical.height * horizontal) / distance;
  return {
    zoom: Math.min(
      (width * 0.88) / Math.max(1, projectedWidth),
      (height * 0.74) / Math.max(1, projectedHeight),
    ),
    targetY: (vertical.min + vertical.max) / 2,
    distanceScale: Math.max(
      1,
      (vertical.height + Math.max(bounds.width, bounds.depth)) / 55,
    ),
  };
}

/** Mirrors the supported move_wall domain, without claiming final validation. */
export function movablePartitions(
  snapshot: RenderSnapshot,
  selected: string,
  levelId: string,
): RenderWall[] {
  return (snapshot.architecture?.walls ?? []).filter((wall) => {
    if (
      wall.level_id !== levelId ||
      wall.exterior ||
      wall.role !== "partition" ||
      wall.space_ids.length !== 2 ||
      !wall.space_ids.includes(selected) ||
      Math.abs(wall.start[0] - wall.end[0]) > 1e-7
    )
      return false;
    const owners = wall.space_ids.map((id) =>
      snapshot.spaces.find((space) => space.id === id),
    );
    if (owners.some((space) => !space || space.classification !== "principal"))
      return false;
    const [a, b] = owners.map((space) => boundsOf(space!.polygon));
    return Math.abs(a.minY - b.minY) < 1e-7 && Math.abs(a.maxY - b.maxY) < 1e-7;
  });
}

export function partitionMoveFits(
  snapshot: RenderSnapshot,
  wall: RenderWall,
  offset: number,
): boolean {
  return wall.space_ids.every((id) => {
    const space = snapshot.spaces.find((s) => s.id === id);
    if (!space) return false;
    const moved = space.polygon.map(([x, y]) => [
      Math.abs(x - wall.start[0]) < 1e-7 ? x + offset : x,
      y,
    ]);
    return boundsOf(moved).width >= 1.5 - 1e-7;
  });
}

interface AxisBox {
  min: Point3;
  max: Point3;
}

const JOIN_EPSILON = 1e-8;

/** Exact bounds for the orthogonal wall family; never approximate angled walls. */
function axisBox(part: BoxPart): AxisBox | undefined {
  const alongX = Math.abs(Math.sin(part.yaw)) < JOIN_EPSILON;
  if (!alongX && Math.abs(Math.cos(part.yaw)) >= JOIN_EPSILON) return undefined;
  const size: Point3 = alongX
    ? part.size
    : [part.size[2], part.size[1], part.size[0]];
  return {
    min: part.position.map((p, axis) => p - size[axis] / 2) as Point3,
    max: part.position.map((p, axis) => p + size[axis] / 2) as Point3,
  };
}

/** Partition a box around an occupied intersection without moving its faces. */
function subtractBox(part: BoxPart, occupied: AxisBox): BoxPart[] {
  const box = axisBox(part);
  if (!box) return [part];
  const low = box.min.map((v, axis) => Math.max(v, occupied.min[axis]));
  const high = box.max.map((v, axis) => Math.min(v, occupied.max[axis]));
  if (low.some((v, axis) => high[axis] - v <= JOIN_EPSILON)) return [part];

  const fragments: BoxPart[] = [];
  const emit = (min: Point3, max: Point3) => {
    const size = max.map((v, axis) => v - min[axis]) as Point3;
    fragments.push({
      ...part,
      position: min.map((v, axis) => (v + max[axis]) / 2) as Point3,
      size:
        Math.abs(Math.sin(part.yaw)) < JOIN_EPSILON
          ? size
          : [size[2], size[1], size[0]],
    });
  };
  // Peel off at most six disjoint slabs. The remaining intersection is hidden
  // inside the owning wall and must not contribute another coplanar face.
  for (let axis = 0; axis < 3; axis++) {
    if (low[axis] - box.min[axis] > JOIN_EPSILON) {
      const end: Point3 = [...box.max];
      end[axis] = low[axis];
      emit([...box.min], end);
      box.min[axis] = low[axis];
    }
    if (box.max[axis] - high[axis] > JOIN_EPSILON) {
      const start: Point3 = [...box.min];
      start[axis] = high[axis];
      emit(start, [...box.max]);
      box.max[axis] = high[axis];
    }
  }
  return fragments;
}

/**
 * Resolve visible wall junctions without changing the canonical snapshot.
 * Exterior walls own their intersections; horizontal runs own exterior corners.
 * Subtraction uses actual solids, so openings and shorter hosts remain respected.
 * The occupied union, opening coordinates and outer dimensions are unchanged.
 */
export function joinedWallParts(
  walls: RenderWall[],
  openings: RenderOpening[],
  clipHeight?: number,
): BoxPart[] {
  const horizontal = (wall: RenderWall) =>
    Math.abs(wall.end[1] - wall.start[1]) < JOIN_EPSILON;
  const ordered = [...walls].sort(
    (a, b) =>
      Number(b.exterior) - Number(a.exterior) ||
      Number(horizontal(b)) - Number(horizontal(a)) ||
      (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
  );
  const occupied = new Map<string, AxisBox[]>();
  const result: BoxPart[] = [];
  for (const wall of ordered) {
    const parts = wallParts(
      wall,
      openings,
      wall.role === "guard" ? undefined : clipHeight,
    );
    if (wall.role === "guard" || wall.material === "glass") {
      result.push(...parts);
      continue;
    }
    const hosts = occupied.get(wall.level_id) ?? [];
    const ownBounds: AxisBox[] = [];
    for (const part of parts) {
      const bounds = axisBox(part);
      if (!bounds || part.surface === "glass") {
        result.push(part);
        continue;
      }
      let fragments = [part];
      for (const host of hosts) {
        if (!fragments.length) break;
        // Reject non-intersecting hosts before allocating any fragments.
        if (
          bounds.min.some(
            (min, axis) =>
              Math.min(bounds.max[axis], host.max[axis]) -
                Math.max(min, host.min[axis]) <=
              JOIN_EPSILON,
          )
        )
          continue;
        fragments = fragments.flatMap((fragment) =>
          subtractBox(fragment, host),
        );
      }
      result.push(...fragments);
      ownBounds.push(bounds);
    }
    // Parts within this wall already share edges, including its frame and cap.
    // Raw occupied bounds have the same union as the resolved fragments.
    hosts.push(...ownBounds);
    occupied.set(wall.level_id, hosts);
  }
  return result;
}

/** Wall segments subtract every hosted opening in both elevation and plan. */
export function wallParts(
  wall: RenderWall,
  openings: RenderOpening[],
  clipHeight?: number,
): BoxPart[] {
  const parts: BoxPart[] = [];
  const dx = wall.end[0] - wall.start[0],
    dy = wall.end[1] - wall.start[1];
  const length = Math.hypot(dx, dy),
    yaw = Math.atan2(dy, dx);
  const height = Math.min(clipHeight ?? wall.height_m, wall.height_m);
  if (length <= 0 || height <= 0) return parts;
  const surface: Surface =
    wall.material === "glass"
      ? "glass"
      : wall.material === "concrete"
        ? "concrete"
        : wall.material === "stone"
          ? "stone"
          : "plaster";
  const put = (
    start: number,
    end: number,
    bottom: number,
    top: number,
    material: Surface = surface,
    thickness = wall.thickness_m,
    body = false,
  ) => {
    const low = Math.max(0, bottom),
      high = Math.min(height, top);
    if (end - start < 0.001 || high - low < 0.001) return;
    if (
      body &&
      surface !== "glass" &&
      clipHeight !== undefined &&
      wall.height_m > clipHeight &&
      high === height
    ) {
      const capBottom = Math.max(low, height - 0.018);
      put(start, end, low, capBottom, material, thickness);
      put(start, end, capBottom, height, "cap", thickness);
      return;
    }
    const middle = (start + end) / 2;
    parts.push({
      position: [
        wall.start[0] + (dx / length) * middle,
        (high + low) / 2,
        -(wall.start[1] + (dy / length) * middle),
      ],
      size: [end - start, high - low, thickness],
      yaw,
      surface: material,
      objectId: wall.space_ids[0],
    });
  };
  const hosted = openings
    .filter((o) => o.wall_id === wall.id)
    .sort((a, b) => a.offset_m - b.offset_m);
  let cursor = 0;
  for (const opening of hosted) {
    const start = Math.max(0, opening.offset_m),
      end = Math.min(length, start + opening.width_m);
    put(cursor, start, 0, height, surface, wall.thickness_m, true);
    put(start, end, 0, opening.sill_height_m, surface, wall.thickness_m, true);
    put(
      start,
      end,
      opening.sill_height_m + opening.height_m,
      height,
      surface,
      wall.thickness_m,
      true,
    );
    if (opening.kind !== "passage") {
      const bottom = opening.sill_height_m,
        top = bottom + opening.height_m;
      const frame = 0.055;
      put(start, start + frame, bottom, top, "metal", wall.thickness_m + 0.015);
      put(end - frame, end, bottom, top, "metal", wall.thickness_m + 0.015);
      put(
        start + frame,
        end - frame,
        bottom,
        bottom + frame,
        "metal",
        wall.thickness_m + 0.015,
      );
      put(
        start + frame,
        end - frame,
        top - frame,
        top,
        "metal",
        wall.thickness_m + 0.015,
      );
      put(
        start + frame,
        end - frame,
        bottom + frame,
        top - frame,
        opening.kind === "window" ? "glass" : "timber",
        0.035,
      );
      // Glazing mullions are presentation framing, not structural elements.
      if (opening.kind === "window" && opening.width_m > 1.8) {
        const bays = Math.ceil(opening.width_m / 1.5);
        for (let i = 1; i < bays; i++) {
          const at = start + (opening.width_m * i) / bays;
          put(
            at - frame / 2,
            at + frame / 2,
            bottom + frame,
            top - frame,
            "metal",
            wall.thickness_m + 0.025,
          );
        }
      }
    }
    cursor = Math.max(cursor, end);
  }
  put(cursor, length, 0, height, surface, wall.thickness_m, true);
  return parts;
}

export function stairParts(stair: RenderStair): BoxPart[] {
  const b = boundsOf(stair.polygon),
    parts: BoxPart[] = [];
  const half = Math.floor(stair.riser_count / 2),
    second = stair.riser_count - half;
  const width = stair.width_m;
  const south = stair.orientation === "south";
  const put = (
    x: number,
    y: number,
    z: number,
    w: number,
    h: number,
    d: number,
  ) =>
    parts.push({
      position: [x, y, -z] as Point3,
      size: [w, h, d] as Point3,
      yaw: 0,
      surface: "timber" as Surface,
      objectId: stair.lower_space_id,
    });
  for (let i = 0; i < half - 1; i++) {
    const height = (i + 1) * stair.riser_height_m;
    put(
      b.minX + width / 2,
      height - 0.065,
      south
        ? b.maxY - (i + 0.5) * stair.tread_depth_m
        : b.minY + (i + 0.5) * stair.tread_depth_m,
      width,
      0.13,
      stair.tread_depth_m,
    );
  }
  put(
    b.cx,
    half * stair.riser_height_m - 0.08,
    south
      ? b.minY + stair.landing_depth_m / 2
      : b.maxY - stair.landing_depth_m / 2,
    b.width,
    0.16,
    stair.landing_depth_m,
  );
  for (let i = 0; i < second - 1; i++) {
    const height = (half + i + 1) * stair.riser_height_m;
    put(
      b.maxX - width / 2,
      height - 0.065,
      south
        ? b.minY + stair.landing_depth_m + (i + 0.5) * stair.tread_depth_m
        : b.maxY - stair.landing_depth_m - (i + 0.5) * stair.tread_depth_m,
      width,
      0.13,
      stair.tread_depth_m,
    );
  }
  return parts;
}

/** Optional presentation furniture fitted within clear polygons. Never exported as equipment. */
export function furnishingParts(
  space: RenderSpace,
  clearPolygon?: number[][],
): BoxPart[] {
  const b = boundsOf(clearPolygon ?? space.polygon),
    out: BoxPart[] = [];
  if (b.width < 2.1 || b.depth < 2.1) return out;
  const put = (
    x: number,
    z: number,
    w: number,
    d: number,
    h: number,
    surface: Surface,
    y = 0,
  ) =>
    out.push({
      position: [x, y + h / 2, -z],
      size: [w, h, d],
      yaw: 0,
      surface,
      objectId: space.id,
    });
  const cx = b.cx,
    cy = b.cy,
    maxW = b.width - 0.7,
    maxD = b.depth - 0.7;
  if (space.use === "bedroom") {
    const w = Math.min(1.9, maxW),
      d = Math.min(2.1, maxD),
      z = b.maxY - d / 2 - 0.38;
    put(cx, z, w + 0.12, d + 0.12, 0.25, "timber");
    put(cx, z, w, d, 0.26, "linen", 0.25);
    put(cx, z + d / 2 + 0.03, w + 0.16, 0.1, 0.95, "timber");
    put(cx - w / 4, z + d / 2 - 0.4, w / 2 - 0.1, 0.42, 0.1, "plaster", 0.51);
    put(cx + w / 4, z + d / 2 - 0.4, w / 2 - 0.1, 0.42, 0.1, "plaster", 0.51);
    if (maxW > w + 1.1) {
      put(cx - w / 2 - 0.42, z + d / 2 - 0.35, 0.5, 0.5, 0.4, "timber");
      put(cx + w / 2 + 0.42, z + d / 2 - 0.35, 0.5, 0.5, 0.4, "timber");
    }
  } else if (["living", "family", "library", "studio"].includes(space.use)) {
    const w = Math.min(3, maxW),
      d = 0.86,
      z = b.maxY - 0.9;
    put(cx, z, w, d, 0.36, "linen");
    put(cx, z + 0.34, w, 0.2, 0.72, "linen");
    put(cx - w / 2 + 0.1, z, 0.2, d, 0.6, "linen");
    put(cx + w / 2 - 0.1, z, 0.2, d, 0.6, "linen");
    put(cx, z - 1.35, Math.min(1.4, w), 0.72, 0.28, "timber");
    put(cx, z - 1, w + 0.4, 2.6, 0.015, "linen");
  } else if (space.use === "dining") {
    const w = Math.min(1, maxW - 1),
      d = Math.min(2.7, maxD - 1);
    put(cx, cy, w, d, 0.1, "timber", 0.68);
    for (const x of [-1, 1])
      for (const z of [-1, 0, 1]) {
        put(
          cx + x * (w / 2 + 0.38),
          cy + (z * d) / 3,
          0.44,
          0.46,
          0.06,
          "linen",
          0.43,
        );
        put(
          cx + x * (w / 2 + 0.57),
          cy + (z * d) / 3,
          0.055,
          0.46,
          0.72,
          "timber",
        );
      }
  } else if (space.use === "kitchen") {
    put(cx, b.maxY - 0.5, maxW, 0.64, 0.86, "timber");
    put(cx, b.maxY - 0.5, maxW + 0.04, 0.68, 0.05, "stone", 0.86);
    const w = Math.min(2.5, maxW - 0.6);
    if (w > 0.8) {
      put(cx, cy, w, 1, 0.86, "timber");
      put(cx, cy, w + 0.08, 1.08, 0.05, "stone", 0.86);
    }
  } else if (space.use === "study") {
    put(cx, cy, Math.min(1.65, maxW), 0.75, 0.08, "timber", 0.7);
    put(cx, cy - 0.7, 0.5, 0.5, 0.08, "linen", 0.43);
    put(cx, cy - 0.92, 0.5, 0.06, 0.88, "linen");
  } else if (["bathroom", "changing"].includes(space.use)) {
    put(cx, b.maxY - 0.55, Math.min(1.3, maxW), 0.6, 0.84, "stone");
    put(cx, b.maxY - 0.55, 0.55, 0.38, 0.06, "plaster", 0.84);
  } else if (space.use === "roof_terrace") {
    const z = b.minY + 1.4;
    for (const x of [b.minX + 1.1, b.minX + 2.25]) {
      put(x, z, 0.72, 1.85, 0.22, "timber");
      put(x, z, 0.66, 1.75, 0.06, "linen", 0.22);
    }
    put(b.maxX - 1.65, b.maxY - 1.65, 1.2, 1.2, 0.12, "stone", 0.62);
  }
  return out.filter(
    (part) =>
      part.size.every((value) => value > 0) &&
      part.position[0] - part.size[0] / 2 >= b.minX + 0.02 &&
      part.position[0] + part.size[0] / 2 <= b.maxX - 0.02 &&
      -part.position[2] - part.size[2] / 2 >= b.minY + 0.02 &&
      -part.position[2] + part.size[2] / 2 <= b.maxY - 0.02,
  );
}
