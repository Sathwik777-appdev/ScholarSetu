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

  const requestOtp = async (phone: string) => {
    const res = await apiClient.post<{ message: string }>('/auth/otp/request', { phone });
    return res.data.message;
  };

  const verifyOtp = async (phone: string, otp: string) => {
    const res = await apiClient.post<AuthTokenResponse>('/auth/otp/verify', { phone, otp });
    if (!CONSOLE_ROLES.includes(res.data.user.role)) {
      const who = res.data.user.name ? `${res.data.user.name} (${res.data.user.role.toLowerCase().replace(/_/g, ' ')})` : 'This number';
      throw new Error(`${who} is not an officer account. This console is for officers and the ministry; students and families use the ScholarSetu mobile app.`);
    }
    tokenStore.set(res.data.access_token);
    setUser(res.data.user);
  };

  return (
    <AuthContext.Provider value={{ user, checking, requestOtp, verifyOtp, logout }}>{children}</AuthContext.Provider>
  );
}

