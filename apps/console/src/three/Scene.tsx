import { Component, Suspense, useEffect, useState, type ReactNode } from 'react';
import { Canvas } from '@react-three/fiber';
import { prefersReducedMotion, webglAvailable } from './support';

class Boundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/**
 * A WebGL canvas that degrades gracefully: without WebGL, or if the scene throws, the fallback is shown
 * (which must carry the same information). With reduced motion the scene renders only on demand.
 */
export default function Scene({ children, fallback, camera = [0, 1.2, 6], className = '', label }: {
  children: ReactNode;
  fallback: ReactNode;
  camera?: [number, number, number];
  className?: string;
  label: string;
}) {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => setOk(webglAvailable()), []);
  if (ok === false) return <>{fallback}</>;
  if (ok === null) return <div className={className} />;
  return (
    <Boundary fallback={fallback}>
      <div className={className} role="img" aria-label={label}>
        <Canvas
          shadows
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true, powerPreference: 'high-performance', preserveDrawingBuffer: true }}
          camera={{ position: camera, fov: 35 }}
          frameloop={prefersReducedMotion() ? 'demand' : 'always'}
        >
          <Suspense fallback={null}>{children}</Suspense>
        </Canvas>
      </div>
    </Boundary>
  );
}
