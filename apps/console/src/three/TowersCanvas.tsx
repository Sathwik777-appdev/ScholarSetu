import type { ReactNode } from 'react';
import Scene from './Scene';
import Towers3D, { type TowerDatum } from './Towers3D';

export type { TowerDatum };

/** 3D bars for real data; `fallback` (a table or 2D chart with the same numbers) shows without WebGL. */
export default function TowersCanvas({ data, label, fallback, className = 'h-72', scaleMax }: {
  data: TowerDatum[];
  scaleMax?: number;
  label: string;
  fallback: ReactNode;
  className?: string;
}) {
  const distance = Math.max(6.2, data.length * 1.1 + 2.2);
  return (
    <div>
      <Scene className={className} camera={[0, 2.8, distance]} label={label} fallback={fallback}>
        <Towers3D data={data} scaleMax={scaleMax} />
      </Scene>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-600">
        {data.map((d) => (
          <li key={d.label} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: d.color }} />
            {d.label} <span className="font-semibold text-slate-900 tabular-nums">{d.display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
