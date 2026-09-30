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

const POWER_URL = 'https://scholarsetu-power-906769842576.asia-south1.run.app';
let wakeTriggered = false;

export async function triggerAutoWake(): Promise<void> {
  if (wakeTriggered) return;
  wakeTriggered = true;
  try {
    await fetch(`${POWER_URL}/wake`, { method: 'POST', mode: 'cors' });
  } catch {
    // best-effort auto-wake
  }
}

apiClient.interceptors.response.use(
  (response) => {
    wakeTriggered = false;
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorized) onUnauthorized();
    if (error.response?.status === 503 || !error.response) {
      triggerAutoWake();
    }
    return Promise.reject(error);
  },
);

/** A message fit to show an officer: the API's own detail when there is one, never a stack trace. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 503) {
      return 'ScholarSetu cloud servers were in zero-cost sleep mode and are now waking up automatically (~30s). Please wait a moment!';
    }
    if (!error.response) return 'The ScholarSetu API could not be reached (auto-waking cloud servers).';
    const detail = (error.response.data as { detail?: unknown })?.detail;
    if (typeof detail === 'string') return detail;
    if (error.response.status === 403) return 'Your role does not have access to this.';
    return `The API returned an error (HTTP ${error.response.status}).`;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
