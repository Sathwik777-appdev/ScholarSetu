import axios, { AxiosError } from 'axios';

// The API origin comes from the build environment; every route lives under /v1.
const API_ORIGIN: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const API_BASE_URL = `${API_ORIGIN.replace(/\/$/, '')}/v1`;

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

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorized) onUnauthorized();
    return Promise.reject(error);
  },
);

/** A message fit to show an officer: the API's own detail when there is one, never a stack trace. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'The ScholarSetu API could not be reached.';
    const detail = (error.response.data as { detail?: unknown })?.detail;
    if (typeof detail === 'string') return detail;
    if (error.response.status === 403) return 'Your role does not have access to this.';
    return `The API returned an error (HTTP ${error.response.status}).`;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
