import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const TITLES: [string, string][] = [
  ['/my-work', 'My work'], ['/dashboard', 'Dashboard'], ['/review-queue', 'Review queue'],
  ['/application/', 'Application'], ['/applications', 'Applications'], ['/coverage-map', 'Coverage'],
  ['/analytics', 'Bottlenecks and SLA'], ['/dbt-monitor', 'DBT failures'], ['/data-requests', 'Data requests'],
  ['/manage-officers', 'Officers'], ['/demo-sms', 'Demo SMS'], ['/login', 'Sign in'],
];

/** Sets the browser tab title from the route, so tabs and history are readable. */
export function usePageTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const hit = TITLES.find(([prefix]) => pathname.startsWith(prefix));
    document.title = hit ? `${hit[1]} · ScholarSetu` : 'ScholarSetu';
  }, [pathname]);
}
