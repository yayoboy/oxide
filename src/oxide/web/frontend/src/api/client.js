/**
 * API Client for Oxide Backend
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Services API
export const servicesAPI = {
  list: () => client.get('/services/'),
  get: (serviceName) => client.get(`/services/${serviceName}/`),
  healthCheck: (serviceName) => client.post(`/services/${serviceName}/health/`),
  test: (serviceName, prompt = 'Hello') =>
    client.post(`/services/${serviceName}/test/`, null, { params: { test_prompt: prompt } }),
  getModels: (serviceName) => client.get(`/services/${serviceName}/models/`),
  getRoutingRules: () => client.get('/services/routing/rules/'),
};

// Tasks API
export const tasksAPI = {
  list: (status = null, limit = 50) =>
    client.get('/tasks/', { params: { status, limit } }),
  get: (taskId) => client.get(`/tasks/${taskId}/`),
  execute: (prompt, files = null, preferences = null) =>
    client.post('/tasks/execute/', { prompt, files, preferences }),
  delete: (taskId) => client.delete(`/tasks/${taskId}/`),
  clear: (status = null) => client.post('/tasks/clear/', { status }),
};

// Monitoring API
export const monitoringAPI = {
  getMetrics: () => client.get('/monitoring/metrics/'),
  getStats: () => client.get('/monitoring/stats/'),
  healthCheck: () => client.get('/monitoring/health/'),
};

// Machines API
export const machinesAPI = {
  list: () => client.get('/machines/'),
  get: (machineId) => client.get(`/machines/${machineId}/`),
};

// API Keys API
export const apiKeysAPI = {
  getStatus: (serviceName) => client.get(`/api-keys/status/${serviceName}/`),
  testKey: (serviceName, apiKey = null) =>
    client.post('/api-keys/test/', { service: serviceName, api_key: apiKey }),
  updateKey: (serviceName, apiKey) =>
    client.post('/api-keys/update/', { service: serviceName, api_key: apiKey }),
};

// WebSocket connection
export const createWebSocket = (onMessage, onError) => {
  const ws = new WebSocket('ws://localhost:8000/ws');

  ws.onopen = () => {
    console.log('WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (onError) onError(error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };

  return ws;
};

export default client;
