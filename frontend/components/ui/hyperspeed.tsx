"use client";

import {
  BloomEffect,
  EffectComposer,
  EffectPass,
  RenderPass,
  SMAAEffect,
  SMAAPreset,
} from "postprocessing";
import { useEffect, useMemo, useRef, type CSSProperties } from "react";
import * as THREE from "three";

import { cn } from "@/lib/utils";

export type HyperspeedEffectOptions = {
  distortion?: "mountainDistortion" | "xyDistortion" | "longRaceDistortion" | "turbulentDistortion";
  length?: number;
  roadWidth?: number;
  islandWidth?: number;
  lanesPerRoad?: number;
  fov?: number;
  fovSpeedUp?: number;
  speedUp?: number;
  carLightsFade?: number;
  totalSideLightSticks?: number;
  lightPairsPerRoadWay?: number;
  shoulderLinesWidthPercentage?: number;
  brokenLinesWidthPercentage?: number;
  brokenLinesLengthPercentage?: number;
  lightStickWidth?: [number, number];
  lightStickHeight?: [number, number];
  movingAwaySpeed?: [number, number];
  movingCloserSpeed?: [number, number];
  carLightsLength?: [number, number];
  carLightsRadius?: [number, number];
  carWidthPercentage?: [number, number];
  carShiftX?: [number, number];
  carFloorSeparation?: [number, number];
  colors?: {
    roadColor?: number;
    islandColor?: number;
    background?: number;
    shoulderLines?: number;
    brokenLines?: number;
    leftCars?: number[];
    rightCars?: number[];
    sticks?: number;
  };
};

type HyperspeedProps = {
  className?: string;
  style?: CSSProperties;
  effectOptions?: HyperspeedEffectOptions;
};

type DistortionKey = NonNullable<HyperspeedEffectOptions["distortion"]>;

type ResolvedEffectOptions = Required<Omit<HyperspeedEffectOptions, "colors" | "distortion">> & {
  distortion: DistortionKey;
  colors: {
    roadColor: number;
    islandColor: number;
    background: number;
    shoulderLines: number;
    brokenLines: number;
    leftCars: number[];
    rightCars: number[];
    sticks: number;
  };
};

const DEFAULT_EFFECT_OPTIONS: ResolvedEffectOptions = {
  distortion: "turbulentDistortion",
  length: 400,
  roadWidth: 10,
  islandWidth: 2,
  lanesPerRoad: 4,
  fov: 90,
  fovSpeedUp: 150,
  speedUp: 2,
  carLightsFade: 0.4,
  totalSideLightSticks: 20,
  lightPairsPerRoadWay: 40,
  shoulderLinesWidthPercentage: 0.05,
  brokenLinesWidthPercentage: 0.1,
  brokenLinesLengthPercentage: 0.5,
  lightStickWidth: [0.12, 0.5],
  lightStickHeight: [1.3, 1.7],
  movingAwaySpeed: [60, 80],
  movingCloserSpeed: [-120, -160],
  carLightsLength: [12, 80],
  carLightsRadius: [0.05, 0.14],
  carWidthPercentage: [0.3, 0.5],
  carShiftX: [-0.8, 0.8],
  carFloorSeparation: [0, 5],
  colors: {
    roadColor: 0x080808,
    islandColor: 0x0a0a0a,
    background: 0x000000,
    shoulderLines: 0xffffff,
    brokenLines: 0xffffff,
    leftCars: [0xd856bf, 0x6750a2, 0xc247ac],
    rightCars: [0x03b3c3, 0x0e5ea5, 0x324555],
    sticks: 0x03b3c3,
  },
};

function randomBetween([min, max]: [number, number]) {
  return min + Math.random() * (max - min);
}

function resolveOptions(effectOptions?: HyperspeedEffectOptions): ResolvedEffectOptions {
  return {
    ...DEFAULT_EFFECT_OPTIONS,
    ...effectOptions,
    distortion: effectOptions?.distortion ?? DEFAULT_EFFECT_OPTIONS.distortion,
    colors: {
      ...DEFAULT_EFFECT_OPTIONS.colors,
      ...effectOptions?.colors,
      leftCars: effectOptions?.colors?.leftCars ?? DEFAULT_EFFECT_OPTIONS.colors.leftCars,
      rightCars: effectOptions?.colors?.rightCars ?? DEFAULT_EFFECT_OPTIONS.colors.rightCars,
    },
  };
}

function createRoadSurface(width: number, length: number, color: number) {
  const geometry = new THREE.PlaneGeometry(width, length, 1, 1);
  const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.97 });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.z = -length / 2;
  return mesh;
}

