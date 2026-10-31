import test from "node:test";
import assert from "node:assert/strict";
import { area, areaLabel, bounds, length } from "../app/lib/format.ts";
test("SI to customary preserves exact foot, inch and fractional carry", () => {
  assert.equal(length(0.3048, "imperial"), "1′ 0″");
  assert.equal(length(0.0254, "imperial"), "0′ 1″");
  assert.equal(length(0.3037, "imperial"), "1′ 0″");
  assert.equal(length(0.3048 * 5 + 0.0254 * 3.5, "imperial"), "5′ 3½″");
  assert.equal(length(2.15, "metric", true), "2.150 m");
  assert.equal(areaLabel(0.09290304, "imperial"), "1 ft²");
});
test("asymmetric translated polygon area does not depend on origin or winding", () => {
  const p = [
    [2, 7],
    [8, 7],
    [8, 10],
    [2, 10],
    [2, 7],
  ];
  assert.equal(area(p), 18);
  assert.equal(area(p.toReversed()), 18);
  assert.deepEqual(bounds(p), { x: 2, y: 7, w: 6, h: 3 });
});
