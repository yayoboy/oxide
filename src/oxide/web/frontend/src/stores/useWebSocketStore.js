/**
 * WebSocket Store - Manages WebSocket connection state
 *
 * Separated from main store to prevent unnecessary re-renders
 * when WebSocket state changes.
 */
import { create } from 'zustand';

export const useWebSocketStore = create((set, get) => ({
  // State
  connected: false,
  lastMessage: null,
  connectionError: null,
  reconnectAttempts: 0,

  // Actions
  setConnected: (connected) => set({ connected }),

  setLastMessage: (message) => set({ lastMessage: message }),

  setConnectionError: (error) => set({ connectionError: error }),

  incrementReconnectAttempts: () => set((state) => ({
    reconnectAttempts: state.reconnectAttempts + 1
  })),

  resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),

  // Selectors (for optimized re-renders)
  isConnected: () => get().connected,
  getLastMessage: () => get().lastMessage,
}));

// Optimized selectors to use in components
export const selectConnected = (state) => state.connected;
export const selectLastMessage = (state) => state.lastMessage;
export const selectConnectionError = (state) => state.connectionError;
