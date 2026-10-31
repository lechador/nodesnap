import test from "node:test";
import assert from "node:assert/strict";
import { joinedWallParts, wallParts } from "../app/scene-model.ts";

const EPS = 1e-8;
const wall = (id, start, end, overrides = {}) => ({
  id,
  level_id: "ground",
  start,
  end,
  height_m: 2.95,
  thickness_m: 0.15,
  exterior: false,
  role: "partition",
  material: "plaster",
  space_ids: [`room-${id}`],
  ...overrides,
});
const enclosure = (id, start, end, overrides = {}) =>
  wall(id, start, end, {
    thickness_m: 0.3,
    exterior: true,
    role: "enclosure",
    material: "concrete",
    ...overrides,
  });
const opening = (id, wallId, overrides = {}) => ({
  id,
  wall_id: wallId,
  kind: "passage",
  offset_m: 2,
  width_m: 2,
  height_m: 2.2,
  sill_height_m: 0,
  space_ids: [`room-${wallId}`],
  ...overrides,
});

// Independent world-space bounds, expressed in canonical X/Y with height Z.
// The current grammar is orthogonal; these tests deliberately avoid renderer
// implementation helpers so a mistaken adapter/subtraction cannot self-verify.
function bounds(part) {
  const dx =
    Math.abs(Math.cos(part.yaw)) * part.size[0] +
    Math.abs(Math.sin(part.yaw)) * part.size[2];
  const dy =
    Math.abs(Math.sin(part.yaw)) * part.size[0] +
    Math.abs(Math.cos(part.yaw)) * part.size[2];
  return {
    lo: [
      part.position[0] - dx / 2,
      -part.position[2] - dy / 2,
      part.position[1] - part.size[1] / 2,
    ],
    hi: [
      part.position[0] + dx / 2,
      -part.position[2] + dy / 2,
      part.position[1] + part.size[1] / 2,
    ],
  };
}
function volume(parts) {
  return parts.reduce((sum, p) => sum + p.size.reduce((a, b) => a * b), 0);
}
function occupied(parts, point) {
  return parts.some((part) => {
    const { lo, hi } = bounds(part);
    return point.every(
      (value, i) => value > lo[i] + EPS && value < hi[i] - EPS,
    );
  });
}
function close(actual, expected, message) {
  assert.ok(
    Math.abs(actual - expected) < EPS,
    `${message}: ${actual} vs ${expected}`,
  );
}
function assertDisjoint(parts) {
  const solids = parts.filter((p) => !["glass", "water"].includes(p.surface));
  for (let i = 0; i < solids.length; i++) {
    const a = bounds(solids[i]);
    for (let j = i + 1; j < solids.length; j++) {
      const b = bounds(solids[j]);
      const overlap = a.lo.map((min, axis) =>
        Math.max(
          0,
          Math.min(a.hi[axis], b.hi[axis]) - Math.max(min, b.lo[axis]),
        ),
      );
      assert.ok(
        overlap.some((extent) => extent < EPS),
        `Opaque parts overlap: ${solids[i].objectId}/${solids[i].surface} and ${solids[j].objectId}/${solids[j].surface}; extents ${overlap}`,
      );
    }
  }
}
function freeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

