import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiClient, errorMessage, setUnauthorizedHandler, tokenStore } from '../api/client';
import type { AuthTokenResponse, AuthUser, UserRole } from '../types';

// The console is for officers and the ministry. Students and guardians use the mobile app.
export const CONSOLE_ROLES: UserRole[] = ['INSTITUTE_OFFICER', 'DISTRICT_OFFICER', 'STATE_OFFICER', 'MINISTRY'];
export const ANALYTICS_ROLES: UserRole[] = ['DISTRICT_OFFICER', 'STATE_OFFICER', 'MINISTRY'];

interface AuthState {
  user: AuthUser | null;
  checking: boolean;
  requestOtp: (phone: string) => Promise<string>;
  verifyOtp: (phone: string, otp: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!tokenStore.get()) {
      setChecking(false);
      return;
    }
    // The role always comes from the server, never from the stored token.
    apiClient
      .get<AuthUser>('/auth/me')
      .then((res) => (CONSOLE_ROLES.includes(res.data.role) ? setUser(res.data) : logout()))
      .catch(() => logout())
      .finally(() => setChecking(false));
  }, [logout]);

  const requestOtp = async (phone: string) => {
    const res = await apiClient.post<{ message: string }>('/auth/otp/request', { phone });
    return res.data.message;
  };

  const verifyOtp = async (phone: string, otp: string) => {
    const res = await apiClient.post<AuthTokenResponse>('/auth/otp/verify', { phone, otp });
    if (!CONSOLE_ROLES.includes(res.data.user.role)) {
      throw new Error('This console is for officers and the ministry. Students use the ScholarSetu mobile app.');
    }
    tokenStore.set(res.data.access_token);
    setUser(res.data.user);
  };

  return (
    <AuthContext.Provider value={{ user, checking, requestOtp, verifyOtp, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

export { errorMessage };
