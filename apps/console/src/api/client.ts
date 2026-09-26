import axios from 'axios';

export const getApiBaseUrl = () => {
  const envUrl = (import.meta as any).env?.VITE_API_URL;
  if (envUrl) {
    return envUrl;
  }
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `http://${hostname}:8000`;
    }
  }
  return 'http://localhost:8000';
};

export const apiClient = axios.create({
  baseURL: `${getApiBaseUrl()}/api`,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

