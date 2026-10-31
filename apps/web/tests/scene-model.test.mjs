import test from "node:test";
import assert from "node:assert/strict";
import {
  wallParts,
  stairParts,
  furnishingParts,
  movablePartitions,
  partitionMoveFits,
  sceneVerticalBounds,
  orthographicFrame,
} from "../app/scene-model.ts";

const wall = {
  id: "w",
  level_id: "g",
  start: [2, 3],
  end: [8, 3],
  height_m: 3,
  thickness_m: 0.2,
  exterior: false,
  role: "partition",
  material: "plaster",
  space_ids: ["room"],
};
const opening = {
  id: "o",
  wall_id: "w",
  kind: "passage",
  offset_m: 1,
  width_m: 2,
  height_m: 2.2,
  sill_height_m: 0,
  space_ids: ["room"],
  hinge: "start",
};

test("opening subtraction agrees with independent closed-form wall volume", () => {
  const parts = wallParts(wall, [opening]);
  const volume = parts.reduce(
    (sum, p) => sum + p.size[0] * p.size[1] * p.size[2],
    0,
  );
  assert.ok(Math.abs(volume - (6 * 3 * 0.2 - 2 * 2.2 * 0.2)) < 1e-10);
  assert.ok(parts.every((p) => p.position[2] === -3));
  assert.equal(Math.min(...parts.map((p) => p.position[0] - p.size[0] / 2)), 2);
  assert.equal(Math.max(...parts.map((p) => p.position[0] + p.size[0] / 2)), 8);
});

test("asymmetric canonical coordinates remain right-handed through the renderer adapter", () => {
  const [part] = wallParts({ ...wall, start: [2, 3], end: [2, 10] }, []);
  assert.deepEqual(part.position, [2, 1.5, -6.5]);
  assert.deepEqual(part.size, [7, 3, 0.2]);
  assert.equal(part.yaw, Math.PI / 2);
});

test("dogleg treads stay inside the footprint and return to the corridor side", () => {
  const stair = {
    id: "s",
    lower_level_id: "g",
    upper_level_id: "u",
    lower_space_id: "r",
    upper_space_id: "q",
    polygon: [
      [15, 2.8],
      [18, 2.8],
      [18, 6.95],
      [15, 6.95],
      [15, 2.8],
    ],
    width_m: 1.2,
    riser_count: 20,
    riser_height_m: 0.17,
    tread_depth_m: 2.95 / 9,
    flight_run_m: 2.95,
    landing_depth_m: 1.2,
    orientation: "south",
  };
  const parts = stairParts(stair);
  assert.equal(parts.length, 19); // 9 treads + landing + 9 treads; upper slab is the final landing.
  for (const part of parts) {
    assert.ok(-part.position[2] - part.size[2] / 2 >= 2.8 - 1e-8);
    assert.ok(-part.position[2] + part.size[2] / 2 <= 6.95 + 1e-8);
  }
  assert.ok(parts[0].position[0] < 16.5);
  assert.ok(parts.at(-1).position[0] > 16.5);
  assert.ok(-parts.at(-1).position[2] > 6.5);
  assert.ok(Math.abs(parts.at(-1).position[1] + 0.065 - 3.23) < 1e-10);
});

test("presentation furniture cannot spill outside small clear rooms", () => {
  const polygon = [
    [0, 0],
    [2.3, 0],
    [2.3, 2.2],
    [0, 2.2],
    [0, 0],
  ];
  for (const use of [
    "bedroom",
    "living",
    "family",
    "study",
    "dining",
    "kitchen",
    "bathroom",
    "roof_terrace",
  ]) {
    const parts = furnishingParts(
      {
        id: "r",
        level_id: "g",
        use,
        name: use,
        classification: "principal",
        polygon,
      },
      polygon,
    );
    for (const part of parts) {
      assert.ok(part.position[0] - part.size[0] / 2 >= 0);
      assert.ok(part.position[0] + part.size[0] / 2 <= 2.3);
      assert.ok(-part.position[2] - part.size[2] / 2 >= 0);
      assert.ok(-part.position[2] + part.size[2] / 2 <= 2.2);
    }
  }
});