function createLightStick(color: number, side: number, options: ResolvedEffectOptions, index: number) {
  const height = randomBetween(options.lightStickHeight);
  const width = randomBetween(options.lightStickWidth);
  const geometry = new THREE.BoxGeometry(width, height, width);
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.7,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(
    side * (options.roadWidth + options.islandWidth * 0.5 + 2.8 + Math.random() * 1.8),
    height / 2,
    -index * (options.length / options.totalSideLightSticks),
  );
  mesh.userData.speed = randomBetween(options.movingAwaySpeed) * 0.72;
  return mesh;
}

function createCarLightTrail(
  color: number,
  side: number,
  options: ResolvedEffectOptions,
  zOffset: number,
  movingTowardCamera: boolean,
) {
  const length = randomBetween(options.carLightsLength);
  const radius = randomBetween(options.carLightsRadius);
  const width = Math.max(0.06, randomBetween(options.carWidthPercentage) * 0.32);
  const geometry = new THREE.BoxGeometry(width, radius, length);
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  const laneWidth = options.roadWidth / options.lanesPerRoad;
  const laneIndex = Math.floor(Math.random() * options.lanesPerRoad);
  const shiftX = randomBetween(options.carShiftX) * 0.2;
  const baseX = side * (options.islandWidth * 0.5 + laneWidth * (laneIndex + 0.5));
  mesh.position.set(
    baseX + shiftX,
    randomBetween(options.carFloorSeparation) * 0.02 + 0.2,
    zOffset,
  );
  mesh.userData.speed = movingTowardCamera
    ? Math.abs(randomBetween(options.movingCloserSpeed)) * options.speedUp
    : randomBetween(options.movingAwaySpeed) * options.speedUp;
  mesh.userData.reset = () => {
    mesh.position.z = movingTowardCamera
      ? -options.length - Math.random() * 120
      : -Math.random() * options.length;
  };
  return mesh;
}

function createBrokenLine(color: number, x: number, z: number, length: number) {
  const geometry = new THREE.BoxGeometry(0.08, 0.025, length);
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.82,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(x, 0.08, z);
  return mesh;
}

function applyDistortion(
  mesh: THREE.Object3D,
  time: number,
  key: DistortionKey,
  strength = 1,
) {
  if (key === "mountainDistortion") {
    mesh.rotation.z = Math.sin(time * 0.18) * 0.015 * strength;
    mesh.position.x = Math.sin(time * 0.22) * 0.3 * strength;
    return;
  }

  if (key === "xyDistortion") {
    mesh.rotation.z = Math.sin(time * 0.6) * 0.028 * strength;
    mesh.position.x = Math.sin(time * 0.8) * 0.45 * strength;
    return;
  }

  if (key === "longRaceDistortion") {
    mesh.rotation.z = Math.sin(time * 0.34) * 0.02 * strength;
    mesh.position.x = Math.sin(time * 0.16) * 0.22 * strength;
    return;
  }

  mesh.rotation.z = Math.sin(time * 1.2) * 0.035 * strength;
  mesh.position.x = Math.sin(time * 1.4) * 0.55 * strength;
}

