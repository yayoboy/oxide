/**
 * React hook for managing services data with WebSocket updates
 */
import { useState, useEffect, useCallback } from 'react';
import { servicesAPI } from '../api/client';
import { useWebSocket } from './useWebSocket';

export const useServices = () => {
  const [services, setServices] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { connected, subscribe } = useWebSocket();

  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      const response = await servicesAPI.list();
      setServices(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (connected) {
      const unsubscribe = subscribe('service_status', (message) => {
        if (message.status) {
          setServices(message.status);
          setLoading(false);
        }
      });

      return unsubscribe;
    }
  }, [connected, subscribe]);

  return { services, loading, error, refresh: fetchServices };
};

export const useService = (serviceName) => {
  const [service, setService] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchService = async () => {
    try {
      setLoading(true);
      const response = await servicesAPI.get(serviceName);
      setService(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (serviceName) {
      fetchService();
    }
  }, [serviceName]);

  return { service, loading, error, refresh: fetchService };
};
