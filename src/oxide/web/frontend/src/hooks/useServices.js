/**
 * React hook for managing services data
 */
import { useState, useEffect } from 'react';
import { servicesAPI } from '../api/client';

export const useServices = (refreshInterval = 5000) => {
  const [services, setServices] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchServices = async () => {
    try {
      const response = await servicesAPI.list();
      setServices(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServices();

    if (refreshInterval > 0) {
      const interval = setInterval(fetchServices, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval]);

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
