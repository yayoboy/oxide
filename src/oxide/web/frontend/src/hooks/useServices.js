/**
 * React hook for managing services data with WebSocket updates
 * Integrated with Zustand global state
 */
import { useEffect, useCallback, useState } from 'react';
import { servicesAPI } from '../api/client';
import { useWebSocket } from './useWebSocket';
import useStore from '../store/useStore';

export const useServices = () => {
  const { connected, subscribe } = useWebSocket();

  // Get state and actions from Zustand store
  const services = useStore((state) => state.services);
  const loading = useStore((state) => state.servicesLoading);
  const error = useStore((state) => state.servicesError);
  const setServices = useStore((state) => state.setServices);
  const setServicesLoading = useStore((state) => state.setServicesLoading);
  const setServicesError = useStore((state) => state.setServicesError);

  const fetchServices = useCallback(async () => {
    try {
      setServicesLoading(true);
      const response = await servicesAPI.list();
      setServices(response.data);
    } catch (err) {
      setServicesError(err.message);
    }
  }, [setServices, setServicesLoading, setServicesError]);

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
        }
      });

      return unsubscribe;
    }
  }, [connected, subscribe, setServices]);

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
