import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Float, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import Studio from './Studio';

const SPAN = 5.2;

/** A student crossing the bridge: a glowing orb moving along the deck from one bank to the other. */
function Traveller({ delay, speed, lane }: { delay: number; speed: number; lane: number }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    const t = ((clock.elapsedTime * speed + delay) % 1 + 1) % 1;
    const x = -SPAN / 2 + t * SPAN;
    if (ref.current) {
      ref.current.position.set(x, 0.32 + Math.sin(t * Math.PI) * 0.55, lane);
      const s = 0.6 + Math.sin(t * Math.PI) * 0.4;
      ref.current.scale.setScalar(s);
    }
  });
  return (
    <mesh ref={ref} castShadow>
      <sphereGeometry args={[0.11, 32, 32]} />
      <meshPhysicalMaterial color="#ffb454" emissive="#f59e0b" emissiveIntensity={1.6} roughness={0.2} clearcoat={1} />
    </mesh>
  );
}

function Arch({ x, scale = 1 }: { x: number; scale?: number }) {
  return (
    <mesh position={[x, 0.1, 0]} scale={scale} castShadow>
      <torusGeometry args={[0.9, 0.06, 32, 96, Math.PI]} />
      <meshPhysicalMaterial color="#dbeafe" transmission={0.92} thickness={0.6} roughness={0.08} ior={1.45}
        clearcoat={1} clearcoatRoughness={0.05} />
    </mesh>
  );
}

/** Keep the whole bridge in frame on tall (phone) screens by stepping the camera back. */
function ResponsiveCamera({ base }: { base: number }) {
  const { camera, size } = useThree();
  useEffect(() => {
    const aspect = size.width / Math.max(size.height, 1);
    const distance = aspect < 1.3 ? base + (1.3 - aspect) * 9 : base;
    camera.position.set(0, 2.4 * (distance / 10.5), distance);
    camera.lookAt(0, 0.4, 0);
  }, [camera, size, base]);
  return null;
}

export default function SetuHero({ distance = 10.5 }: { distance?: number }) {
  const group = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (group.current) group.current.rotation.y = Math.sin(clock.elapsedTime * 0.15) * 0.25 - 0.35;
  });
  return (
    <>
      <color attach="background" args={['#0c1326']} />
      <fog attach="fog" args={['#0c1326', 11, 22]} />
      <ResponsiveCamera base={distance} />
      <Studio shadowY={-0.05} />
      <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.35}>
        <group ref={group} position={[0, 0.6, 0]} scale={0.95}>
          {/* Banks: the two systems the bridge joins */}
          <RoundedBox args={[1.1, 0.9, 1.4]} radius={0.12} position={[-SPAN / 2 - 0.4, -0.2, 0]} castShadow receiveShadow>
            <meshPhysicalMaterial color="#1f2a4d" metalness={0.6} roughness={0.35} clearcoat={0.6} />
          </RoundedBox>
          <RoundedBox args={[1.1, 0.9, 1.4]} radius={0.12} position={[SPAN / 2 + 0.4, -0.2, 0]} castShadow receiveShadow>
            <meshPhysicalMaterial color="#1f2a4d" metalness={0.6} roughness={0.35} clearcoat={0.6} />
          </RoundedBox>
          {/* Deck: brushed metal */}
          <RoundedBox args={[SPAN, 0.12, 0.9]} radius={0.05} position={[0, 0.12, 0]} castShadow receiveShadow>
            <meshPhysicalMaterial color="#c7cedb" metalness={0.9} roughness={0.28} anisotropy={0.6} />
          </RoundedBox>
          {[-1.8, 0, 1.8].map((x, i) => <Arch key={x} x={x} scale={i === 1 ? 1.15 : 0.95} />)}
          {/* Verified: a teal ring on the far bank */}
          <mesh position={[SPAN / 2 + 0.4, 0.62, 0]} rotation-x={Math.PI / 2} castShadow>
            <torusGeometry args={[0.32, 0.07, 32, 64]} />
            <meshPhysicalMaterial color="#2dd4bf" emissive="#14b8a6" emissiveIntensity={0.6} metalness={0.3} roughness={0.2} clearcoat={1} />
          </mesh>
          {[0, 0.2, 0.4, 0.6, 0.8].map((d, i) => (
            <Traveller key={d} delay={d} speed={0.09 + i * 0.012} lane={(i % 3 - 1) * 0.22} />
          ))}
        </group>
      </Float>
    </>
  );
}
