/**
 * React hook for managing machines data
 */
import { useState, useEffect } from 'react';
import { machinesAPI } from '../api/client';

export const useMachines = (refreshInterval = 3000) => {
  const [machines, setMachines] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMachines = async () => {
    try {
      const response = await machinesAPI.list();
      setMachines(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();

    if (refreshInterval > 0) {
      const interval = setInterval(fetchMachines, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval]);

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
