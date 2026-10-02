import { createContext, useContext } from 'react';
import type { AuthUser, UserRole } from '../types';

// The console is for officers and the ministry. Students and guardians use the mobile app.
export const CONSOLE_ROLES: UserRole[] = ['INSTITUTE_OFFICER', 'DISTRICT_OFFICER', 'STATE_OFFICER', 'MINISTRY'];
export const ANALYTICS_ROLES: UserRole[] = ['DISTRICT_OFFICER', 'STATE_OFFICER', 'MINISTRY'];

export interface AuthState {
  user: AuthUser | null;
  checking: boolean;
  requestOtp: (email: string, demo: boolean) => Promise<string>;
  verifyOtp: (email: string, otp: string, demo: boolean) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
