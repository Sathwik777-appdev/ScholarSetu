import { lazy, Suspense, type ComponentProps } from 'react';

const HeroCanvasLazy = lazy(() => import('../three/HeroCanvas'));
const TowersCanvasLazy = lazy(() => import('../three/TowersCanvas'));

export function Hero3D(props: ComponentProps<typeof HeroCanvasLazy>) {
  return (
    <Suspense fallback={<div className={`${props.className ?? ''} bg-ink-900`} />}>
      <HeroCanvasLazy {...props} />
    </Suspense>
  );
}

export function Towers3D(props: ComponentProps<typeof TowersCanvasLazy>) {
  return (
    <Suspense fallback={<div className={`${props.className ?? 'h-72'} skeleton`} />}>
      <TowersCanvasLazy {...props} />
    </Suspense>
  );
}
