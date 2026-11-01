"use client";
/* eslint-disable react-hooks/immutability -- Three.js owns mutable GPU scene, camera, and renderer objects; effects are their synchronization boundary. */

import {
  Component,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ComponentRef,
  type ReactNode,
} from "react";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import {
  modelBounds,
  boundsOf,
  sceneVerticalBounds,
  orthographicFrame,
  movablePartitions,
  partitionMoveFits,
  joinedWallParts,
  stairParts,
  furnishingParts,
  type BoxPart,
  type Bounds,
  type RenderLevel,
  type RenderSnapshot,
  type RenderWall,
  type Surface,
} from "./scene-model";

import { garageParts, waterPolygon, type SiteSurface } from "./site-model";
import { PROJECT_BOUNDARY_ID, projectBoundaryPolygon } from "./site-selection";

export type ModelView = "building" | "cutaway" | "exploded";
export interface Villa3DProps {
  snap: RenderSnapshot;
  level: string;
  selected?: string;
  onSelect?: (spaceId: string) => void;
  mode?: ModelView;
  materialMode?: "material" | "white";
  replayKey?: number;
  furnishings?: boolean;
  onMoveWall?: (wallId: string, offsetMetres: number) => void | Promise<void>;
  disabled?: boolean;
}

const SURFACES: Surface[] = [
  "stone",
  "plaster",
  "concrete",
  "glass",
  "metal",
  "timber",
  "linen",
  "water",
  "cap",
  "grass",
  "ground",
];
type Palette = Record<Surface, THREE.MeshStandardMaterial>;

function subscribeMotion(callback: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}
function motionSnapshot() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Self-contained presentation textures: no remote assets or provider requests. */
function surfaceTexture(kind: "stone" | "timber") {
  const size = 256,
    canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const pixels = ctx.createImageData(size, size);
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const noise =
        (((Math.sin(x * 127.1 + y * 311.7) * 43758.5453) % 1) + 1) % 1;
      const grain =
        kind === "timber"
          ? Math.sin(x * 0.44 + Math.sin(y * 0.026) * 3.4) * 8 +
            Math.sin(x * 1.7 + y * 0.014) * 3
          : Math.sin(x * 0.035 + y * 0.09) * 2;
      const seam = kind === "timber" && x % 64 < 1 ? -38 : 0;
      const n = noise * 10 + grain + seam;
      const rgb =
        kind === "timber"
          ? [144 + n, 117 + n, 86 + n]
          : [224 + n, 220 + n, 209 + n];
      pixels.data[i] = rgb[0];
      pixels.data[i + 1] = rgb[1];
      pixels.data[i + 2] = rgb[2];
      pixels.data[i + 3] = 255;
    }
  ctx.putImageData(pixels, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.repeat.set(
    kind === "timber" ? 0.7 : 0.3,
    kind === "timber" ? 0.7 : 0.3,
  );
  texture.anisotropy = 4;
  return texture;
}

function usePalette(
  white: boolean,
  paletteId: RenderSnapshot["material_palette"],
) {
  const palette = useMemo(() => {
    const stone = white ? null : surfaceTexture("stone"),
      timber = white ? null : surfaceTexture("timber");
    const warm = paletteId === "warm_concrete",
      stucco = paletteId === "white_stucco";
    const solid = (
      color: string,
      roughness = 0.8,
      map: THREE.Texture | null = null,
    ) =>
      new THREE.MeshStandardMaterial({
        color: white ? "#eeeae0" : color,
        roughness,
        map,
        envMapIntensity: 0.4,
      });
    return {
      stone: solid(
        stucco ? "#f3f0e7" : warm ? "#c3bdb0" : "#eee9dc",
        0.82,
        stone,
      ),
      plaster: solid(stucco ? "#fcfbf5" : "#f2f0e9"),
      concrete: solid(warm ? "#b8aa97" : "#b7b5aa", 0.86, stone),
      metal: new THREE.MeshStandardMaterial({
        color: white
          ? "#b3b2ad"
          : warm
            ? "#5a493b"
            : stucco
              ? "#232d2e"
              : "#323b38",
        roughness: 0.48,
        metalness: 0.65,
        envMapIntensity: 0.65,
      }),
      glass: new THREE.MeshStandardMaterial({
        color: white ? "#d4dddd" : "#88b1b1",
        roughness: 0.12,
        metalness: 0.22,
        transparent: true,
        opacity: 0.32,
        depthWrite: false,
        side: THREE.DoubleSide,
        envMapIntensity: 1.1,
      }),
      timber: solid(
        warm ? "#9e7857" : stucco ? "#d9c5a2" : "#d1b590",
        0.68,
        timber,
      ),
      linen: solid(warm ? "#d6c9b7" : "#e9e3d5", 0.98),
      water: new THREE.MeshStandardMaterial({
        color: "#5caaa8",
        roughness: 0.16,
        metalness: 0.25,
        transparent: true,
        opacity: 0.78,
        envMapIntensity: 0.8,
      }),
      cap: solid("#7c8277", 0.8),
      grass: solid("#849367", 1),
      ground: solid("#e9e9e1", 1),
    } satisfies Palette;
  }, [white, paletteId]);
  useEffect(
    () => () => {
      const textures = new Set<THREE.Texture>();
      Object.values(palette).forEach((material) => {
        if (material.map) textures.add(material.map);
        material.dispose();
      });
      textures.forEach((texture) => texture.dispose());
    },
    [palette],
  );
  return palette;
}