test("3D handles expose only domain-supported shared principal-room partitions", () => {
  const room = (id, x, w, classification = "principal") => ({
    id,
    level_id: "g",
    name: id,
    use: "living",
    classification,
    polygon: [
      [x, 0],
      [x + w, 0],
      [x + w, 4],
      [x, 4],
      [x, 0],
    ],
  });
  const partition = {
    ...wall,
    id: "partition",
    start: [3, 0],
    end: [3, 4],
    space_ids: ["a", "b"],
  };
  const snapshot = {
    revision_id: "r",
    revision_number: 1,
    levels: [],
    spaces: [room("a", 0, 3), room("b", 3, 1.5)],
    architecture: {
      walls: [
        partition,
        { ...partition, id: "envelope", exterior: true },
        { ...partition, id: "horizontal", start: [0, 2], end: [3, 2] },
      ],
    },
  };
  assert.deepEqual(
    movablePartitions(snapshot, "a", "g").map((w) => w.id),
    ["partition"],
  );
  assert.equal(partitionMoveFits(snapshot, partition, 0.1), false);
  assert.equal(partitionMoveFits(snapshot, partition, -0.1), true);
  snapshot.spaces[1].classification = "support";
  assert.equal(movablePartitions(snapshot, "a", "g").length, 0);
});

test("raised roof, basement pool, exploded offsets and cutaway stairs determine model height", () => {
  const levels = [
    ["b", -3.2],
    ["g", 0],
    ["u", 3.4],
    ["new", 6.8],
    ["roof", 10.2],
  ].map(([id, elevation_m]) => ({ id, name: id, label: id, elevation_m }));
  const snapshot = {
    levels,
    spaces: [],
    pool: { level_id: "b", water_depth_m: 1.8 },
    architecture: {
      walls: levels.map((l) => ({
        ...wall,
        level_id: l.id,
        height_m: l.id === "roof" ? 2.6 : 3.15,
      })),
      slabs: [{ level_id: "roof", elevation_m: 13.05, thickness_m: 0.25 }],
      stairs: [
        { lower_level_id: "new", riser_count: 20, riser_height_m: 0.17 },
      ],
    },
  };
  assert.deepEqual(sceneVerticalBounds(snapshot, "building", "g"), {
    min: -0.25,
    max: 13.05,
    height: 13.3,
  });
  const exploded = sceneVerticalBounds(snapshot, "exploded", "new");
  assert.equal(exploded.min, -5);
  assert.equal(exploded.max, 27.05);
  const cutaway = sceneVerticalBounds(snapshot, "cutaway", "new");
  assert.ok(Math.abs(cutaway.min - 6.55) < 1e-10);
  assert.ok(Math.abs(cutaway.max - 10.2) < 1e-10);
});

test("camera contains all eight model corners at three and twelve floors on desktop and mobile", async () => {
  // Independently project each corner using the actual three.js camera basis.
  const { Vector3, Matrix4 } = await import("three");
  const bounds = { width: 18, depth: 15.5 };
  for (const max of [13.05, 58, 103.5])
    for (const [width, height] of [
      [980, 720],
      [390, 590],
    ]) {
      const vertical = { min: -5, max, height: max + 5 };
      const frame = orthographicFrame(bounds, vertical, width, height);
      const eye = new Vector3(27, 24, 32)
        .multiplyScalar(frame.distanceScale)
        .add(new Vector3(0, frame.targetY, 0));
      const target = new Vector3(0, frame.targetY, 0);
      const basis = new Matrix4().lookAt(eye, target, new Vector3(0, 1, 0));
      const right = new Vector3().setFromMatrixColumn(basis, 0),
        up = new Vector3().setFromMatrixColumn(basis, 1);
      for (const x of [-9, 9])
        for (const z of [-7.75, 7.75])
          for (const y of [vertical.min, vertical.max]) {
            const relative = new Vector3(x, y, z).sub(target);
            assert.ok(
              Math.abs(relative.dot(right) * frame.zoom) <= width * 0.44 + 1e-9,
            );
            assert.ok(
              Math.abs(relative.dot(up) * frame.zoom) <= height * 0.37 + 1e-9,
            );
            assert.ok(
              new Vector3(x, y, z)
                .sub(eye)
                .dot(new Vector3().subVectors(target, eye).normalize()) > 0,
            );
          }
    }
});
