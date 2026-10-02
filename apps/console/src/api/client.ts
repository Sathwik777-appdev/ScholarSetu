import axios, { AxiosError } from 'axios';

// When hosted on Vercel, always use same-origin relative /v1 to leverage Vercel's edge proxy and eliminate all CORS issues.
const isVercel = typeof window !== 'undefined' && window.location.hostname.endsWith('vercel.app');
const rawOrigin = import.meta.env.VITE_API_URL;
const API_ORIGIN: string = isVercel
  ? ''
  : (rawOrigin !== undefined && rawOrigin !== '' ? rawOrigin : (import.meta.env.PROD ? '' : 'http://localhost:8000'));
export const API_BASE_URL = API_ORIGIN ? `${API_ORIGIN.replace(/\/$/, '')}/v1` : '/v1';

const TOKEN_KEY = 'scholarsetu.console.token';

export const tokenStore = {
  get: (): string | null => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
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

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorized) onUnauthorized();
    if (isWaking(error)) wakingListeners.forEach((fn) => fn());
    return Promise.reject(error);
  },
);

/** The API answers 503 with code WAKING when its database is asleep; it has already asked for everything to
 * start (the power manager is private, so the console never calls it). */
export function isWaking(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 503
    && (error.response.data as { code?: unknown })?.code === 'WAKING';
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
      const d = detail as { message: string; violations?: unknown };
      const violations = Array.isArray(d.violations) ? d.violations.filter((v) => typeof v === 'string') : [];
      return violations.length ? `${d.message} ${violations.join(' ')}` : d.message;
    }
    if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === 'string') {
      return detail.map((e: { loc?: unknown[]; msg: string }) => `${(e.loc ?? []).slice(1).join('.')}: ${e.msg}`).join('; ');
    }
    if (error.response.status === 403) return 'Your role does not have access to this.';
    return `The API returned an error (HTTP ${error.response.status}).`;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
