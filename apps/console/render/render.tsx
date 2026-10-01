/* eslint-disable react-refresh/only-export-components -- build-time screenshot entry, never hot-reloaded */
// Build-time only: renders one 3D scene full-window so scripts/render-assets.mjs can screenshot it.
import { StrictMode, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { Canvas, useThree } from '@react-three/fiber';
import SetuHero from '../src/three/SetuHero';
import { CoinStack, SecureShield, VerifiedBadge } from '../src/three/assets/AssetScenes';

const scenes = { hero: SetuHero, badge: VerifiedBadge, coins: CoinStack, shield: SecureShield } as const;
const name = (new URLSearchParams(location.search).get('scene') ?? 'hero') as keyof typeof scenes;
const Scene = scenes[name];

function Ready() {
  const { gl } = useThree();
  useEffect(() => {
    const t = setTimeout(() => { (window as unknown as { __ready: boolean }).__ready = true; }, 2500);
    return () => clearTimeout(t);
  }, [gl]);
  return null;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Canvas shadows dpr={1} gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
      camera={{ position: name === 'hero' ? [0, 1.7, 7.6] : [0, 0.3, 5.0], fov: 35 }}>
      {name === 'hero' ? <SetuHero distance={7.2} /> : <Scene />}
      <Ready />
    </Canvas>
  </StrictMode>,
);
