import { useState, useEffect, useCallback } from 'react';
import { SensorData } from '../types';

const REFRESH_INTERVAL = 5000;
const USE_MOCK = false;

export function useSensorData() {
  const [data, setData] = useState<SensorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  const fetchData = useCallback(async () => {
    const endpoint = USE_MOCK ? '/api/mock' : '/api/data';

    try {
      const response = await fetch(endpoint, {
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json: SensorData = await response.json();
      setData(json);
      setLastUpdated(new Date());
      setIsOnline(true);
      setError(null);
    } catch (err) {
      setIsOnline(false);
      setError('Unable to reach sensor backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { data, loading, error, lastUpdated, isOnline };
}