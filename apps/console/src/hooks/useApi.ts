import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

export function useApi<T>(endpoint: string, fallbackData: T) {
  const [data, setData] = useState<T>(fallbackData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get<T>(endpoint);
        if (mounted) {
          setData(response.data);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          console.warn(`API call to ${endpoint} failed, using fallback data.`, err.message);
          setData(fallbackData);
          setError(err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, [endpoint, fallbackData]);

  // If endpoint is empty, just return fallbackData
  useEffect(() => {
      if(!endpoint) {
          setData(fallbackData)
      }
  }, [endpoint, fallbackData])

  return { data, loading, error };
}
