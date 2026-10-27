"use client";
import { useEffect, useRef, useState } from "react";
import { Stage, Layer, Rect, Text, Group } from "react-konva";

export default function Plan2D({ snap, level, selected, onSelect, onMove }: any) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [wrapW, setWrapW] = useState(524);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setWrapW(Math.max(300, Math.min(900, el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const S = (wrapW - 20) / 18; // px per metre, fits the 18 m plate to the panel
  const lvl = snap.levels.find((l: any) => l.name === level);
  const spaces = snap.spaces.filter((s: any) => s.level_id === lvl.id);
  return (
    <div ref={wrapRef} className="ns-plan-wrap">
      <Stage width={wrapW} height={15.5 * S + 20} style={{ background: "#f7f5ef", maxWidth: "100%" }}>
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
                  draggable={selected === s.id}
                  onDragEnd={(e: any) => {
                    const dx = (e.target.x() - (10 + x * S)) / S;
                    const dy = -((e.target.y() - (10 + sy * S)) / S);
                    e.target.position({ x: 10 + x * S, y: 10 + sy * S });
                    onMove && onMove(s.id, dx, dy);
                  }}
                  onClick={() => onSelect(s.id)} onTap={() => onSelect(s.id)} />
                <Text x={10 + x * S + 4} y={10 + sy * S + d * S / 2 - 6} width={Math.max(w * S - 8, 10)}
                  text={s.name} fontSize={Math.max(8, Math.min(11, S * 0.38))} fill="#1c2733" align="center"
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
                text={`POOL WATER ${snap.pool.water_length_m} × ${snap.pool.water_width_m} m`}
                fontSize={11} fill="#1d6fd1" />
            </>
          )}
        </Layer>
      </Stage>
    </div>
  );
}
