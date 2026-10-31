type Floor = { name: string; elevation_m: number };

/** Keep the current floor, or move below a removed floor without selecting the roof. */
export function survivingFloor(
  current: string,
  previous: readonly Floor[],
  next: readonly Floor[],
): string {
  if (next.some((level) => level.name === current)) return current;
  const old = previous.find((level) => level.name === current);
  const living = next
    .filter((level) => level.name !== "roof" && level.name !== "basement")
    .sort((a, b) => a.elevation_m - b.elevation_m);
  if (old) {
    // Use the old vertical order: higher surviving floors may have moved down
    // into the removed interval, with small floating-point coordinate changes.
    const below = previous
      .filter(
        (level) =>
          level.elevation_m < old.elevation_m &&
          living.some((survivor) => survivor.name === level.name),
      )
      .sort((a, b) => a.elevation_m - b.elevation_m)
      .at(-1);
    if (below) return below.name;
  }
  return (
    next.find((level) => level.name === "ground")?.name ??
    living[0]?.name ??
    next[0]?.name ??
    "ground"
  );
}
