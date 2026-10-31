import test from "node:test";
import assert from "node:assert/strict";
import {
  doorSwing,
  roomLabelLines,
  stairPlan,
} from "../app/lib/plan-details.ts";
import { planFrame } from "../app/lib/plan-frame.ts";
const rect = (x, y, w, h) => [
  [x, y],
  [x + w, y],
  [x + w, y + h],
  [x, y + h],
  [x, y],
];

test("large-building corridor labels stay within their clear height", () => {
  const { scale } = planFrame(rect(0, 0, 60, 60));
  const height = 1.45 * scale;
  const lines = roomLabelLines({
    name: "Main circulation",
    key: "R12",
    area: "132 m²",
    width: 45 * scale,
    height,
  });
  assert.deepEqual(
    lines.map((line) => line.text),
    ["R12"],
  );
  for (const line of lines) {
    assert.ok(line.y - line.size >= 0);
    assert.ok(line.y + line.size * 0.25 <= height);
  }
});

test("long room names become keys and dimensions appear only when space permits", () => {
  const lines = roomLabelLines({
    name: "WWWW".repeat(30),
    key: "R3",
    area: "12.5 m²",
    dimensions: "3.00 m × 4.17 m",
    width: 110,
    height: 100,
  });
  assert.equal(lines[0].text, "R3");
  assert.ok(lines.some((line) => line.kind === "area"));
  assert.ok(lines.some((line) => line.kind === "dimensions"));
  assert.deepEqual(
    roomLabelLines({
      name: "Store",
      key: "R20",
      area: "2 m²",
      width: 8,
      height: 7,
    }),
    [],
  );
  const compact = roomLabelLines({
    name: "Office",
    key: "R1",
    area: "12 m²",
    dimensions: "3 m × 4 m",
    width: 35,
    height: 20,
  });
  assert.equal(compact.length, 1);
  assert.equal(compact[0].text, "R1");
});

test("doors swing into the owning room using the declared start or end jamb", () => {
  const wall = { start: [0, 0], end: [10, 0] };
  const corridor = {
    id: "hall",
    use: "circulation",
    polygon: rect(0, -2, 10, 2),
  };
  const room = { id: "room", use: "bedroom", polygon: rect(0, 0, 10, 5) };
  const opening = {
    offset_m: 2,
    width_m: 0.9,
    hinge: "start",
    space_ids: ["hall", "room"],
  };
  assert.deepEqual(doorSwing(wall, opening, [corridor, room]), {
    hingeX: 0,
    closedX: 0.9,
    leafY: -0.9,
    sweep: 1,
  });
  assert.deepEqual(
    doorSwing(wall, { ...opening, hinge: "end" }, [corridor, room]),
    { hingeX: 0.9, closedX: 0, leafY: -0.9, sweep: 0 },
  );
  const southRoom = { ...room, polygon: rect(0, -5, 10, 5) };
  assert.deepEqual(doorSwing(wall, opening, [corridor, southRoom]), {
    hingeX: 0,
    closedX: 0.9,
    leafY: 0.9,
    sweep: 0,
  });
  assert.deepEqual(doorSwing(wall, { ...opening, hinge: "end" }, [southRoom]), {
    hingeX: 0.9,
    closedX: 0,
    leafY: 0.9,
    sweep: 1,
  });
  assert.equal(
    doorSwing({ start: [10, 0], end: [0, 0] }, opening, [room]).leafY,
    0.9,
  );
  const eastRoom = { ...room, polygon: rect(0, 0, 5, 10) };
  assert.equal(
    doorSwing({ start: [0, 0], end: [0, 10] }, opening, [eastRoom]).leafY,
    0.9,
  );
});

test("intermediate floors use outgoing risers and label both directions; bare roofs have no invented stair", () => {
  const lower = {
    id: "ground-upper",
    lower_level_id: "ground",
    upper_level_id: "upper",
    riser_count: 18,
  };
  const upper = {
    id: "upper-third",
    lower_level_id: "upper",
    upper_level_id: "third",
    riser_count: 24,
  };
  const stairs = [lower, upper];
  assert.deepEqual(stairPlan(stairs, "upper"), {
    stair: upper,
    direction: "UP / DN",
  });
  assert.deepEqual(stairPlan(stairs, "ground"), {
    stair: lower,
    direction: "UP",
  });
  assert.deepEqual(stairPlan(stairs, "third"), {
    stair: upper,
    direction: "DN",
  });
  assert.equal(stairPlan(stairs, "roof"), null);
});
