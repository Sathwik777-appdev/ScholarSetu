import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { UserRole } from '../types';

export interface DemoAccount { name: string; role: UserRole; email?: string | null; phone?: string | null }
export interface DemoInfo {
  available: boolean;
  demo_code: string | null;
  console_accounts: DemoAccount[];
  app_accounts: DemoAccount[];
}

const KEY = 'scholarsetu.demoMode';

function read(): boolean {
  try { return localStorage.getItem(KEY) === 'on'; } catch { return false; }
}

/** The demo toggle shown on every sign-in page. With it on, the seeded demo accounts sign in with the demo code;
 * the server allows that only for demo accounts, so the toggle never opens a real account. */
export function useDemoMode() {
  const [enabled, setEnabledState] = useState(read);
  const [info, setInfo] = useState<DemoInfo | null>(null);
  useEffect(() => {
    apiClient.get<DemoInfo>('/auth/demo').then((r) => setInfo(r.data)).catch(() => setInfo(null));
  }, []);
  const setEnabled = (on: boolean) => {
    setEnabledState(on);
    try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch { /* private window: not remembered */ }
  };
  return { enabled, setEnabled, info };
}
