/**
 * React hook for managing machines data with WebSocket updates
 */
import { useState, useEffect, useCallback } from 'react';
import { machinesAPI } from '../api/client';
import { useWebSocket } from './useWebSocket';

export const useMachines = () => {
  const [machines, setMachines] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { connected, subscribe } = useWebSocket();

  const fetchMachines = useCallback(async () => {
    try {
      setLoading(true);
      const response = await machinesAPI.list();
      setMachines(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMachines();
  }, [fetchMachines]);

  // Subscribe to WebSocket updates for machine metrics
  useEffect(() => {
    if (connected) {
      const unsubscribe = subscribe('metrics', (message) => {
        // Machines data might be part of cluster metrics in the future
        // For now, keep using REST API with manual refresh
        if (message.data?.machines) {
          setMachines(message.data.machines);
          setLoading(false);
        }
      });

      return unsubscribe;
    }
  }, [connected, subscribe]);

  return { machines, loading, error, refresh: fetchMachines };
};

export const useMachine = (machineId) => {
  const [machine, setMachine] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMachine = async () => {
    try {
      setLoading(true);
      const response = await machinesAPI.get(machineId);
      setMachine(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (machineId) {
      fetchMachine();
    }
  }, [machineId]);

  return { machine, loading, error, refresh: fetchMachine };
};