test("office entrance flank partitions never expose plaster on the exterior face", () => {
  // Exact problematic ground-floor coordinates from the synthetic 14 × 12 m
  // office: the entry lies between y=5.2 and y=6.8 on the west façade.
  const walls = [
    enclosure("west-south", [0.15, 0], [0.15, 5.2]),
    enclosure("entry", [0.15, 5.2], [0.15, 6.8]),
    enclosure("west-north", [0.15, 6.8], [0.15, 12]),
    wall("south-flank", [0, 5.2], [9.2307692, 5.2]),
    wall("north-flank", [0, 6.8], [3.8461538, 6.8]),
  ];
  const entry = opening("door", "entry", {
    kind: "door",
    offset_m: 0.25,
    width_m: 1.1,
    height_m: 2.5,
  });
  const parts = joinedWallParts(walls, [entry]);
  const plaster = parts.filter((p) => p.surface === "plaster");
  assert.ok(plaster.length >= 2);
  for (const part of plaster) {
    assert.ok(
      bounds(part).lo[0] >= 0.3 - EPS,
      "plaster end must stop inside façade",
    );
  }
  assertDisjoint(parts);
  // Frame and leaf must retain their canonical offset from the original host,
  // independent of how neighboring wall solids were resolved.
  assert.deepEqual(
    parts.filter((p) => p.surface === "timber"),
    wallParts(walls[1], [entry]).filter((p) => p.surface === "timber"),
  );
});

test("all four enclosure corners retain the exact envelope and solid union", () => {
  const walls = [
    enclosure("south", [0, 0.15], [14, 0.15]),
    enclosure("north", [0, 11.85], [14, 11.85]),
    enclosure("west", [0.15, 0], [0.15, 12]),
    enclosure("east", [13.85, 0], [13.85, 12]),
  ];
  const parts = joinedWallParts(walls, []);
  assertDisjoint(parts);
  close(
    volume(parts),
    (14 * 12 - 13.4 * 11.4) * 2.95,
    "rectangular wall-ring volume",
  );
  for (const part of parts) {
    const b = bounds(part);
    assert.ok(b.lo[0] >= -EPS && b.hi[0] <= 14 + EPS);
    assert.ok(b.lo[1] >= -EPS && b.hi[1] <= 12 + EPS);
  }
  for (const x of [0.05, 0.25, 13.75, 13.95]) {
    for (const y of [0.05, 0.25, 11.75, 11.95]) {
      assert.ok(
        occupied(parts, [x, y, 1]),
        `corner remains filled at ${x}, ${y}`,
      );
    }
  }
});

test("junction subtraction respects an actual opening and unequal wall heights", () => {
  const host = enclosure("low-host", [0, 0.15], [6, 0.15], { height_m: 1.5 });
  const crossing = wall("tall-partition", [3, 0], [3, 4], { height_m: 3 });
  const aperture = opening("low-passage", host.id, { height_m: 1.2 });
  const parts = joinedWallParts([crossing, host], [aperture]);
  assertDisjoint(parts);
  // Only the 300 mm tall header overlaps this partition. The passage below
  // and the taller exposed partition above must survive unchanged.
  close(
    volume(parts),
    6 * 0.3 * 1.5 - 2 * 0.3 * 1.2 + 4 * 0.15 * 3 - 0.3 * 0.15 * 0.3,
    "opening-aware solid union",
  );
  const partition = parts.filter((p) => p.objectId === "room-tall-partition");
  assert.ok(occupied(partition, [3, 0.1, 0.8]));
  assert.ok(!occupied(partition, [3, 0.1, 1.35]));
  assert.ok(occupied(partition, [3, 0.1, 2]));
  assert.ok(
    !occupied(parts, [2.5, 0.1, 0.8]),
    "unobstructed passage area stays open",
  );
});

test("cutaway caps replace wall tops and leave door and glazing voids open", () => {
  const host = enclosure("cut-wall", [0, 0.15], [6, 0.15]);
  const passage = opening("passage", host.id);
  const parts = wallParts(host, [passage], 1.15);
  const caps = parts.filter((p) => p.surface === "cap");
  assert.ok(caps.length > 0);
  assertDisjoint(parts);
  close(
    volume(parts),
    (6 - 2) * 0.3 * 1.15,
    "cap replaces wall, without added material",
  );
  for (const cap of caps) {
    close(bounds(cap).hi[2], 1.15, "cut surface elevation");
    assert.ok(
      !occupied([cap], [3, 0.15, 1.14]),
      "cap cannot bridge an opening",
    );
  }
  const glazed = wallParts(
    host,
    [
      opening("window", host.id, {
        kind: "window",
        width_m: 3,
        sill_height_m: 0.45,
      }),
    ],
    1.15,
  );
  assertDisjoint(glazed);
  assert.ok(
    !occupied(
      glazed.filter((p) => p.surface === "cap"),
      [3, 0.15, 1.14],
    ),
  );
});

