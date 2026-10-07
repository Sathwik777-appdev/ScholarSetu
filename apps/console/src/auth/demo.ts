import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { UserRole } from '../types';

export interface DemoAccount {
  name: string;
  role: UserRole;
  email?: string | null;
  phone?: string | null;
}

export interface DemoInfo {
  available: boolean;
  demo_code: string | null;
  console_accounts: DemoAccount[];
  app_accounts: DemoAccount[];
}

export const DEFAULT_DEMO_ACCOUNTS: DemoAccount[] = [
  { name: 'MoTA Scholarship Division', role: 'MINISTRY', email: 'kotianchethan4@gmail.com' },
  { name: 'Tribal Welfare Department, Jharkhand', role: 'STATE_OFFICER', email: 'chethankotian006@gmail.com' },
  { name: 'District Welfare Officer, Dumka', role: 'DISTRICT_OFFICER', email: 'sathwikjpoojary@gmail.com' },
  { name: 'Principal, Dumka Government College', role: 'INSTITUTE_OFFICER', email: 'teamace088@gmail.com' },
];

export const DEFAULT_DEMO_INFO: DemoInfo = {
  available: true,
  demo_code: '123456',
  console_accounts: DEFAULT_DEMO_ACCOUNTS,
  app_accounts: [
    { name: 'Sunita Hansda', role: 'STUDENT', phone: '9876543210' },
    { name: 'Babulal Hansda', role: 'GUARDIAN', phone: '9876543212' },
    { name: 'MoTA Scholarship Division', role: 'MINISTRY', phone: '9876543213' },
  ],
};

const KEY = 'scholarsetu.demoMode';

function read(): boolean {
  try {
    const val = localStorage.getItem(KEY);
    return val === null ? true : val === 'on';
  } catch {
    return true;
  }
}

/**
 * The demo toggle shown on every sign-in page.
 * With it on, seeded demo accounts sign in with the fixed demo OTP (123456).
 * Defaults to seeded accounts immediately so the officer list is never blank.
 */
export function useDemoMode() {
  const [enabled, setEnabledState] = useState(read);
  const [info, setInfo] = useState<DemoInfo>(DEFAULT_DEMO_INFO);

  const fetchDemo = useCallback(async () => {
    try {
      const res = await apiClient.get<DemoInfo>('/auth/demo', { timeout: 8000 });
      if (res.data?.available && res.data.console_accounts?.length) {
        setInfo(res.data);
      }
    } catch {
      // Retain DEFAULT_DEMO_INFO if cold or unreachable
    }
  }, []);

  useEffect(() => {
    fetchDemo();
    window.addEventListener('scholarsetu:ready', fetchDemo);
    return () => window.removeEventListener('scholarsetu:ready', fetchDemo);
  }, [fetchDemo]);

  const setEnabled = (on: boolean) => {
    setEnabledState(on);
    try {
      localStorage.setItem(KEY, on ? 'on' : 'off');
    } catch {
      /* private window: not remembered */
    }
    if (on) {
      fetchDemo();
    }
  };

  return { enabled, setEnabled, info };
}
