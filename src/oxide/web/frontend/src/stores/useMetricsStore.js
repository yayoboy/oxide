/**
 * Metrics Store - Manages system metrics state
 *
 * Handles real-time metrics updates from WebSocket.
 * Separated for performance - metrics update frequently.
 */
import { create } from 'zustand';

export const useMetricsStore = create((set, get) => ({
  // State
  metrics: null,
  history: [], // Keep last N metrics for charts
  maxHistoryLength: 60, // Last 60 data points (2 minutes at 2s intervals)

  // Actions
  setMetrics: (metrics) => set((state) => {
    const newHistory = [...state.history, {
      ...metrics,
      timestamp: Date.now()
    }].slice(-state.maxHistoryLength);

    return {
      metrics,
      history: newHistory
    };
  }),

  clearMetrics: () => set({
    metrics: null,
    history: []
  }),

  setMaxHistoryLength: (length) => set({
    maxHistoryLength: length
  }),

  // Computed selectors
  getCPUPercent: () => get().metrics?.system?.cpu_percent || 0,

  getMemoryPercent: () => get().metrics?.system?.memory_percent || 0,

  getTaskStats: () => get().metrics?.tasks || {
    total: 0,
    running: 0,
    completed: 0,
    failed: 0,
    queued: 0
  },

  getServiceStats: () => get().metrics?.services || {
    total: 0,
    enabled: 0,
    healthy: 0,
    unhealthy: 0
  },

  getWebSocketConnections: () => get().metrics?.websocket?.connections || 0,

  // Get historical data for charts
  getCPUHistory: () => get().history.map(m => ({
    timestamp: m.timestamp,
    value: m.system?.cpu_percent || 0
  })),

  getMemoryHistory: () => get().history.map(m => ({
    timestamp: m.timestamp,
    value: m.system?.memory_percent || 0
  })),
}));

// Optimized selectors
export const selectMetrics = (state) => state.metrics;
export const selectCPUPercent = (state) => state.metrics?.system?.cpu_percent || 0;
export const selectMemoryPercent = (state) => state.metrics?.system?.memory_percent || 0;
export const selectTaskStats = (state) => state.metrics?.tasks || {};
export const selectServiceStats = (state) => state.metrics?.services || {};
export const selectHistory = (state) => state.history;
