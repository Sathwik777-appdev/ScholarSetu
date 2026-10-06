import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

// When hosted on Vercel, always use same-origin relative /v1 to leverage Vercel's edge proxy and eliminate all CORS issues.
const isVercel = typeof window !== 'undefined' && window.location.hostname.endsWith('vercel.app');
const rawOrigin = import.meta.env.VITE_API_URL;
const API_ORIGIN: string = rawOrigin !== undefined && rawOrigin !== ''
  ? rawOrigin
  : (import.meta.env.PROD || (typeof window !== 'undefined' && window.location.hostname.endsWith('vercel.app'))
      ? 'https://scholarsetu-api.onrender.com'
      : 'http://localhost:8000');
export const API_BASE_URL = `${API_ORIGIN.replace(/\/$/, '')}/v1`;

const TOKEN_KEY = 'scholarsetu.console.token';
const REFRESH_KEY = 'scholarsetu.console.refresh';

// Per tab (sessionStorage): closing the tab ends the session. The refresh token renews the 15-minute access token.
export const tokenStore = {
  get: (): string | null => sessionStorage.getItem(TOKEN_KEY),
  getRefresh: (): string | null => sessionStorage.getItem(REFRESH_KEY),
  set: (token: string, refresh?: string | null) => {
    sessionStorage.setItem(TOKEN_KEY, token);
    if (refresh) sessionStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  },
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

// The API answers 503 WAKING while its database starts after an idle period; listeners show progress.
type WakingListener = () => void;
const wakingListeners = new Set<WakingListener>();
export const onWaking = (fn: WakingListener) => {
  wakingListeners.add(fn);
  return () => { wakingListeners.delete(fn); };
};

type Renewed = { token: string } | { ended: true } | { unavailable: true };
let renewing: Promise<Renewed> | null = null;

/** Trade the refresh token for a new access token. One call at a time: the server accepts a refresh token once
 * (a second use looks like a copied token and ends the session), so parallel requests share one call. */
function renew(): Promise<Renewed> {
  renewing ??= (async (): Promise<Renewed> => {
    const refresh = tokenStore.getRefresh();
    if (!refresh) return { ended: true };
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh }, { timeout: 20000 });
      tokenStore.set(res.data.access_token, res.data.refresh_token);
      return { token: res.data.access_token as string };
    } catch (err) {
      // Only the server saying no ends the session; a sleeping or unreachable API must not sign anyone out.
      return axios.isAxiosError(err) && err.response?.status === 401 ? { ended: true } : { unavailable: true };
    }
  })().finally(() => { renewing = null; });
  return renewing;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _renewed?: boolean }) | undefined;
    // Signing in, renewing and signing out carry their own credentials; every other call (including /auth/me) renews.
    const isAuthCall = /^\/auth\/(otp|refresh|logout)/.test(String(original?.url ?? ''));
    if (error.response?.status === 401 && original && !original._renewed && !isAuthCall && tokenStore.getRefresh()) {
      original._renewed = true;
      const result = await renew();
      if ('token' in result) {
        original.headers.Authorization = `Bearer ${result.token}`;
        return apiClient(original);
      }
      if ('ended' in result && onUnauthorized) onUnauthorized();
      return Promise.reject(error);
    }
    if (error.response?.status === 401 && onUnauthorized) onUnauthorized();
    if (isWaking(error)) wakingListeners.forEach((fn) => fn());
    return Promise.reject(error);
  },
);

/** The API answers 503 with code WAKING when its database is asleep; it has already asked for everything to
 * start (the power manager is private, so the console never calls it). While the database is mid-start the
 * request can outlast the host's proxy, which then answers 502 or 504 instead: treat those the same. The waking
 * banner checks the API itself, so a gateway error from anything else clears within seconds. */
export function isWaking(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  const status = error.response?.status;
  if (status === 502 || status === 504) return true;
  return status === 503 && (error.response?.data as { code?: unknown })?.code === 'WAKING';
}

/** A message fit to show an officer: the API's own detail when there is one, never a stack trace. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (isWaking(error)) return 'ScholarSetu is starting up after being idle. This takes a few minutes; this page will refresh itself.';
    if (!error.response) return 'The ScholarSetu API could not be reached.';
    const detail = (error.response.data as { detail?: unknown })?.detail;
    if (typeof detail === 'string') return detail;
    // Structured refusals (rule violations, open review cases, one scheme at a time) carry a message.
    if (detail && typeof detail === 'object' && typeof (detail as { message?: unknown }).message === 'string') {
      const d = detail as { message: string; violations?: unknown; issues?: unknown };
      const violations = Array.isArray(d.violations) ? d.violations.filter((v) => typeof v === 'string') : [];
      // The bank check names what is wrong (and the steps that fix it) in each issue.
      const issues = Array.isArray(d.issues)
        ? d.issues.map((i) => (i as { message?: unknown })?.message).filter((m): m is string => typeof m === 'string') : [];
      return [d.message, ...violations, ...issues].join(' ');
    }
    if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === 'string') {
      return detail.map((e: { loc?: unknown[]; msg: string }) => `${(e.loc ?? []).slice(1).join('.')}: ${e.msg}`).join('; ');
    }
    if (error.response.status === 403) return 'Your role does not have access to this.';
    if (error.response.status === 502 || error.response.status === 504) return 'ScholarSetu is starting up after being idle. This takes a few minutes; this page will refresh itself.';
    return `The API returned an error (HTTP ${error.response.status}).`;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
