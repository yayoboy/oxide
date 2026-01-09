/**
 * UI Store - Manages UI state (theme, notifications, preferences)
 *
 * Handles user preferences and UI-only state.
 * Persisted to localStorage for consistency across sessions.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useUIStore = create(
  persist(
    (set, get) => ({
      // State
      theme: 'dark', // 'light' | 'dark'
      sidebarCollapsed: false,
      notifications: [],
      preferredService: 'auto',
      autoRefreshEnabled: true,
      refreshInterval: 3000, // ms

      // Actions
      setTheme: (theme) => set({ theme }),

      toggleTheme: () => set((state) => ({
        theme: state.theme === 'dark' ? 'light' : 'dark'
      })),

      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      toggleSidebar: () => set((state) => ({
        sidebarCollapsed: !state.sidebarCollapsed
      })),

      // Notifications
      addNotification: (notification) => set((state) => ({
        notifications: [
          ...state.notifications,
          {
            id: Date.now(),
            timestamp: Date.now(),
            ...notification
          }
        ]
      })),

      removeNotification: (id) => set((state) => ({
        notifications: state.notifications.filter(n => n.id !== id)
      })),

      clearNotifications: () => set({ notifications: [] }),

      // Preferences
      setPreferredService: (service) => set({ preferredService: service }),

      setAutoRefreshEnabled: (enabled) => set({ autoRefreshEnabled: enabled }),

      setRefreshInterval: (interval) => set({ refreshInterval: interval }),

      // Computed
      isDarkMode: () => get().theme === 'dark',

      getUnreadNotifications: () => {
        return get().notifications.filter(n => !n.read);
      },

      getNotificationCount: () => {
        return get().getUnreadNotifications().length;
      }
    }),
    {
      name: 'oxide-ui-storage',
      // Persist all UI preferences
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        preferredService: state.preferredService,
        autoRefreshEnabled: state.autoRefreshEnabled,
        refreshInterval: state.refreshInterval
      }),
      version: 1
    }
  )
);

// Optimized selectors
export const selectTheme = (state) => state.theme;
export const selectIsDarkMode = (state) => state.theme === 'dark';
export const selectSidebarCollapsed = (state) => state.sidebarCollapsed;
export const selectNotifications = (state) => state.notifications;
export const selectUnreadNotifications = (state) =>
  state.notifications.filter(n => !n.read);
export const selectPreferredService = (state) => state.preferredService;
export const selectAutoRefreshEnabled = (state) => state.autoRefreshEnabled;
export const selectRefreshInterval = (state) => state.refreshInterval;