function Environment({ top, span }: { top: number; span: number }) {
  const { gl, scene, invalidate } = useThree();
  useEffect(() => {
    const room = new RoomEnvironment(),
      generator = new THREE.PMREMGenerator(gl);
    const target = generator.fromScene(room, 0.04);
    scene.environment = target.texture;
    scene.environmentIntensity = 0.55;
    room.dispose();
    generator.dispose();
    invalidate();
    return () => {
      scene.environment = null;
      target.dispose();
    };
  }, [gl, scene, invalidate]);
  return (
    <>
      <hemisphereLight args={["#f4f6ed", "#9b927f", 1.15]} />
      <directionalLight
        castShadow
        position={[-14, top + 24, 15]}
        intensity={3.2}
        color="#fff5dc"
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0003}
        shadow-normalBias={0.035}
        shadow-camera-left={-Math.max(24, span)}
        shadow-camera-right={Math.max(24, span)}
        shadow-camera-top={Math.max(24, span)}
        shadow-camera-bottom={-Math.max(24, span)}
        shadow-camera-near={1}
        shadow-camera-far={Math.max(75, top + span + 50)}
      />
      <directionalLight
        position={[15, 10, -18]}
        intensity={1.15}
        color="#dbe8ef"
      />
    </>
  );
}

function Boxes({
  parts,
  material,
  selected,
  onSelect,
}: {
  parts: BoxPart[];
  material: THREE.Material;
  selected?: string;
  onSelect?: (id: string) => void;
}) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const { gl, invalidate } = useThree();
  useEffect(
    () => () => {
      gl.domElement.style.cursor = "grab";
    },
    [gl],
  );
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const dummy = new THREE.Object3D(),
      color = new THREE.Color();
    parts.forEach((part, index) => {
      dummy.position.set(...part.position);
      dummy.rotation.set(0, part.yaw, 0);
      dummy.scale.set(...part.size);
      dummy.updateMatrix();
      mesh.setMatrixAt(index, dummy.matrix);
      color.set(
        part.objectId && part.objectId === selected ? "#b1c991" : "#ffffff",
      );
      mesh.setColorAt(index, color);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
    invalidate();
  }, [parts, selected, invalidate]);
  if (!parts.length) return null;
  const pick = (event: ThreeEvent<MouseEvent>) => {
    const objectId = parts[event.instanceId ?? -1]?.objectId;
    if (objectId) {
      event.stopPropagation();
      if (event.delta <= 5) onSelect?.(objectId);
    }
  };
  return (
    <instancedMesh
      ref={ref}
      args={[undefined, material, parts.length]}
      castShadow={!material.transparent}
      receiveShadow
      onClick={pick}
      onPointerOver={(e) => {
        if (parts[e.instanceId ?? -1]?.objectId) {
          e.stopPropagation();
          gl.domElement.style.cursor = "pointer";
        }
      }}
      onPointerOut={() => {
        gl.domElement.style.cursor = "grab";
      }}
    >
      <boxGeometry args={[1, 1, 1]} />
    </instancedMesh>
  );
}

function polygonShape(polygon: number[][], holes: number[][][] = []) {
  const shape = new THREE.Shape(
    polygon.map((point) => new THREE.Vector2(point[0], point[1])),
  );
  for (const ring of holes)
    shape.holes.push(
      new THREE.Path(
        ring.map((point) => new THREE.Vector2(point[0], point[1])),
      ),
    );
  return shape;
}

