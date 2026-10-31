import type { Point, Units } from "./types";
export function area(p: Point[]) {
  return (
    Math.abs(
      p.reduce((sum, a, i) => {
        const b = p[(i + 1) % p.length];
        return sum + a[0] * b[1] - b[0] * a[1];
      }, 0),
    ) / 2
  );
}
export function bounds(p: Point[]) {
  const xs = p.map((v) => v[0]),
    ys = p.map((v) => v[1]);
  const x = Math.min(...xs),
    y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}
export function length(m: number, units: Units, precise = false) {
  if (units === "metric") return `${m.toFixed(precise ? 3 : 2)} m`;
  const eighths = Math.round((m / 0.0254) * 8);
  const feet = Math.floor(eighths / 96);
  const rem = eighths % 96;
  const inch = Math.floor(rem / 8),
    fraction = rem % 8;
  const fractions = ["", "⅛", "¼", "⅜", "½", "⅝", "¾", "⅞"];
  return `${feet}′ ${inch}${fractions[fraction]}″`;
}
export function areaLabel(m: number, units: Units) {
  return `${(units === "metric" ? m : m / 0.09290304).toLocaleString("en-US", { maximumFractionDigits: 1 })} ${units === "metric" ? "m²" : "ft²"}`;
}
export function title(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}
export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
