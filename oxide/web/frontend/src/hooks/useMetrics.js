/**
 * React hook for monitoring metrics
 */
import { useState, useEffect } from 'react';
import { monitoringAPI } from '../api/client';

export const useMetrics = (refreshInterval = 2000) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    try {
      const response = await monitoringAPI.getMetrics();
      setMetrics(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();

    if (refreshInterval > 0) {
      const interval = setInterval(fetchMetrics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval]);

  return { metrics, loading, error, refresh: fetchMetrics };
};