function PlanarSurface({
  polygon,
  holes = [],
  depth = 0,
  y = 0,
  material,
  onClick,
}: {
  polygon: number[][];
  holes?: number[][][];
  depth?: number;
  y?: number;
  material: THREE.Material;
  onClick?: (event: ThreeEvent<MouseEvent>) => void;
}) {
  const geometry = useMemo(() => {
    const shape = polygonShape(polygon, holes);
    return depth
      ? new THREE.ExtrudeGeometry(shape, {
          depth,
          bevelEnabled: false,
          steps: 1,
        })
      : new THREE.ShapeGeometry(shape);
  }, [polygon, holes, depth]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, y, 0]}
      geometry={geometry}
      material={material}
      castShadow={depth > 0}
      receiveShadow
      onClick={onClick}
    />
  );
}

function AnimatedLevel({
  children,
  elevation,
  index,
  reduced,
}: {
  children: ReactNode;
  elevation: number;
  index: number;
  reduced: boolean;
}) {
  const group = useRef<THREE.Group>(null),
    started = useRef<number | null>(null);
  useFrame(({ clock, invalidate }) => {
    if (!group.current) return;
    if (started.current === null) started.current = clock.elapsedTime;
    const elapsed = clock.elapsedTime - started.current - index * 0.12;
    const progress = reduced ? 1 : Math.min(1, Math.max(0, elapsed / 1.1));
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    group.current.scale.y = 0.025 + 0.975 * eased;
    group.current.position.y = elevation + (1 - eased) * 0.8;
    if (progress < 1) invalidate();
  });
  return (
    <group ref={group} position={[0, elevation, 0]}>
      {children}
    </group>
  );
}

function Floor({
  snapshot,
  level,
  clip,
  materials,
  selected,
  onSelect,
  furnishings,
}: {
  snapshot: RenderSnapshot;
  level: RenderLevel;
  clip: boolean;
  materials: Palette;
  selected?: string;
  onSelect?: (id: string) => void;
  furnishings: boolean;
}) {
  const architecture = snapshot.architecture;
  const parts = useMemo(() => {
    if (!architecture) return [];
    const walls = architecture.walls.filter((w) => w.level_id === level.id);
    const result = joinedWallParts(
      walls,
      architecture.openings,
      clip ? 1.15 : undefined,
    );
    result.push(
      ...architecture.stairs
        .filter((s) => s.lower_level_id === level.id)
        .flatMap(stairParts),
    );
    if (furnishings)
      for (const space of snapshot.spaces.filter(
        (s) => s.level_id === level.id,
      )) {
        result.push(
          ...furnishingParts(
            space,
            architecture.space_metrics.find((m) => m.space_id === space.id)
              ?.clear_polygon,
          ),
        );
      }
    return result;
  }, [architecture, level.id, snapshot.spaces, clip, furnishings]);
  const batches = useMemo(
    () =>
      SURFACES.map((surface) => ({
        surface,
        parts: parts.filter((p) => p.surface === surface),
      })),
    [parts],
  );
  const selectedMaterial = useMemo(
    () => new THREE.MeshStandardMaterial({ color: "#b8c4a1", roughness: 0.9 }),
    [],
  );
  useEffect(() => () => selectedMaterial.dispose(), [selectedMaterial]);
  if (!architecture) return null;
  const pool =
    snapshot.pool?.location !== "outdoor" &&
    snapshot.pool?.level_id === level.id
      ? snapshot.pool
      : null;
  return (
    <>
      {architecture.slabs
        .filter(
          (s) =>
            s.level_id === level.id &&
            (!clip ||
              (s.elevation_m ?? level.elevation_m) <= level.elevation_m + 1.15),
        )
        .map((slab) => (
          <PlanarSurface
            key={slab.id}
            polygon={slab.polygon}
            holes={slab.holes}
            depth={slab.thickness_m}
            y={
              (slab.elevation_m ?? level.elevation_m) -
              level.elevation_m -
              slab.thickness_m
            }
            material={materials.concrete}
          />
        ))}
      {snapshot.spaces
        .filter((s) => s.level_id === level.id)
        .map((space) => {
          const metric = architecture.space_metrics.find(
            (m) => m.space_id === space.id,
          );
          const wood = [
            "bedroom",
            "living",
            "family",
            "library",
            "study",
            "roof_terrace",
          ].includes(space.use);
          const polygon = metric?.clear_polygon?.length
            ? metric.clear_polygon
            : space.polygon;
          const holes =
            pool && space.use === "pool_hall"
              ? [
                  [
                    [pool.origin_x_m, pool.origin_y_m],
                    [pool.origin_x_m + pool.water_length_m, pool.origin_y_m],
                    [
                      pool.origin_x_m + pool.water_length_m,
                      pool.origin_y_m + pool.water_width_m,
                    ],
                    [pool.origin_x_m, pool.origin_y_m + pool.water_width_m],
                    [pool.origin_x_m, pool.origin_y_m],
                  ],
                ]
              : [];
          if (space.use === "stairs_service") return null;
          return (
            <PlanarSurface
              key={space.id}
              polygon={polygon}
              holes={holes}
              y={0.014}
              material={
                space.id === selected
                  ? selectedMaterial
                  : wood
                    ? materials.timber
                    : materials.stone
              }
              onClick={(e) => {
                e.stopPropagation();
                if (e.delta <= 5) onSelect?.(space.id);
              }}
            />
          );
        })}
      {batches.map((batch) => (
        <Boxes
          key={batch.surface}
          parts={batch.parts}
          material={materials[batch.surface]}
          selected={selected}
          onSelect={onSelect}
        />
      ))}
      {pool && (
        <mesh
          position={[
            pool.origin_x_m + pool.water_length_m / 2,
            -pool.water_depth_m / 2,
            -pool.origin_y_m - pool.water_width_m / 2,
          ]}
          material={materials.water}
          receiveShadow
        >
          <boxGeometry
            args={[pool.water_length_m, pool.water_depth_m, pool.water_width_m]}
          />
        </mesh>
      )}
    </>
  );
}

