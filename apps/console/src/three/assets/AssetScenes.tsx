import { RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import Studio from '../Studio';

/** Hero-object renders for the mobile app (exported to PNG/WebP by scripts/render-assets.mjs). */

export function VerifiedBadge() {
  const check = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.42, 0.02, 0.2), new THREE.Vector3(-0.12, -0.28, 0.2), new THREE.Vector3(0.48, 0.34, 0.2),
  ], false, 'catmullrom', 0.01);
  return (
    <>
      <Studio shadowY={-1.25} warm={false} />
      <group rotation={[-0.12, -0.4, 0.05]}>
        <mesh castShadow rotation-x={Math.PI / 2}>
          <cylinderGeometry args={[1, 1, 0.28, 96]} />
          <meshPhysicalMaterial color="#99f6e4" transmission={0.85} thickness={0.8} roughness={0.06} ior={1.5} clearcoat={1} attenuationColor="#14b8a6" attenuationDistance={1.2} />
        </mesh>
        <mesh castShadow>
          <torusGeometry args={[1.02, 0.07, 32, 128]} />
          <meshPhysicalMaterial color="#e2e8f0" metalness={1} roughness={0.18} />
        </mesh>
        <mesh position={[0, 0, 0]}>
          <tubeGeometry args={[check, 64, 0.075, 24, false]} />
          <meshPhysicalMaterial color="#ffffff" emissive="#ccfbf1" emissiveIntensity={0.25} roughness={0.15} clearcoat={1} />
        </mesh>
      </group>
    </>
  );
}

export function CoinStack() {
  const coins = [0, 1, 2, 3, 4];
  return (
    <>
      <Studio shadowY={-1.05} />
      <group rotation={[0.35, -0.5, 0]} position={[0, -0.2, 0]}>
        {coins.map((i) => (
          <mesh key={i} position={[Math.sin(i * 1.7) * 0.05, -0.8 + i * 0.19, Math.cos(i * 1.3) * 0.05]} castShadow receiveShadow>
            <cylinderGeometry args={[0.85, 0.85, 0.16, 96]} />
            <meshPhysicalMaterial color="#f5b942" metalness={1} roughness={0.3} clearcoat={0.4} />
          </mesh>
        ))}
        <mesh position={[0.9, 0.05, 0.55]} rotation={[Math.PI / 2.2, 0, 0.4]} castShadow>
          <cylinderGeometry args={[0.7, 0.7, 0.14, 96]} />
          <meshPhysicalMaterial color="#f5b942" metalness={1} roughness={0.2} clearcoat={0.4} />
        </mesh>
      </group>
    </>
  );
}

export function SecureShield() {
  const shape = new THREE.Shape();
  shape.moveTo(0, 1.1);
  shape.bezierCurveTo(0.45, 0.95, 0.8, 0.9, 0.9, 0.85);
  shape.bezierCurveTo(0.9, 0.1, 0.65, -0.55, 0, -1.05);
  shape.bezierCurveTo(-0.65, -0.55, -0.9, 0.1, -0.9, 0.85);
  shape.bezierCurveTo(-0.8, 0.9, -0.45, 0.95, 0, 1.1);
  return (
    <>
      <Studio shadowY={-1.3} />
      <group rotation={[0.1, -0.45, 0]}>
        <mesh castShadow position={[0, 0, -0.15]}>
          <extrudeGeometry args={[shape, { depth: 0.3, bevelEnabled: true, bevelSize: 0.06, bevelThickness: 0.06, bevelSegments: 8, curveSegments: 48 }]} />
          <meshPhysicalMaterial color="#c7d2fe" transmission={0.9} thickness={1} roughness={0.05} ior={1.5} clearcoat={1} attenuationColor="#4338ca" attenuationDistance={1.5} />
        </mesh>
        <RoundedBox args={[0.62, 0.48, 0.2]} radius={0.06} position={[0, -0.15, 0.3]} castShadow>
          <meshPhysicalMaterial color="#ffb454" metalness={0.9} roughness={0.25} />
        </RoundedBox>
        <mesh position={[0, 0.17, 0.3]} castShadow>
          <torusGeometry args={[0.2, 0.055, 24, 64, Math.PI]} />
          <meshPhysicalMaterial color="#e2e8f0" metalness={1} roughness={0.2} />
        </mesh>
      </group>
    </>
  );
}
