/**
 * Services Store - Manages LLM services state
 *
 * Handles fetching, caching, and updating service status.
 * Separated for performance - only components using services re-render.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useServicesStore = create(
  persist(
    (set, get) => ({
      // State
      services: {},
      loading: false,
      error: null,
      lastFetch: null,

      // Actions
      setServices: (services) => set({
        services,
        lastFetch: Date.now(),
        error: null
      }),

      setLoading: (loading) => set({ loading }),

      setError: (error) => set({ error, loading: false }),

      updateService: (serviceName, updates) => set((state) => ({
        services: {
          ...state.services,
          [serviceName]: {
            ...state.services[serviceName],
            ...updates
          }
        }
      })),

      clearServices: () => set({
        services: {},
        loading: false,
        error: null,
        lastFetch: null
      }),

      // Computed/Selectors
      getService: (serviceName) => get().services[serviceName],

      getHealthyServices: () => {
        const services = get().services;
        return Object.entries(services)
          .filter(([_, service]) => service.healthy)
          .map(([name]) => name);
      },

      getServiceCount: () => {
        const services = get().services;
        return {
          total: Object.keys(services).length,
          healthy: Object.values(services).filter(s => s.healthy).length,
          enabled: Object.values(services).filter(s => s.enabled).length
        };
      },

      // Check if data is stale (older than 30s)
      isStale: () => {
        const lastFetch = get().lastFetch;
        if (!lastFetch) return true;
        return Date.now() - lastFetch > 30000;
      }
    }),
    {
      name: 'oxide-services-storage',
      // Only persist services data, not loading/error states
      partialize: (state) => ({
        services: state.services,
        lastFetch: state.lastFetch
      })
    }
  )
);

// Optimized selectors
export const selectServices = (state) => state.services;
export const selectLoading = (state) => state.loading;
export const selectError = (state) => state.error;
export const selectServiceByName = (name) => (state) => state.services[name];
export const selectHealthyServices = (state) =>
  Object.entries(state.services)
    .filter(([_, service]) => service.healthy)
    .map(([name]) => name);