/** Select the actual surface mesh: its holes remain open to deck/water picking. */
function SelectableSiteObject({
  id,
  onSelect,
  children,
}: {
  id: string;
  onSelect?: (id: string) => void;
  children: ReactNode;
}) {
  const { gl } = useThree();
  useEffect(
    () => () => {
      gl.domElement.style.cursor = "grab";
    },
    [gl],
  );
  return (
    <group
      onClick={(event) => {
        event.stopPropagation();
        // OrbitControls also starts on these meshes; a drag is not a pick.
        if (event.delta <= 5) onSelect?.(id);
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        gl.domElement.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        gl.domElement.style.cursor = "grab";
      }}
    >
      {children}
    </group>
  );
}

function SiteOutline({
  polygon,
  holes = [],
  elevation,
  boundary = false,
  selected = true,
}: {
  polygon: number[][];
  holes?: number[][][];
  elevation: number;
  boundary?: boolean;
  selected?: boolean;
}) {
  const rings = useMemo(
    () =>
      [polygon, ...holes].map((ring) => {
        if (ring.length < 3) return [];
        const closed =
          ring[0][0] === ring.at(-1)![0] && ring[0][1] === ring.at(-1)![1]
            ? ring
            : [...ring, ring[0]];
        return closed.map(
          ([x, y]) => [x, elevation, -y] as [number, number, number],
        );
      }),
    [polygon, holes, elevation],
  );
  return rings
    .filter((ring) => ring.length > 2)
    .map((points, index) => (
      <Line
        key={index}
        points={points}
        color={selected ? "#345f42" : "#697c69"}
        lineWidth={selected ? 2.5 : 1.6}
        dashed={boundary}
        dashSize={0.65}
        gapSize={0.32}
        // Palette edits replace the ground material. Draw annotation lines
        // after opaque surfaces regardless of material creation order.
        renderOrder={2}
        depthWrite={false}
        toneMapped={false}
      />
    ));
}

function SelectableSiteSurface({
  surface,
  material,
  selected,
  onSelect,
}: {
  surface: SiteSurface;
  material: THREE.Material;
  selected?: string;
  onSelect?: (id: string) => void;
}) {
  return (
    <SelectableSiteObject id={surface.id} onSelect={onSelect}>
      <PlanarSurface
        polygon={surface.polygon}
        holes={surface.holes}
        y={surface.elevation_m}
        material={material}
      />
      {selected === surface.id && (
        <SiteOutline
          polygon={surface.polygon}
          holes={surface.holes}
          elevation={surface.elevation_m + 0.025}
        />
      )}
    </SelectableSiteObject>
  );
}

