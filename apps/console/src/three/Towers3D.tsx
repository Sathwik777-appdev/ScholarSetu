import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, OrbitControls, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import Studio from './Studio';

export interface TowerDatum {
  label: string;
  value: number;
  display: string; // what the label shows (e.g. "123" or "51.0%")
  color: string;
}

/** One glossy bar that grows to its height once, from the real value it represents. */
function Tower({ x, height, datum }: { x: number; height: number; datum: TowerDatum }) {
  const ref = useRef<THREE.Group>(null);
  const grown = useRef(0);
  useFrame((_, delta) => {
    grown.current = Math.min(1, grown.current + delta * 1.6);
    const eased = 1 - Math.pow(1 - grown.current, 3);
    if (ref.current) ref.current.scale.y = Math.max(0.001, eased);
  });
  const h = Math.max(height, 0.04);
  return (
    <group position={[x, 0, 0]}>
      <group ref={ref}>
        <RoundedBox args={[0.62, h, 0.62]} radius={0.08} position={[0, h / 2, 0]} castShadow receiveShadow>
          <meshPhysicalMaterial color={datum.color} metalness={0.25} roughness={0.22} clearcoat={1} clearcoatRoughness={0.08} />
        </RoundedBox>
      </group>
      <Html position={[0, h + 0.22, 0]} center className="pointer-events-none select-none">
        <div className="whitespace-nowrap rounded-full bg-white/95 px-2 py-0.5 text-[11px] font-semibold text-slate-900 shadow ring-1 ring-slate-200">{datum.display}</div>
      </Html>
    </group>
  );
}

/** Bars in 3D. Heights are proportional to the values: against `scaleMax` when given (e.g. 100 for
 * percentages), otherwise against the largest value. */
export default function Towers3D({ data, maxHeight = 2.2, scaleMax }: { data: TowerDatum[]; maxHeight?: number; scaleMax?: number }) {
  const max = useMemo(() => scaleMax ?? Math.max(...data.map((d) => d.value), 1), [data, scaleMax]);
  const gap = 0.95;
  const start = -((data.length - 1) * gap) / 2;
  return (
    <>
      <Studio shadowY={0} warm={false} />
      {data.map((d, i) => (
        <Tower key={d.label} x={start + i * gap} height={(d.value / max) * maxHeight} datum={d} />
      ))}
      <OrbitControls enablePan={false} enableZoom={false} minPolarAngle={0.6} maxPolarAngle={1.35}
        minAzimuthAngle={-0.7} maxAzimuthAngle={0.7} target={[0, 1.0, 0]} />
    </>
  );
}
