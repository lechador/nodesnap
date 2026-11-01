import test from "node:test";
import assert from "node:assert/strict";
import {
  garageParts,
  garageWallFootprints,
  waterPolygon,
} from "../app/site-model.ts";
import { modelBounds, sceneVerticalBounds } from "../app/scene-model.ts";
import { planFrame } from "../app/lib/plan-frame.ts";
const rect = (x, y, w, d) => [
  [x, y],
  [x + w, y],
  [x + w, y + d],
  [x, y + d],
  [x, y],
];
const garage = {
  id: "garage",
  name: "Detached garage",
  polygon: rect(15.5, 0, 3.6, 6),
  elevation_m: 0,
  height_m: 2.8,
  wall_thickness_m: 0.2,
  slab_thickness_m: 0.16,
  roof_thickness_m: 0.18,
  vehicle_door_width_m: 2.6,
  vehicle_door_height_m: 2.2,
  vehicle_door_start: [16, 0],
  vehicle_door_end: [18.6, 0],
};
const volume = (p) => p.size.reduce((a, b) => a * b, 1);
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);
const fixture = () => ({
  revision_id: "r",
  revision_number: 1,
  levels: [
    { id: "g", name: "ground", label: "Ground", elevation_m: 0 },
    { id: "r", name: "roof", label: "Roof", elevation_m: 3.2 },
  ],
  spaces: [],
  architecture: {
    revision_id: "r",
    slabs: [
      {
        id: "s",
        level_id: "g",
        polygon: rect(0, 0, 14, 12),
        holes: [],
        thickness_m: 0.25,
        kind: "floor",
      },
    ],
    walls: [],
    openings: [],
    stairs: [],
  },
  site_layout: {
    revision_id: "r",
    context_polygon: rect(-3, -9, 25.1, 34),
    garage,
    yard: { polygon: rect(0, 13, 14, 8) },
    driveway: { polygon: rect(15.5, -6, 3.6, 6) },
    pool_deck: null,
  },
});
test("garage wall solid volume equals exterior ring minus the real vehicle opening", () => {
  const stone = garageParts(garage).filter((p) => p.surface === "stone");
  near(
    stone.reduce((sum, p) => sum + volume(p), 0),
    (3.6 * 6 - 3.2 * 5.6) * 2.8 - 2.6 * 2.2 * 0.2,
  );
  const wallArea = garageWallFootprints(garage).reduce(
    (sum, p) => sum + p.width * p.depth,
    0,
  );
  near(wallArea, 3.6 * 6 - 3.2 * 5.6 - 2.6 * 0.2);
});
test("garage corners and opening piers have no competing opaque wall volumes", () => {
  const solids = garageParts(garage).filter((p) => p.surface === "stone");
  for (let i = 0; i < solids.length; i++)
    for (let j = i + 1; j < solids.length; j++) {
      const a = solids[i],
        b = solids[j];
      const overlap = [0, 1, 2]
        .map((k) =>
          Math.max(
            0,
            Math.min(
              a.position[k] + a.size[k] / 2,
              b.position[k] + b.size[k] / 2,
            ) -
              Math.max(
                a.position[k] - a.size[k] / 2,
                b.position[k] - b.size[k] / 2,
              ),
          ),
        )
        .reduce((x, y) => x * y, 1);
      near(overlap, 0);
    }
  const door = garageParts(garage).find((p) => p.surface === "metal");
  near(door.position[0] - door.size[0] / 2, garage.vehicle_door_start[0]);
  near(door.position[0] + door.size[0] / 2, garage.vehicle_door_end[0]);
});
test("garage slab, roof and cutaway use canonical elevations with no hidden ceiling", () => {
  const shifted = { ...garage, elevation_m: 0.5 };
  const concrete = garageParts(shifted).filter(
    (p) => p.surface === "concrete" && p.size[1] > 0.02,
  );
  near(
    Math.min(...concrete.map((p) => p.position[1] - p.size[1] / 2)),
    0.5 - 0.16,
  );
  near(
    Math.max(...concrete.map((p) => p.position[1] + p.size[1] / 2)),
    0.5 + 2.8 + 0.18,
  );
  near(
    Math.max(
      ...garageParts(shifted, true).map((p) => p.position[1] + p.size[1] / 2),
    ),
    0.5 + 1.15,
  );
});
test("full site camera includes driveway and yard while floor camera retains house extents", () => {
  const snap = fixture();
  assert.deepEqual(
    [modelBounds(snap).minX, modelBounds(snap).minY, modelBounds(snap).maxY],
    [0, -6, 21],
  );
  assert.deepEqual(
    [
      modelBounds(snap, false).minX,
      modelBounds(snap, false).maxX,
      modelBounds(snap, false).maxY,
    ],
    [0, 14, 12],
  );
  const drawing = planFrame(snap.site_layout.context_polygon);
  for (const [x, y] of snap.site_layout.context_polygon) {
    const px = drawing.X + x * drawing.scale,
      py = drawing.Y + (drawing.H - y) * drawing.scale;
    assert.ok(
      px >= 85 - 1e-8 &&
        px <= 715 + 1e-8 &&
        py >= 75 - 1e-8 &&
        py <= 617.5 + 1e-8,
    );
  }
});
test("site pool stays at grade in exploded view and a tall garage fits the camera", () => {
  const snap = fixture();
  snap.site_layout.garage = { ...garage, height_m: 4.5 };
  snap.pool = {
    location: "outdoor",
    level_id: "g",
    origin_x_m: 2,
    origin_y_m: 15,
    water_length_m: 8,
    water_width_m: 3.5,
    water_depth_m: 1.6,
  };
  const limits = sceneVerticalBounds(snap, "building", "g");
  near(limits.min, -1.6);
  near(limits.max, 4.68);
  near(sceneVerticalBounds(snap, "exploded", "g").min, -1.6);
  const water = waterPolygon(snap.pool);
  assert.deepEqual(water, rect(2, 15, 8, 3.5));
  near((water[1][0] - water[0][0]) * (water[2][1] - water[1][1]), 28);
});
