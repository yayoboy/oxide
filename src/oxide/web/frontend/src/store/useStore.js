/**
 * Global State Store using Zustand
 *
 * Centralized state management for the Oxide dashboard.
 * Provides reactive state updates across components without prop drilling.
 */
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

const useStore = create(
  devtools(
    persist(
      (set, get) => ({
        // WebSocket State
        wsConnected: false,
        wsError: null,
        setWsConnected: (connected) => set({ wsConnected: connected }),
        setWsError: (error) => set({ wsError: error }),

        // Services State
        services: null,
        servicesLoading: true,
        servicesError: null,
        setServices: (services) =>
          set({ services, servicesLoading: false, servicesError: null }),
        setServicesLoading: (loading) => set({ servicesLoading: loading }),
        setServicesError: (error) => set({ servicesError: error, servicesLoading: false }),

        // Metrics State
        metrics: null,
        metricsLoading: true,
        metricsError: null,
        setMetrics: (metrics) =>
          set({ metrics, metricsLoading: false, metricsError: null }),
        setMetricsLoading: (loading) => set({ metricsLoading: loading }),
        setMetricsError: (error) => set({ metricsError: error, metricsLoading: false }),

        // Tasks State
        tasks: [],
        tasksLoading: false,
        tasksError: null,
        setTasks: (tasks) => set({ tasks, tasksLoading: false, tasksError: null }),
        setTasksLoading: (loading) => set({ tasksLoading: loading }),
        setTasksError: (error) => set({ tasksError: error, tasksLoading: false }),

        // Add a task
        addTask: (task) =>
          set((state) => ({ tasks: [task, ...state.tasks] })),

        // Update a task
        updateTask: (taskId, updates) =>
          set((state) => ({
            tasks: state.tasks.map((task) =>
              task.task_id === taskId ? { ...task, ...updates } : task
            ),
          })),

        // Remove a task
        removeTask: (taskId) =>
          set((state) => ({
            tasks: state.tasks.filter((task) => task.task_id !== taskId),
          })),

        // Notifications State
        notifications: [],
        addNotification: (notification) =>
          set((state) => ({
            notifications: [
              ...state.notifications,
              { id: Date.now(), ...notification },
            ],
          })),
        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          })),
        clearNotifications: () => set({ notifications: [] }),

        // UI State
        selectedTab: 'dashboard',
        setSelectedTab: (tab) => set({ selectedTab: tab }),

        sidebarOpen: true,
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setSidebarOpen: (open) => set({ sidebarOpen: open }),

        // Cluster/Machines State
        machines: [],
        machinesLoading: false,
        machinesError: null,
        setMachines: (machines) =>
          set({ machines, machinesLoading: false, machinesError: null }),
        setMachinesLoading: (loading) => set({ machinesLoading: loading }),
        setMachinesError: (error) => set({ machinesError: error, machinesLoading: false }),

        // User Preferences (persisted)
        preferences: {
          compactView: false,
          autoRefresh: true,
          showSystemMetrics: true,
          notificationsEnabled: true,
        },
        setPreference: (key, value) =>
          set((state) => ({
            preferences: { ...state.preferences, [key]: value },
          })),
        setPreferences: (preferences) => set({ preferences }),

        // Global Actions
        reset: () =>
          set({
            services: null,
            metrics: null,
            tasks: [],
            machines: [],
            notifications: [],
            wsConnected: false,
            wsError: null,
          }),
      }),
      {
        name: 'oxide-storage', // localStorage key
        partialize: (state) => ({
          // Only persist these fields
          preferences: state.preferences,
          selectedTab: state.selectedTab,
          sidebarOpen: state.sidebarOpen,
        }),
      }
    ),
    { name: 'Oxide Store' } // Redux DevTools name
  )
);

// Selectors for optimized access
export const selectors = {
  // WebSocket
  useWsStatus: () => useStore((state) => ({
    connected: state.wsConnected,
    error: state.wsError,
  })),

  // Services
  useServices: () => useStore((state) => ({
    services: state.services,
    loading: state.servicesLoading,
    error: state.servicesError,
  })),

  // Metrics
  useMetrics: () => useStore((state) => ({
    metrics: state.metrics,
    loading: state.metricsLoading,
    error: state.metricsError,
  })),

  // Tasks
  useTasks: () => useStore((state) => ({
    tasks: state.tasks,
    loading: state.tasksLoading,
    error: state.tasksError,
  })),

  // UI
  useUI: () => useStore((state) => ({
    selectedTab: state.selectedTab,
    sidebarOpen: state.sidebarOpen,
  })),

  // Preferences
  usePreferences: () => useStore((state) => state.preferences),
};

export default useStore;
