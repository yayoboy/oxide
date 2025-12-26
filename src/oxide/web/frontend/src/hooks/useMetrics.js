/**
 * React hook for monitoring metrics with WebSocket updates
 */
import { useState, useEffect, useCallback } from 'react';
import { monitoringAPI } from '../api/client';
import { useWebSocket } from './useWebSocket';

export const useMetrics = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { connected, subscribe } = useWebSocket();

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await monitoringAPI.getMetrics();
      setMetrics(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (connected) {
      const unsubscribe = subscribe('metrics', (message) => {
        if (message.data) {
          setMetrics(message.data);
          setLoading(false);
        }
      });

      return unsubscribe;
    }
  }, [connected, subscribe]);

  return { metrics, loading, error, refresh: fetchMetrics };
};
