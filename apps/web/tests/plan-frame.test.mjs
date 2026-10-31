import test from "node:test";
import assert from "node:assert/strict";
import { planFrame } from "../app/lib/plan-frame.ts";
const rect = (x, y, w, h) => [
  [x, y],
  [x + w, y],
  [x + w, y + h],
  [x, y + h],
  [x, y],
];
test("seed plan keeps its established scale and both outside dimensions", () => {
  const frame = planFrame(rect(0, 0, 18, 15.5));
  assert.equal(frame.scale, 35);
  assert.equal(frame.width, 18);
  assert.equal(frame.depth, 15.5);
  assert.equal(frame.left, 85);
  assert.equal(frame.top, 75);
});
test("small, wide and deep buildings fit the drawing and preserve metre distances", () => {
  for (const [w, h] of [
    [12, 10],
    [60, 8],
    [8, 60],
    [40, 35],
  ]) {
    const f = planFrame(rect(-7, 13, w, h));
    const xy = ([x, y]) => [f.X + x * f.scale, f.Y + (f.H - y) * f.scale];
    const origin = xy([-7, 13]),
      east = xy([-7 + w, 13]),
      north = xy([-7, 13 + h]);
    assert.ok(Math.abs((east[0] - origin[0]) / f.scale - w) < 1e-10);
    assert.ok(Math.abs((origin[1] - north[1]) / f.scale - h) < 1e-10);
    assert.ok(
      f.left >= 85 &&
        f.right <= 715 + 1e-9 &&
        f.top >= 75 &&
        f.bottom <= 617.5 + 1e-9,
    );
    assert.ok(f.barMetres * f.scale <= 280);
  }
});
test("plan transform does not invent dimensions for absent or invalid geometry", () => {
  assert.throws(() => planFrame([]));
  assert.throws(() => planFrame([[NaN, 0]]));
});