export function Hyperspeed({ className, style, effectOptions }: HyperspeedProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const options = useMemo(() => resolveOptions(effectOptions), [effectOptions]);

  useEffect(() => {
    const containerElement = containerRef.current;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!containerElement || reducedMotion) return;

    while (containerElement.firstChild) {
      containerElement.removeChild(containerElement.firstChild);
    }

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(options.colors.background, 0);
    renderer.domElement.className = "hyperspeed-canvas";
    containerElement.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(options.colors.background, 18, options.length * 0.5);

    const camera = new THREE.PerspectiveCamera(options.fov, 1, 0.1, options.length * 2);
    camera.position.set(0, 6.3, 12);
    camera.rotation.x = -0.47;

    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(
      new EffectPass(
        camera,
        new BloomEffect({
          intensity: 1.9,
          luminanceThreshold: 0.02,
          luminanceSmoothing: 0.18,
        }),
        new SMAAEffect({ preset: SMAAPreset.HIGH }),
      ),
    );

    const leftRoad = createRoadSurface(options.roadWidth, options.length, options.colors.roadColor);
    leftRoad.position.x = -(options.islandWidth + options.roadWidth) / 2;
    const rightRoad = createRoadSurface(options.roadWidth, options.length, options.colors.roadColor);
    rightRoad.position.x = (options.islandWidth + options.roadWidth) / 2;
    const island = createRoadSurface(options.islandWidth, options.length, options.colors.islandColor);

    scene.add(leftRoad, rightRoad, island);

    const brokenLines: THREE.Mesh[] = [];
    const laneWidth = options.roadWidth / options.lanesPerRoad;
    const dashLength = options.length * options.brokenLinesLengthPercentage * 0.028;
    for (let i = 0; i < 28; i += 1) {
      for (let lane = 1; lane < options.lanesPerRoad; lane += 1) {
        const offset = options.islandWidth * 0.5 + laneWidth * lane;
        const z = -i * 14;
        const leftLine = createBrokenLine(options.colors.brokenLines, -offset, z, dashLength);
        const rightLine = createBrokenLine(options.colors.brokenLines, offset, z - 6, dashLength);
        brokenLines.push(leftLine, rightLine);
        scene.add(leftLine, rightLine);
      }
    }

    const shoulderLines = [-1, 1].flatMap((roadSide) => {
      const innerX = roadSide * (options.islandWidth * 0.5 + 0.04);
      const outerX = roadSide * (options.islandWidth * 0.5 + options.roadWidth + 0.04);
      const inner = createBrokenLine(options.colors.shoulderLines, innerX, -options.length * 0.4, options.length);
      const outer = createBrokenLine(options.colors.shoulderLines, outerX, -options.length * 0.4, options.length);
      inner.scale.x = 0.7;
      outer.scale.x = 0.9;
      scene.add(inner, outer);
      return [inner, outer];
    });

    const movingAway = Array.from({ length: options.lightPairsPerRoadWay * 2 }, (_, index) => {
      const side = index % 2 === 0 ? -1 : 1;
      const palette = side < 0 ? options.colors.leftCars : options.colors.rightCars;
      const color = palette[index % palette.length];
      const light = createCarLightTrail(color, side, options, -Math.random() * options.length, false);
      scene.add(light);
      return light;
    });

    const movingCloser = Array.from(
      { length: Math.max(18, Math.floor(options.lightPairsPerRoadWay * 0.72)) },
      (_, index) => {
        const side = index % 2 === 0 ? -1 : 1;
        const palette = side < 0 ? options.colors.rightCars : options.colors.leftCars;
        const color = palette[index % palette.length];
        const light = createCarLightTrail(color, side, options, -Math.random() * options.length, true);
        const material = light.material as THREE.MeshBasicMaterial;
        material.opacity = options.carLightsFade;
        scene.add(light);
        return light;
      },
    );

    const sticks = Array.from({ length: options.totalSideLightSticks * 3 }, (_, index) => {
      const side = index % 2 === 0 ? -1 : 1;
      const stick = createLightStick(options.colors.sticks, side, options, index);
      scene.add(stick);
      return stick;
    });

    const ambient = new THREE.AmbientLight(0xffffff, 0.18);
    scene.add(ambient);

    const mountNode = containerElement;

    function resize() {
      const width = Math.max(1, mountNode.clientWidth);
      const height = Math.max(1, mountNode.clientHeight);
      renderer.setSize(width, height, false);
      composer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    const clock = new THREE.Clock();
    let frameId = 0;

    function animate() {
      const delta = Math.min(clock.getDelta(), 0.05);
      const elapsed = clock.elapsedTime;
      const speedBoost = 1.18 + Math.sin(elapsed * 0.55) * 0.05;

      movingAway.forEach((light) => {
        light.position.z += light.userData.speed * delta * speedBoost;
        if (light.position.z > 22) {
          light.position.z = -options.length - Math.random() * 60;
        }
      });

      movingCloser.forEach((light) => {
        light.position.z += light.userData.speed * delta * speedBoost;
        if (light.position.z > 18) {
          light.userData.reset();
        }
      });

      sticks.forEach((stick) => {
        stick.position.z += stick.userData.speed * delta * 1.15;
        if (stick.position.z > 28) {
          stick.position.z = -options.length - Math.random() * 40;
        }
      });

      brokenLines.forEach((line) => {
        line.position.z += randomBetween(options.movingAwaySpeed) * delta * speedBoost;
        if (line.position.z > 24) {
          line.position.z = -options.length * 0.88;
        }
      });

      applyDistortion(leftRoad, elapsed, options.distortion, 0.8);
      applyDistortion(rightRoad, elapsed, options.distortion, 0.8);
      applyDistortion(island, elapsed, options.distortion, 0.28);

      shoulderLines.forEach((line) => {
        line.position.x += Math.sin(elapsed * 0.6 + line.position.z * 0.004) * 0.001;
      });

      camera.fov = options.fov + Math.sin(elapsed * 0.8) * (options.fovSpeedUp * 0.012);
      camera.updateProjectionMatrix();
      composer.render(delta);
      frameId = window.requestAnimationFrame(animate);
    }

    resize();
    window.addEventListener("resize", resize);
    frameId = window.requestAnimationFrame(animate);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
      composer.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.domElement.remove();
    };
  }, [options]);

  return (
    <div
      ref={containerRef}
      className={cn("hyperspeed absolute inset-0 overflow-hidden", className)}
      style={style}
      aria-hidden="true"
    />
  );
}

