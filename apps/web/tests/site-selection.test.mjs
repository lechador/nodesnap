import test from "node:test";
import assert from "node:assert/strict";
import {
  PROJECT_BOUNDARY_ID,
  findSiteFeature,
  garageQuantities,
  polygonQuantities,
  projectBoundaryPolygon,
  siteFeatures,
  surfaceQuantities,
} from "../app/site-selection.ts";

const rect = (x, y, width, depth) => [
  [x, y],
  [x + width, y],
  [x + width, y + depth],
  [x, y + depth],
  [x, y],
];
const near = (actual, expected) =>
  assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
const feature = (id, name, polygon, holes = []) => ({
  id,
  name,
  polygon,
  holes,
  elevation_m: 0,
  material: "paving",
});
function fixture() {
  const water = rect(3, 13.5, 6, 3),
    deck = rect(2.4, 12.9, 7.2, 4.2);
  return {
    revision_id: "revision-one",
    revision_number: 1,
    levels: [{ id: "ground", name: "ground", label: "Ground", elevation_m: 0 }],
    spaces: [
      {
        id: "living",
        level_id: "ground",
        name: "Living",
        polygon: rect(0, 0, 12, 10),
      },
    ],
    architecture: {
      revision_id: "revision-one",
      walls: [],
      openings: [],
      stairs: [],
      space_metrics: [],
      slabs: [
        {
          id: "floor",
          polygon: rect(0, 0, 12, 10),
          holes: [],
          level_id: "ground",
          thickness_m: 0.25,
          kind: "floor",
        },
      ],
    },
    site_layout: {
      revision_id: "revision-one",
      context_polygon: rect(-3, -9, 23.1, 31),
      yard: {
        ...feature("yard-stable", "Rear yard", rect(0, 11, 12, 8), [deck]),
        material: "grass",
      },
      garage: {
        id: "garage-stable",
        name: "Detached garage",
        polygon: rect(13.5, 0, 3.6, 6),
        elevation_m: 0,
        height_m: 2.8,
        wall_thickness_m: 0.2,
        slab_thickness_m: 0.16,
        roof_thickness_m: 0.18,
        vehicle_door_width_m: 2.6,
        vehicle_door_height_m: 2.2,
        vehicle_door_start: [14, 0],
        vehicle_door_end: [16.6, 0],
      },
      driveway: feature(
        "driveway-stable",
        "Garage approach",
        rect(13.5, -6, 3.6, 6),
      ),
      pool_deck: feature("deck-stable", "Outdoor pool deck", deck, [water]),
    },
    pool: {
      id: "pool-stable",
      location: "outdoor",
      level_id: "ground",
      origin_x_m: 3,
      origin_y_m: 13.5,
      water_length_m: 6,
      water_width_m: 3,
      water_depth_m: 1.5,
    },
  };
}

test("saved boundary contains house, rear yard, approach, garage, deck and water", () => {
  const snap = fixture(),
    polygon = projectBoundaryPolygon(snap);
  assert.deepEqual(polygon, snap.site_layout.context_polygon);
  const xs = polygon.map((p) => p[0]),
    ys = polygon.map((p) => p[1]);
  for (const ring of [
    snap.spaces[0].polygon,
    ...siteFeatures(snap).map((f) => f.polygon),
  ]) {
    for (const [x, y] of ring) {
      assert.ok(x >= Math.min(...xs) - 1e-8 && x <= Math.max(...xs) + 1e-8);
      assert.ok(y >= Math.min(...ys) - 1e-8 && y <= Math.max(...ys) + 1e-8);
    }
  }
  const quantities = polygonQuantities(polygon);
  near(quantities.area_m2, 716.1);
  near(quantities.perimeter_m, 108.2);
});

test("saved study polygon is authoritative instead of silently enlarged or replaced", () => {
  const snap = fixture();
  snap.site_layout.context_polygon = rect(-8, -12, 40, 50);
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-8, -12, 40, 50));
  assert.equal(
    findSiteFeature(snap, PROJECT_BOUNDARY_ID).label,
    "Project boundary",
  );
});

