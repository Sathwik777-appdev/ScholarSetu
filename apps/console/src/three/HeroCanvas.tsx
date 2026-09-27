import Scene from './Scene';
import SetuHero from './SetuHero';

export default function HeroCanvas({ className = '' }: { className?: string }) {
  return (
    <Scene className={className} camera={[0, 2.4, 10.5]} label="A glass bridge carrying students from one system to another"
      fallback={<div className={`${className} bg-[radial-gradient(ellipse_at_30%_40%,#1f2a4d,#0c1326_70%)]`} />}>
      <SetuHero />
    </Scene>
  );
}