function SiteModel({
  snap,
  materials,
  cutaway,
  replayKey,
  reduced,
  selected,
  onSelect,
}: {
  snap: RenderSnapshot;
  materials: Palette;
  cutaway: boolean;
  replayKey: number;
  reduced: boolean;
  selected?: string;
  onSelect?: (id: string) => void;
}) {
  const site = snap.site_layout;
  const parts = useMemo(
    () =>
      site?.garage
        ? garageParts(site.garage, cutaway).map((part) => ({
            ...part,
            objectId: site.garage!.id,
          }))
        : [],
    [site, cutaway],
  );
  if (!site) return null;
  const pool = snap.pool?.location === "outdoor" ? snap.pool : null;
  const ground = snap.levels.find((l) => l.name === "ground")?.elevation_m ?? 0;
  return (
    <>
      {site.yard && (
        <SelectableSiteSurface
          surface={site.yard}
          material={materials.grass}
          selected={selected}
          onSelect={onSelect}
        />
      )}
      {site.driveway && (
        <SelectableSiteSurface
          surface={site.driveway}
          material={materials.concrete}
          selected={selected}
          onSelect={onSelect}
        />
      )}
      {site.pool_deck && (
        <SelectableSiteSurface
          surface={site.pool_deck}
          material={materials.stone}
          selected={selected}
          onSelect={onSelect}
        />
      )}
      {pool && (
        <SelectableSiteObject id={pool.id ?? "site-pool"} onSelect={onSelect}>
          <PlanarSurface
            polygon={waterPolygon(pool)}
            y={ground - pool.water_depth_m}
            material={materials.stone}
          />
          <mesh
            material={materials.water}
            position={[
              pool.origin_x_m + pool.water_length_m / 2,
              ground - pool.water_depth_m / 2,
              -pool.origin_y_m - pool.water_width_m / 2,
            ]}
            receiveShadow
          >
            <boxGeometry
              args={[
                pool.water_length_m,
                pool.water_depth_m,
                pool.water_width_m,
              ]}
            />
          </mesh>
          {selected === (pool.id ?? "site-pool") && (
            <SiteOutline
              polygon={waterPolygon(pool)}
              elevation={ground + 0.025}
            />
          )}
        </SelectableSiteObject>
      )}
      {site.garage && (
        <AnimatedLevel
          key={`garage-${snap.revision_id}-${replayKey}-${cutaway}`}
          elevation={0}
          index={1}
          reduced={reduced}
        >
          {SURFACES.map((surface) => (
            <Boxes
              key={surface}
              parts={parts.filter((part) => part.surface === surface)}
              material={materials[surface]}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
          {selected === site.garage.id && (
            <SiteOutline
              polygon={site.garage.polygon}
              elevation={
                site.garage.elevation_m +
                (cutaway
                  ? Math.min(1.15, site.garage.height_m)
                  : site.garage.height_m + site.garage.roof_thickness_m) +
                0.025
              }
            />
          )}
        </AnimatedLevel>
      )}
    </>
  );
}

function CameraRig({
  rearView = false,
  bounds,
  vertical,
  resetKey,
  zoomRequest,
}: {
  rearView?: boolean;
  bounds: Bounds;
  vertical: { min: number; max: number; height: number };
  resetKey: number;
  zoomRequest: number;
}) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const { camera, size, invalidate } = useThree();
  const {
    zoom: baseZoom,
    targetY,
    distanceScale,
  } = orthographicFrame(bounds, vertical, size.width, size.height);
  useEffect(() => {
    camera.position.set(
      27 * distanceScale,
      targetY + 24 * distanceScale,
      (rearView ? -32 : 32) * distanceScale,
    );
    controls.current?.target.set(0, targetY, 0);
    controls.current?.update();
    invalidate();
  }, [camera, invalidate, resetKey, targetY, distanceScale, rearView]);
  useEffect(() => {
    if (camera instanceof THREE.OrthographicCamera) {
      camera.zoom = baseZoom * Math.pow(1.18, zoomRequest);
      camera.far = Math.max(250, 160 * distanceScale);
      camera.updateProjectionMatrix();
      invalidate();
    }
  }, [camera, invalidate, baseZoom, zoomRequest, distanceScale]);
  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping
      dampingFactor={0.09}
      target={[0, targetY, 0]}
      maxPolarAngle={Math.PI * 0.485}
      minPolarAngle={0.12}
      minZoom={baseZoom * 0.45}
      maxZoom={baseZoom * 5}
      rotateSpeed={0.65}
      panSpeed={0.65}
      zoomSpeed={0.8}
    />
  );
}

function PartitionHandle({
  snapshot,
  wall,
  elevation,
  disabled,
  onMove,
  portalElement,
}: {
  snapshot: RenderSnapshot;
  wall: RenderWall;
  elevation: number;
  disabled: boolean;
  onMove: NonNullable<Villa3DProps["onMoveWall"]>;
  portalElement: HTMLDivElement;
}) {
  const pending = useRef(false),
    [working, setWorking] = useState(false),
    [failed, setFailed] = useState(false);
  const portal = useMemo(() => ({ current: portalElement }), [portalElement]);
  async function move(offset: number) {
    if (
      disabled ||
      pending.current ||
      !partitionMoveFits(snapshot, wall, offset)
    )
      return;
    pending.current = true;
    setWorking(true);
    setFailed(false);
    try {
      await onMove(wall.id, offset);
    } catch {
      setFailed(true);
    } finally {
      pending.current = false;
      setWorking(false);
    }
  }
  return (
    <Html
      center
      portal={portal}
      style={{ pointerEvents: "auto" }}
      position={[
        (wall.start[0] + wall.end[0]) / 2,
        elevation + 1.6,
        -(wall.start[1] + wall.end[1]) / 2,
      ]}
      zIndexRange={[5, 0]}
    >
      <div
        className="partition-handle"
        onPointerDown={(event) => event.stopPropagation()}
        style={{
          background: "#fbfcf7",
          color: "#354730",
          boxShadow: "0 5px 22px #233b2629",
          borderRadius: 8,
          padding: "5px 6px",
          whiteSpace: "nowrap",
          fontSize: 10,
          textAlign: "center",
          minWidth: 126,
        }}
      >
        <div style={{ padding: "1px 4px 4px", fontSize: 9, color: "#61705b" }}>
          {working ? "Updating partition…" : "Shared partition · X axis"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {[-0.1, 0.1].map((offset) => (
            <button
              key={offset}
              type="button"
              aria-label={`Move shared partition ${offset < 0 ? "minus" : "plus"} 0.1 metres along X`}
              title="Validated 0.1 m partition edit; updates both adjacent rooms"
              disabled={
                disabled ||
                working ||
                !partitionMoveFits(snapshot, wall, offset)
              }
              onClick={() => void move(offset)}
              style={{
                minHeight: 28,
                minWidth: 60,
                padding: "4px 6px",
                borderRadius: 4,
                background: "#e8eedf",
                color: "#345135",
                fontSize: 10,
              }}
            >
              {offset < 0 ? "−100 mm" : "+100 mm"}
            </button>
          ))}
        </div>
        {failed && (
          <div role="status" style={{ fontSize: 9, paddingTop: 4 }}>
            Move rejected. Revision kept.
          </div>
        )}
      </div>
    </Html>
  );
}

function Scene({
  snap,
  level,
  selected,
  onSelect,
  onMoveWall,
  disabled = false,
  mode = "building",
  materialMode = "material",
  replayKey = 0,
  furnishings = true,
  resetKey,
  zoomRequest,
  reduced,
  portalElement,
  rearView,
}: Villa3DProps & {
  resetKey: number;
  zoomRequest: number;
  rearView: boolean;
  reduced: boolean;
  portalElement: HTMLDivElement | null;
}) {
  const materials = usePalette(materialMode === "white", snap.material_palette);
  const active = snap.levels.find((l) => l.name === level) ?? snap.levels[0];
  const showSite = mode !== "cutaway" || active.name === "ground";
  const boundary = useMemo(() => projectBoundaryPolygon(snap), [snap]);
  const bounds = useMemo(
    () =>
      showSite && boundary.length
        ? boundsOf(boundary)
        : modelBounds(snap, false),
    [snap, showSite, boundary],
  );
  const outdoorWater =
    showSite && snap.pool?.location === "outdoor" ? snap.pool : null;
  const orderedLevels = [...snap.levels].sort(
    (a, b) => a.elevation_m - b.elevation_m,
  );
  const vertical = sceneVerticalBounds(snap, mode, active.id);
  const levels = orderedLevels.filter(
    (l) =>
      mode === "exploded" ||
      (mode === "cutaway" ? l.id === active.id : l.elevation_m >= 0),
  );
  return (
    <>
      <color attach="background" args={["#e9e9e1"]} />
      <fog
        attach="fog"
        args={[
          "#e9e9e1",
          75 + vertical.height * 2 + Math.max(bounds.width, bounds.depth),
          140 + vertical.height * 3 + Math.max(bounds.width, bounds.depth),
        ]}
      />
      <Environment
        top={vertical.max}
        span={Math.max(vertical.height, bounds.width, bounds.depth)}
      />
      {outdoorWater ? (
        <PlanarSurface
          polygon={[
            [-110, -110],
            [110, -110],
            [110, 110],
            [-110, 110],
            [-110, -110],
          ]}
          holes={[
            waterPolygon(outdoorWater).map((p) => [
              p[0] - bounds.cx,
              p[1] - bounds.cy,
            ]),
          ]}
          y={-0.38}
          material={materials.ground}
        />
      ) : (
        <mesh
          rotation={[-Math.PI / 2, 0, 0]}
          position={[
            0,
            mode === "cutaway"
              ? active.elevation_m -
                (snap.pool?.level_id === active.id
                  ? snap.pool.water_depth_m + 0.2
                  : 0.4)
              : mode === "exploded"
                ? vertical.min - 0.15
                : -0.38,
            0,
          ]}
          receiveShadow
        >
          <planeGeometry args={[220, 220]} />
          <meshStandardMaterial color="#e9e9e1" roughness={1} />
        </mesh>
      )}
      <group position={[-bounds.cx, 0, bounds.cy]}>
        {showSite && boundary.length > 2 && (
          <SelectableSiteObject id={PROJECT_BOUNDARY_ID} onSelect={onSelect}>
            <SiteOutline
              polygon={boundary}
              elevation={
                (snap.levels.find((floor) => floor.name === "ground")
                  ?.elevation_m ?? 0) - 0.35
              }
              boundary
              selected={selected === PROJECT_BOUNDARY_ID}
            />
          </SelectableSiteObject>
        )}
        {showSite && (
          <SiteModel
            snap={snap}
            materials={materials}
            cutaway={mode === "cutaway"}
            replayKey={replayKey}
            reduced={reduced}
            selected={selected}
            onSelect={onSelect}
          />
        )}
        {levels.map((floor, index) => {
          const originalIndex = orderedLevels.findIndex(
            (l) => l.id === floor.id,
          );
          const elevation =
            floor.elevation_m + (mode === "exploded" ? originalIndex * 3.5 : 0);
          return (
            <AnimatedLevel
              key={`${floor.id}-${snap.revision_id}-${replayKey}-${mode}`}
              elevation={elevation}
              index={index}
              reduced={reduced}
            >
              <Floor
                snapshot={snap}
                level={floor}
                clip={mode === "cutaway"}
                materials={materials}
                selected={selected}
                onSelect={onSelect}
                furnishings={furnishings}
              />
            </AnimatedLevel>
          );
        })}
        {portalElement &&
          mode === "cutaway" &&
          selected &&
          onMoveWall &&
          movablePartitions(snap, selected, active.id).map((wall) => (
            <PartitionHandle
              key={`${wall.id}-${snap.revision_id}`}
              snapshot={snap}
              wall={wall}
              elevation={active.elevation_m}
              disabled={disabled}
              onMove={onMoveWall}
              portalElement={portalElement}
            />
          ))}
      </group>
      <CameraRig
        rearView={showSite && rearView}
        bounds={bounds}
        vertical={vertical}
        resetKey={resetKey}
        zoomRequest={zoomRequest}
      />
    </>
  );
}

class SceneBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="scene-unavailable" role="status">
        The 3D view could not start. Use the 2D plan, or reload with WebGL
        enabled.
      </div>
    ) : (
      this.props.children
    );
  }
}

