/**
 * Task Executor Component
 * Allows users to create and execute tasks with manual service selection
 */
import React, { useState, useEffect } from 'react';
import { tasksAPI } from '../api/client';
import { useServices } from '../hooks/useServices';
import { useWebSocket } from '../hooks/useWebSocket';

const TaskExecutor = ({ onTaskCompleted }) => {
  const [prompt, setPrompt] = useState('');
  const [selectedService, setSelectedService] = useState('auto');
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [result, setResult] = useState('');
  const [error, setError] = useState(null);

  const { services, loading: servicesLoading } = useServices();
  const { lastMessage } = useWebSocket();

  // Listen for WebSocket updates
  useEffect(() => {
    if (!lastMessage || !currentTaskId) return;

    if (lastMessage.type === 'task_progress' && lastMessage.task_id === currentTaskId) {
      // Append streaming result
      setResult((prev) => prev + lastMessage.chunk);
    } else if (lastMessage.type === 'task_complete' && lastMessage.task_id === currentTaskId) {
      setIsExecuting(false);
      if (lastMessage.success) {
        // Task completed successfully
        if (onTaskCompleted) onTaskCompleted();
      } else {
        setError(lastMessage.error || 'Task failed');
      }
    }
  }, [lastMessage, currentTaskId, onTaskCompleted]);

  const handleExecute = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsExecuting(true);
    setResult('');
    setError(null);
    setCurrentTaskId(null);

    try {
      // Build preferences
      const preferences = {};
      if (selectedService !== 'auto') {
        preferences.preferred_service = selectedService;
      }

      // Execute task
      const response = await tasksAPI.execute(prompt, null, preferences);
      setCurrentTaskId(response.data.task_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setIsExecuting(false);
    }
  };

  const handleClear = () => {
    setPrompt('');
    setResult('');
    setError(null);
    setCurrentTaskId(null);
    setIsExecuting(false);
  };

  // Get list of healthy services
  const healthyServices = services?.services
    ? Object.entries(services.services)
        .filter(([_, service]) => service.healthy)
        .map(([name]) => name)
    : [];

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">🚀 Execute Task</h3>
      </div>

      <div style={{ padding: '20px' }}>
        {/* Service Selection */}
        <div style={{ marginBottom: '16px' }}>
          <label
            htmlFor="service-select"
            style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '0.9rem',
              fontWeight: '500',
              color: '#c9d1d9',
            }}
          >
            LLM Service
          </label>
          <select
            id="service-select"
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            disabled={isExecuting || servicesLoading}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '0.95rem',
              cursor: 'pointer',
            }}
          >
            <option value="auto">🤖 Auto (Intelligent Routing)</option>
            <optgroup label="Available Services">
              {healthyServices.map((serviceName) => (
                <option key={serviceName} value={serviceName}>
                  {serviceName}
                </option>
              ))}
            </optgroup>
            {healthyServices.length === 0 && (
              <option disabled>No healthy services available</option>
            )}
          </select>
          <div style={{ fontSize: '0.85rem', color: '#8b949e', marginTop: '4px' }}>
            {selectedService === 'auto'
              ? 'Oxide will automatically select the best service based on your query'
              : `Task will be routed to ${selectedService}`}
          </div>
        </div>

        {/* Prompt Input */}
        <div style={{ marginBottom: '16px' }}>
          <label
            htmlFor="prompt-input"
            style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '0.9rem',
              fontWeight: '500',
              color: '#c9d1d9',
            }}
          >
            Prompt
          </label>
          <textarea
            id="prompt-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isExecuting}
            placeholder="Enter your query or task description..."
            rows={4}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '0.95rem',
              fontFamily: 'inherit',
              resize: 'vertical',
            }}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
          <button
            onClick={handleExecute}
            disabled={isExecuting || !prompt.trim()}
            className="btn btn-primary"
            style={{ flex: 1 }}
          >
            {isExecuting ? '⏳ Executing...' : '▶️ Execute Task'}
          </button>
          <button
            onClick={handleClear}
            disabled={isExecuting}
            className="btn btn-secondary"
          >
            🗑️ Clear
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div
            className="error"
            style={{
              marginBottom: '16px',
              padding: '12px',
              background: '#3d1e1e',
              border: '1px solid #f85149',
              borderRadius: '6px',
            }}
          >
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Result Display */}
        {(result || isExecuting) && (
          <div>
            <div
              style={{
                marginBottom: '8px',
                fontSize: '0.9rem',
                fontWeight: '500',
                color: '#c9d1d9',
              }}
            >
              Result {isExecuting && <span style={{ color: '#58a6ff' }}>(streaming...)</span>}
            </div>
            <div
              style={{
                padding: '12px',
                background: '#0d1117',
                border: '1px solid #30363d',
                borderRadius: '6px',
                maxHeight: '300px',
                overflowY: 'auto',
                fontSize: '0.9rem',
                color: '#c9d1d9',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: 'ui-monospace, monospace',
              }}
            >
              {result || 'Waiting for response...'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskExecutor;
