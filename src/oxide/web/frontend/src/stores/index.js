/**
 * Central export for all Zustand stores
 *
 * Import stores like:
 * import { useWebSocketStore, useServicesStore } from '@/stores';
 */

// Export stores
export { useWebSocketStore, selectConnected, selectLastMessage, selectConnectionError } from './useWebSocketStore';
export { useServicesStore, selectServices, selectLoading, selectError, selectServiceByName, selectHealthyServices } from './useServicesStore';
export { useMetricsStore, selectMetrics, selectCPUPercent, selectMemoryPercent, selectTaskStats, selectServiceStats, selectHistory } from './useMetricsStore';
export { useTasksStore, selectTasks, selectCurrentTaskId, selectCurrentResult, selectLoading as selectTasksLoading, selectError as selectTasksError, selectRecentTasks, selectTasksByStatus } from './useTasksStore';
export { useUIStore, selectTheme, selectIsDarkMode, selectSidebarCollapsed, selectNotifications, selectUnreadNotifications, selectPreferredService, selectAutoRefreshEnabled, selectRefreshInterval } from './useUIStore';
