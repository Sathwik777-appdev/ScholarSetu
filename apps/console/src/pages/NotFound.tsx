import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div className="text-center">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-ink-900 text-saffron-400"><Compass className="h-7 w-7" /></span>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight text-slate-900">Page not found</h1>
        <p className="mt-2 text-[15px] text-slate-500">That page does not exist, or you do not have access to it.</p>
        <Link to="/my-work" className="btn btn-primary mt-6">Go to My work</Link>
      </div>
    </div>
  );
}