test("cutaway interior T joints have a single solid and cap owner", () => {
  const host = wall("horizontal", [0, 3], [6, 3]);
  const branch = wall("vertical", [3, 0], [3, 3]);
  const parts = joinedWallParts([branch, host], [], 1.15);
  assertDisjoint(parts);
  close(
    volume(parts),
    (6 * 0.15 + 3 * 0.15 - 0.15 * 0.075) * 1.15,
    "T junction union",
  );
  assert.ok(parts.filter((p) => p.surface === "cap").length >= 2);
});

test("window framing and mullions do not contain duplicate opaque surfaces", () => {
  const host = enclosure("window-wall", [0, 0.15], [6, 0.15]);
  const pane = opening("window", host.id, {
    kind: "window",
    width_m: 3,
    height_m: 2.1,
    sill_height_m: 0.45,
  });
  const parts = wallParts(host, [pane]);
  assertDisjoint(parts);
  assert.ok(parts.some((p) => p.surface === "glass"));
});

test("canonical walls/openings stay immutable and junction ownership is order independent", () => {
  const walls = freeze([
    enclosure("exterior", [0.15, 0], [0.15, 8]),
    wall("partition", [0, 4], [6, 4]),
  ]);
  const openings = freeze([opening("door", "partition", { kind: "door" })]);
  const before = JSON.stringify({ walls, openings });
  const parts = joinedWallParts(walls, openings, 1.15);
  assert.equal(JSON.stringify({ walls, openings }), before);
  assert.deepEqual(
    joinedWallParts([...walls].reverse(), openings, 1.15),
    parts,
  );
  assert.ok(
    parts.every((p) =>
      ["room-exterior", "room-partition"].includes(p.objectId),
    ),
  );
});

test("transparent guards cannot erase opaque walls", () => {
  const partition = wall("partition", [0, 3], [6, 3]);
  const guard = enclosure("guard", [3, 0], [3, 6], {
    height_m: 1.1,
    thickness_m: 0.06,
    material: "glass",
    role: "guard",
  });
  const parts = joinedWallParts([guard, partition], []);
  close(
    volume(parts.filter((p) => p.surface === "plaster")),
    6 * 0.15 * 2.95,
    "opaque partition unaffected by glass",
  );
  assert.ok(parts.some((p) => p.surface === "glass"));
});

test("walls on different floors never subtract each other in local coordinates", () => {
  const ground = enclosure("ground-wall", [0, 0.15], [6, 0.15]);
  const upper = enclosure("upper-wall", [0, 0.15], [6, 0.15], {
    level_id: "upper",
  });
  const parts = joinedWallParts([ground, upper], [], 1.15);
  for (const host of [ground, upper]) {
    close(
      volume(parts.filter((part) => part.objectId === `room-${host.id}`)),
      6 * 0.3 * 1.15,
      `${host.level_id} retains its complete wall`,
    );
  }
});

test("nonorthogonal walls retain exact geometry instead of an AABB approximation", () => {
  const diagonal = wall("diagonal", [0, 0], [6, 6]);
  const orthogonal = enclosure("orthogonal", [0, 3], [6, 3]);
  const parts = joinedWallParts([diagonal, orthogonal], []);
  assert.deepEqual(
    parts.filter((part) => part.objectId === "room-diagonal"),
    wallParts(diagonal, []),
  );
  assert.deepEqual(
    parts.filter((part) => part.objectId === "room-orthogonal"),
    wallParts(orthogonal, []),
  );
});