test("legacy boundary uses all slab, space and outdoor extents plus a 3 metre margin", () => {
  const snap = fixture();
  snap.site_layout.context_polygon = [];
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-3, -9, 23.1, 31));
  snap.architecture.slabs.push({
    ...snap.architecture.slabs[0],
    polygon: rect(-2, 0, 2, 2),
  });
  snap.spaces.push({ ...snap.spaces[0], polygon: rect(0, 22, 2, 2) });
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-5, -9, 25.1, 36));
});

test("a legacy house without site layout receives a boundary and an empty model does not", () => {
  const snap = fixture();
  delete snap.site_layout;
  delete snap.pool;
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-3, -3, 18, 16));
  delete snap.architecture;
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-3, -3, 18, 16));
  snap.spaces = [];
  assert.deepEqual(projectBoundaryPolygon(snap), []);
  assert.deepEqual(siteFeatures(snap), []);
});

test("outdoor pool contributes its footprint with no site layout and indoor pools stay in the house", () => {
  const snap = fixture();
  delete snap.site_layout;
  snap.pool.origin_y_m = 24;
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-3, -3, 18, 33));
  assert.equal(findSiteFeature(snap, "pool-stable").kind, "pool");
  delete snap.pool.id;
  assert.equal(findSiteFeature(snap, "site-pool").kind, "pool");
  snap.pool.location = "indoor";
  assert.equal(findSiteFeature(snap, "site-pool"), undefined);
  assert.deepEqual(projectBoundaryPolygon(snap), rect(-3, -3, 18, 16));
});

test("lawn excludes the whole pool/deck footprint while paving excludes only pool water", () => {
  const snap = fixture(),
    lawn = surfaceQuantities(snap.site_layout.yard),
    deck = surfaceQuantities(snap.site_layout.pool_deck);
  near(lawn.gross_area_m2, 96);
  near(lawn.excluded_area_m2, 30.24);
  near(lawn.net_area_m2, 65.76);
  near(deck.gross_area_m2, 30.24);
  near(deck.excluded_area_m2, 18);
  near(deck.net_area_m2, 12.24);
  near(lawn.net_area_m2 + deck.net_area_m2 + 18, lawn.gross_area_m2);
  near(
    surfaceQuantities({ polygon: rect(-5, -5, 4, 3).reverse() }).net_area_m2,
    12,
  );
});

test("garage clear floor area subtracts both wall faces from each exterior dimension", () => {
  const q = garageQuantities(fixture().site_layout.garage);
  near(q.width_m, 3.6);
  near(q.depth_m, 6);
  near(q.gross_area_m2, 21.6);
  near(q.clear_width_m, 3.2);
  near(q.clear_depth_m, 5.6);
  near(q.clear_area_m2, 17.92);
});

test("selection follows canonical IDs through revisions and disappears only when removed", () => {
  const snap = fixture(),
    before = structuredClone(snap);
  assert.deepEqual(
    siteFeatures(snap).map(({ id }) => id),
    [
      PROJECT_BOUNDARY_ID,
      "yard-stable",
      "garage-stable",
      "driveway-stable",
      "deck-stable",
      "pool-stable",
    ],
  );
  assert.equal(findSiteFeature(snap, "living"), undefined);
  assert.equal(findSiteFeature(snap, "missing"), undefined);
  assert.deepEqual(
    snap,
    before,
    "read adapters must not mutate saved revisions",
  );
  const next = structuredClone(snap);
  next.revision_id = "revision-two";
  next.revision_number = 2;
  next.site_layout.yard.polygon = rect(0, 11, 12, 10);
  assert.equal(findSiteFeature(next, "yard-stable").id, "yard-stable");
  near(
    polygonQuantities(findSiteFeature(next, "yard-stable").polygon).area_m2,
    120,
  );
  next.site_layout.garage = null;
  assert.equal(findSiteFeature(next, "garage-stable"), undefined);
});
