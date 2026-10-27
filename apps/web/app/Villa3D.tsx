"use client";
import { useEffect, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

export default function Villa3D({ snap, level }: { snap: any; level: string }) {
  // Force the WebGL drawing buffer to the measured panel size. Without this,
  // R3F can leave the buffer at the 300x150 canvas default in some browsers,
  // which CSS then stretches into a blurry image.
  const wrapRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<any>(null);
  const [size, setSize] = useState({ w: 760, h: 520 });
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => {
      const w = Math.max(300, el.clientWidth), h = 520;
      setSize({ w, h });
      // R3F only pushes size into the GL buffer when the size CHANGES after
      // its subscription registers; the initial size can be missed, leaving
      // the buffer at 300x150 (blurry when CSS-stretched). Nudge by 1px and
      // back to force the update through.
      const s = stateRef.current;
      if (s) {
        s.setSize(w - 1, h, 0, 0);
        requestAnimationFrame(() => s.setSize(w, h, 0, 0));
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const lvl = snap.levels.find((l: any) => l.name === level);
  const spaces = snap.spaces.filter((s: any) => s.level_id === lvl.id);
  return (
    <div ref={wrapRef} style={{ width: "100%", height: 520, position: "relative" }}>
      {snap.pool && level === "basement" && (
        <div style={{ position: "absolute", top: 10, left: 10, zIndex: 2, background: "rgba(10,18,26,0.82)",
                      color: "#a5f3fc", padding: "6px 10px", fontSize: 13, border: "1px solid #155e75" }}>
          Pool water {snap.pool.water_length_m} × {snap.pool.water_width_m} × {snap.pool.water_depth_m} m
          {" "}(bright slab on the hall block)
        </div>
      )}
      <Canvas camera={{ position: [16, 15, 16], fov: 50 }}
        style={{ width: size.w, height: size.h }}
        onCreated={(s) => {
          stateRef.current = s;
          const { width, height, top, left } = s.size;
          s.setSize(width - 1, height, top, left);
          requestAnimationFrame(() => s.setSize(width, height, top, left));
        }}
        gl={{ preserveDrawingBuffer: true, antialias: true }}>
        <color attach="background" args={["#1a222c"]} />
        <ambientLight intensity={1.2} />
        <directionalLight position={[10, 18, 8]} intensity={2} />
        <mesh position={[0, 0.2, 0]}>
          <boxGeometry args={[18, 0.4, 15.5]} />
          <meshStandardMaterial color="#3d4a5a" />
        </mesh>
        {spaces.map((s: any) => {
          const xs = s.polygon.map((p: number[]) => p[0]);
          const ys = s.polygon.map((p: number[]) => p[1]);
          const w = Math.max(...xs) - Math.min(...xs);
          const d = Math.max(...ys) - Math.min(...ys);
          const cx = (Math.min(...xs) + Math.max(...xs)) / 2 - 9;
          const cz = (Math.min(...ys) + Math.max(...ys)) / 2 - 7.75;
          const isPool = s.use === "pool_hall";
          return (
            <mesh key={s.id} position={[cx, 1.9, -cz]}>
              <boxGeometry args={[Math.max(w - 0.06, 0.1), 3.0, Math.max(d - 0.06, 0.1)]} />
              <meshStandardMaterial color={isPool ? "#2b6cb0" : s.classification === "principal" ? "#d8c9a3" : "#8a919c"}
                transparent={isPool} opacity={isPool ? 0.45 : 1} />
            </mesh>
          );
        })}
        {snap.pool && level === "basement" && (
          <mesh position={[snap.pool.origin_x_m + snap.pool.water_length_m / 2 - 9, 3.55,
            -(snap.pool.origin_y_m + snap.pool.water_width_m / 2 - 7.75)]}>
            <boxGeometry args={[snap.pool.water_length_m, 0.35, snap.pool.water_width_m]} />
            <meshStandardMaterial color="#22d3ee" emissive="#0e7490" emissiveIntensity={0.7} />
          </mesh>
        )}
        <OrbitControls />
      </Canvas>
    </div>
  );
}
