import { useCallback, useEffect, useState } from 'react';
import { apiClient, errorMessage } from '../api/client';

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** GET an endpoint. There is no fallback data: on failure `data` stays null and `error` says why. */
export function useApi<T>(endpoint: string | null, params?: Record<string, string | number | undefined>): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(endpoint !== null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const paramKey = JSON.stringify(params ?? {});

  useEffect(() => {
    if (endpoint === null) return;
    let active = true;
    setLoading(true);
    setError(null);
    apiClient
      .get<T>(endpoint, { params: JSON.parse(paramKey) })
      .then((res) => active && setData(res.data))
      .catch((err) => {
        if (!active) return;
        setData(null);
        setError(errorMessage(err));
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [endpoint, paramKey, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, reload };
}
