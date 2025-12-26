/**
 * React hook for monitoring metrics with WebSocket updates
 * Integrated with Zustand global state
 */
import { useEffect, useCallback } from 'react';
import { monitoringAPI } from '../api/client';
import { useWebSocket } from './useWebSocket';
import useStore from '../store/useStore';

export const useMetrics = () => {
  const { connected, subscribe } = useWebSocket();

  // Get state and actions from Zustand store
  const metrics = useStore((state) => state.metrics);
  const loading = useStore((state) => state.metricsLoading);
  const error = useStore((state) => state.metricsError);
  const setMetrics = useStore((state) => state.setMetrics);
  const setMetricsLoading = useStore((state) => state.setMetricsLoading);
  const setMetricsError = useStore((state) => state.setMetricsError);

  const fetchMetrics = useCallback(async () => {
    try {
      setMetricsLoading(true);
      const response = await monitoringAPI.getMetrics();
      setMetrics(response.data);
    } catch (err) {
      setMetricsError(err.message);
    }
  }, [setMetrics, setMetricsLoading, setMetricsError]);

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
        }
      });

      return unsubscribe;
    }
  }, [connected, subscribe, setMetrics]);

  return { metrics, loading, error, refresh: fetchMetrics };
};
