/**
 * Tasks Store - Manages task execution state
 *
 * Handles task history, current executing tasks, and results.
 * Separated for performance - task list can be large.
 */
import { create } from 'zustand';

export const useTasksStore = create((set, get) => ({
  // State
  tasks: [],
  currentTaskId: null,
  currentResult: '',
  loading: false,
  error: null,

  // Actions
  setTasks: (tasks) => set({ tasks }),

  addTask: (task) => set((state) => ({
    tasks: [task, ...state.tasks] // Prepend new tasks
  })),

  updateTask: (taskId, updates) => set((state) => ({
    tasks: state.tasks.map(task =>
      task.id === taskId ? { ...task, ...updates } : task
    )
  })),

  removeTask: (taskId) => set((state) => ({
    tasks: state.tasks.filter(task => task.id !== taskId)
  })),

  clearTasks: () => set({
    tasks: [],
    currentTaskId: null,
    currentResult: ''
  }),

  // Current task execution
  setCurrentTaskId: (taskId) => set({
    currentTaskId: taskId,
    currentResult: '',
    error: null
  }),

  appendToCurrentResult: (chunk) => set((state) => ({
    currentResult: state.currentResult + chunk
  })),

  setCurrentResult: (result) => set({ currentResult: result }),

  clearCurrentTask: () => set({
    currentTaskId: null,
    currentResult: '',
    error: null
  }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error, loading: false }),

  // Computed/Selectors
  getTaskById: (taskId) => {
    return get().tasks.find(task => task.id === taskId);
  },

  getTasksByStatus: (status) => {
    return get().tasks.filter(task => task.status === status);
  },

  getTasksByService: (serviceName) => {
    return get().tasks.filter(task => task.service === serviceName);
  },

  getRecentTasks: (limit = 10) => {
    return get().tasks.slice(0, limit);
  },

  getTaskStats: () => {
    const tasks = get().tasks;
    return {
      total: tasks.length,
      completed: tasks.filter(t => t.status === 'completed').length,
      running: tasks.filter(t => t.status === 'running').length,
      failed: tasks.filter(t => t.status === 'failed').length,
      queued: tasks.filter(t => t.status === 'queued').length
    };
  }
}));

// Optimized selectors
export const selectTasks = (state) => state.tasks;
export const selectCurrentTaskId = (state) => state.currentTaskId;
export const selectCurrentResult = (state) => state.currentResult;
export const selectLoading = (state) => state.loading;
export const selectError = (state) => state.error;
export const selectRecentTasks = (limit = 10) => (state) => state.tasks.slice(0, limit);
export const selectTasksByStatus = (status) => (state) =>
  state.tasks.filter(task => task.status === status);
