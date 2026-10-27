"use client";
import { Stage, Layer, Rect, Text, Group } from "react-konva";

const S = 28; // px per metre

export default function Plan2D({ snap, level, selected, onSelect }: any) {
  const lvl = snap.levels.find((l: any) => l.name === level);
  const spaces = snap.spaces.filter((s: any) => s.level_id === lvl.id);
  return (
    <Stage width={18 * S + 20} height={15.5 * S + 20} style={{ background: "#f7f5ef" }}>
      <Layer>
        {spaces.map((s: any) => {
          const xs = s.polygon.map((p: number[]) => p[0]);
          const ys = s.polygon.map((p: number[]) => p[1]);
          const x = Math.min(...xs), y = Math.min(...ys);
          const w = Math.max(...xs) - x, d = Math.max(...ys) - y;
          // canonical Y-up -> screen Y-down
          const sy = 15.5 - (y + d);
          return (
            <Group key={s.id}>
              <Rect x={10 + x * S} y={10 + sy * S} width={w * S} height={d * S}
                fill={selected === s.id ? "#f2c14e" : s.classification === "principal" ? "#e8eef7" : "#f3ead8"}
                stroke="#26303c" strokeWidth={1}
                onClick={() => onSelect(s.id)} onTap={() => onSelect(s.id)} />
              <Text x={10 + x * S + 4} y={10 + sy * S + d * S / 2 - 6} width={w * S - 8}
                text={s.name} fontSize={10} fill="#1c2733" align="center"
                onClick={() => onSelect(s.id)} />
            </Group>
          );
        })}
        {snap.pool && level === "basement" && (
          <>
            <Rect x={10 + snap.pool.origin_x_m * S}
              y={10 + (15.5 - (snap.pool.origin_y_m + snap.pool.water_width_m)) * S}
              width={snap.pool.water_length_m * S} height={snap.pool.water_width_m * S}
              stroke="#1d6fd1" strokeWidth={3} />
            <Text x={10 + snap.pool.origin_x_m * S + 6}
              y={10 + (15.5 - (snap.pool.origin_y_m + snap.pool.water_width_m)) * S + 6}
              text={`POOL WATER ${snap.pool.water_length_m} × ${snap.pool.water_width_m} m`} fontSize={11} fill="#1d6fd1" />
          </>
        )}
      </Layer>
    </Stage>
  );
}
