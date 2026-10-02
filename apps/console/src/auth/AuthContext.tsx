import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { apiClient, setUnauthorizedHandler, tokenStore } from '../api/client';
import type { AuthTokenResponse, AuthUser } from '../types';
import { AuthContext, CONSOLE_ROLES } from './auth';

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

  // Officers sign in with a code emailed to them. `demo` comes from the demo toggle: the server then accepts the
  // demo code for seeded demo accounts only.
  const requestOtp = async (email: string, demo: boolean) => {
    const res = await apiClient.post<{ message: string }>('/auth/otp/request', { email, demo });
    return res.data.message;
  };

  const verifyOtp = async (email: string, otp: string, demo: boolean) => {
    const res = await apiClient.post<AuthTokenResponse>('/auth/otp/verify', { email, otp, demo });
    if (!CONSOLE_ROLES.includes(res.data.user.role)) {
      throw new Error(`${res.data.user.name || 'This account'} is not an officer account. This console is for officers `
        + 'and the Ministry; students and families use the ScholarSetu app.');
    }
    tokenStore.set(res.data.access_token);
    setUser(res.data.user);
  };

  return (
    <AuthContext.Provider value={{ user, checking, requestOtp, verifyOtp, logout }}>{children}</AuthContext.Provider>
  );
}

