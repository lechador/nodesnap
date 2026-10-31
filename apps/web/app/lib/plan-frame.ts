/** Drawing-space transform; measurements always stay in canonical metres. */
export function planFrame(points: number[][]) {
  if (
    !points.length ||
    points.some(
      (p) => p.length < 2 || !Number.isFinite(p[0]) || !Number.isFinite(p[1]),
    )
  )
    throw new Error("A plan requires finite model coordinates.");
  const xs = points.map((p) => p[0]),
    ys = points.map((p) => p[1]);
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minY = Math.min(...ys),
    maxY = Math.max(...ys);
  const width = Math.max(0.1, maxX - minX),
    depth = Math.max(0.1, maxY - minY);
  const scale = Math.min(630 / width, 542.5 / depth);
  const left = 85 + (630 - width * scale) / 2,
    top = 75 + (542.5 - depth * scale) / 2;
  const barMetres = width > 35 ? 10 : width < 10 ? 2 : 5;
  return {
    scale,
    X: left - minX * scale,
    Y: top,
    H: maxY,
    left,
    top,
    width,
    depth,
    right: left + width * scale,
    bottom: top + depth * scale,
    barMetres,
  };
}
