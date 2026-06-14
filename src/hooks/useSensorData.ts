import { useState, useEffect, useCallback } from 'react';
import { SensorData } from '../types';

const REFRESH_INTERVAL = 5000;

export function useSensorData() {
  const [data, setData] = useState<SensorData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const endpoint = '/api/data';

    try {
      const response = await fetch(endpoint, {
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json: SensorData = await response.json();
      setData(json);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { data, loading };
}