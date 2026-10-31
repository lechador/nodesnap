import type { Opening, Space, Stair, Wall } from "./types";

type LabelLine = {
  kind: "name" | "area" | "dimensions";
  text: string;
  size: number;
  y: number;
};

// Conservative font allowance; the SVG also clips labels to the clear room
// polygon. Full names and measurements remain available in the room register.
function textWidth(text: string, size: number) {
  return [...text].reduce(
    (sum, character) =>
      sum +
      (/\s/.test(character)
        ? 0.4
        : /[MWmw@%\u0080-\uFFFF]/.test(character)
          ? 1.1
          : 0.8) *
        size,
    0,
  );
}

/** Place labels inside a measured clear rectangle in drawing coordinates. */
export function roomLabelLines({
  name,
  key,
  area,
  dimensions,
  width,
  height,
}: {
  name: string;
  key: string;
  area: string;
  dimensions?: string;
  width: number;
  height: number;
}): LabelLine[] {
  if (
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  )
    return [];
  const padding = Math.min(5, height * 0.12, width * 0.12);
  const availableWidth = width - padding * 2,
    availableHeight = height - padding * 2;
  let size = width >= 90 ? 10 : 8;
  const text =
    height >= 24 && textWidth(name, size) <= availableWidth ? name : key;
  size = Math.min(
    size,
    availableHeight / 1.25,
    (size * availableWidth) / Math.max(1, textWidth(text, size)),
  );
  if (size < 6) return [];
  const areaSize = 8.5;
  const showArea =
    !!area &&
    availableHeight >= size * 1.25 + areaSize * 1.25 + 3 &&
    textWidth(area, areaSize) <= availableWidth;
  const areaHeight = showArea ? areaSize * 1.25 + 3 : 0;
  const bottom = height - padding;
  const result: LabelLine[] = [
    { kind: "name", text, size, y: bottom - areaHeight - size * 0.25 },
  ];
  if (showArea)
    result.push({
      kind: "area",
      text: area,
      size: areaSize,
      y: bottom - areaSize * 0.25,
    });
  const dimensionSize = 8;
  if (
    dimensions &&
    availableHeight >= size * 1.25 + areaHeight + dimensionSize * 1.25 + 8 &&
    textWidth(dimensions, dimensionSize) <= availableWidth
  )
    result.push({
      kind: "dimensions",
      text: dimensions,
      size: dimensionSize,
      y: padding + dimensionSize,
    });
  return result;
}

/** Match the PDF convention: swing toward the owning room, at its declared jamb. */
export function doorSwing(
  wall: Pick<Wall, "start" | "end">,
  opening: Pick<Opening, "offset_m" | "width_m" | "hinge" | "space_ids">,
  spaces: Pick<Space, "id" | "use" | "polygon">[],
) {
  const dx = wall.end[0] - wall.start[0],
    dy = wall.end[1] - wall.start[1],
    distance = Math.hypot(dx, dy);
  const nx = -dy / distance,
    ny = dx / distance;
  const start = [
    wall.start[0] + (dx / distance) * opening.offset_m,
    wall.start[1] + (dy / distance) * opening.offset_m,
  ];
  const owner =
    spaces.find(
      (space) =>
        opening.space_ids.includes(space.id) &&
        !["circulation", "stairs_service"].includes(space.use),
    ) ?? spaces.find((space) => opening.space_ids.includes(space.id));
  let side = 1;
  if (owner) {
    const ring = owner.polygon;
    const closed =
      ring.length > 1 &&
      ring[0][0] === ring.at(-1)![0] &&
      ring[0][1] === ring.at(-1)![1];
    const points = closed ? ring.slice(0, -1) : ring;
    const cx = points.reduce((sum, point) => sum + point[0], 0) / points.length;
    const cy = points.reduce((sum, point) => sum + point[1], 0) / points.length;
    side = nx * (cx - start[0]) + ny * (cy - start[1]) >= 0 ? 1 : -1;
  }
  const endHinge = opening.hinge === "end";
  return {
    hingeX: endHinge ? opening.width_m : 0,
    closedX: endHinge ? 0 : opening.width_m,
    leafY: -side * opening.width_m,
    sweep: side > 0 !== endHinge ? 1 : 0,
  };
}

/** Draw the outgoing flight on a through floor; retain both travel directions. */
export function stairPlan<
  T extends Pick<Stair, "lower_level_id" | "upper_level_id">,
>(stairs: T[], levelId: string) {
  const outgoing = stairs.find((stair) => stair.lower_level_id === levelId);
  const incoming = stairs.find((stair) => stair.upper_level_id === levelId);
  const stair = outgoing ?? incoming;
  return stair
    ? {
        stair,
        direction: outgoing && incoming ? "UP / DN" : outgoing ? "UP" : "DN",
      }
    : null;
}
