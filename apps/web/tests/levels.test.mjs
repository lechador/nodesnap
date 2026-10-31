import test from "node:test";
import assert from "node:assert/strict";
import { survivingFloor } from "../app/lib/levels.ts";

const previous = [
  ["ground", 0],
  ["upper", 3.4],
  ["level_3", 6.8],
  ["level_4", 10.2],
  ["roof", 13.6],
  ["basement", -3.2],
].map(([name, elevation_m]) => ({ name, elevation_m }));

test("removing the active top floor selects the nearest living floor below it", () => {
  const next = previous
    .filter((l) => l.name !== "level_4")
    .map((l) => (l.name === "roof" ? { ...l, elevation_m: 10.2 } : l));
  assert.equal(survivingFloor("level_4", previous, next), "level_3");
});

test("removing a middle floor preserves a surviving selected floor or selects below the removed one", () => {
  const next = previous
    .filter((l) => l.name !== "level_3")
    .map((l) => ({
      ...l,
      elevation_m: l.elevation_m >= 10.2 ? l.elevation_m - 3.4 : l.elevation_m,
    }));
  assert.equal(survivingFloor("level_3", previous, next), "upper");
  assert.equal(survivingFloor("level_4", previous, next), "level_4");
  assert.equal(survivingFloor("roof", previous, next), "roof");
});

test("unknown saved floor falls back to ground even when levels arrive unordered", () => {
  assert.equal(
    survivingFloor("removed-old-name", previous, [...previous].reverse()),
    "ground",
  );
});