function CameraIcon({ kind }: { kind: "home" | "plus" | "minus" | "turn" }) {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {kind === "turn" ? (
        <path d="M20 7h-6m6 0V2m0 5a9 9 0 1 0 1 10" />
      ) : kind === "home" ? (
        <>
          <path d="m3 10 9-7 9 7v10H3Z" />
          <path d="M9 20v-7h6v7" />
        </>
      ) : (
        <>
          <path d="M5 12h14" />
          {kind === "plus" && <path d="M12 5v14" />}
        </>
      )}
    </svg>
  );
}

export default function Villa3D(props: Villa3DProps) {
  const [resetKey, setResetKey] = useState(0),
    [zoomRequest, setZoomRequest] = useState(0);
  const [rearOverride, setRearOverride] = useState<boolean | null>(null);
  const rearView = !!props.snap.site_layout?.yard && (rearOverride ?? true);
  const active =
    props.snap.levels.find((floor) => floor.name === props.level) ??
    props.snap.levels[0];
  const showSite = props.mode !== "cutaway" || active?.name === "ground";
  // R3F mounts its scene in a separate React root. Wait for our own attached
  // portal instead of letting Drei capture a transient Canvas event target.
  // This also preserves handles when Documents unmounts and remounts the model.
  const [portalElement, setPortalElement] = useState<HTMLDivElement | null>(
    null,
  );
  const reduced = useSyncExternalStore(
    subscribeMotion,
    motionSnapshot,
    () => true,
  );
  if (
    !props.snap.architecture ||
    props.snap.architecture.revision_id !== props.snap.revision_id
  )
    return (
      <div className="scene-unavailable" role="status">
        Architectural geometry is not available for this revision. The 2D room
        plan remains available.
      </div>
    );
  return (
    <div
      className="villa-scene"
      style={{
        width: "100%",
        height: "100%",
        minHeight: 440,
        position: "relative",
      }}
      aria-label={`Interactive building model, revision ${props.snap.revision_number}`}
    >
      <SceneBoundary>
        <Canvas
          orthographic
          shadows
          dpr={[1, 1.75]}
          frameloop="demand"
          camera={{ position: [27, 27, 32], zoom: 22, near: 0.1, far: 250 }}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: "high-performance",
            preserveDrawingBuffer: true,
          }}
          onCreated={({ gl }) => {
            gl.toneMapping = THREE.ACESFilmicToneMapping;
            gl.toneMappingExposure = 1.05;
            gl.domElement.style.cursor = "grab";
          }}
          fallback={
            <div className="scene-unavailable">
              3D requires WebGL. You can continue with the 2D plan.
            </div>
          }
        >
          <Scene
            {...props}
            resetKey={resetKey}
            zoomRequest={zoomRequest}
            reduced={reduced}
            portalElement={portalElement}
            rearView={rearView}
          />
        </Canvas>
      </SceneBoundary>
      <div
        ref={setPortalElement}
        className="scene-handle-layer"
        data-testid="scene-handle-layer"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 5,
        }}
      />
      <div
        className="scene-camera-controls"
        onPointerDown={(event) => event.stopPropagation()}
        onPointerUp={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
        onDoubleClick={(event) => event.stopPropagation()}
        onWheel={(event) => event.stopPropagation()}
        style={{
          position: "absolute",
          right: 18,
          top: "50%",
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: 2,
          background: "#fafbf5",
          padding: 4,
          borderRadius: 10,
          boxShadow: "0 4px 16px #323b3814",
        }}
      >
        <button
          type="button"
          aria-label="Reset 3D camera"
          title="Reset camera"
          onClick={() => {
            setResetKey((k) => k + 1);
            setZoomRequest(0);
          }}
        >
          <CameraIcon kind="home" />
        </button>
        {props.snap.site_layout?.yard && (
          <button
            type="button"
            aria-label={rearView ? "View front of house" : "View backyard"}
            title={rearView ? "View front of house" : "View backyard"}
            onClick={() => setRearOverride(!rearView)}
          >
            <CameraIcon kind="turn" />
          </button>
        )}
        <button
          type="button"
          aria-label="Zoom in 3D"
          title="Zoom in"
          onClick={() => setZoomRequest((z) => Math.min(7, z + 1))}
        >
          <CameraIcon kind="plus" />
        </button>
        <button
          type="button"
          aria-label="Zoom out 3D"
          title="Zoom out"
          onClick={() => setZoomRequest((z) => Math.max(-4, z - 1))}
        >
          <CameraIcon kind="minus" />
        </button>
      </div>
      {showSite && (
        <button
          type="button"
          className="scene-boundary-control"
          aria-label="Inspect project boundary"
          aria-pressed={props.selected === PROJECT_BOUNDARY_ID}
          title="Modeled project extent; not a surveyed property boundary"
          onPointerDown={(event) => event.stopPropagation()}
          onPointerUp={(event) => event.stopPropagation()}
          onDoubleClick={(event) => event.stopPropagation()}
          onWheel={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            props.onSelect?.(PROJECT_BOUNDARY_ID);
          }}
          style={{
            position: "absolute",
            bottom: 118,
            left: 20,
            zIndex: 4,
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            padding: "7px 10px",
            border: "1px dashed #869781",
            borderRadius: 5,
            background:
              props.selected === PROJECT_BOUNDARY_ID ? "#e3ebdb" : "#fafbf5",
            color: "#3e5b43",
            fontSize: 11,
            lineHeight: 1.5,
          }}
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            aria-hidden="true"
          >
            <path d="M1.5 5V1.5H5m6 0h3.5V5m0 6v3.5H11m-6 0H1.5V11" />
          </svg>
          Project boundary · Assumed
        </button>
      )}
      <div
        className="scene-presentation-note"
        style={{
          position: "absolute",
          bottom: 92,
          left: 20,
          color: "#5b6259",
          fontSize: 10,
          lineHeight: 1.5,
          pointerEvents: "none",
        }}
      >
        Materials & furniture are illustrative
      </div>
    </div>
  );
}
