/**
 * Task Assignment Manager Component
 * Manages custom routing rules: assign specific LLM services to task types
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useServices } from '../hooks/useServices';

const API_BASE = 'http://localhost:8000/api';

const TaskAssignmentManager = () => {
  const [rules, setRules] = useState([]);
  const [taskTypes, setTaskTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Form state
  const [selectedTaskType, setSelectedTaskType] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const { services } = useServices();

  // Fetch routing rules and task types
  const fetchData = async () => {
    try {
      setLoading(true);
      const [rulesRes, typesRes] = await Promise.all([
        axios.get(`${API_BASE}/routing/rules`),
        axios.get(`${API_BASE}/routing/task-types`)
      ]);

      setRules(rulesRes.data.rules || []);
      setTaskTypes(typesRes.data.task_types || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddRule = async () => {
    if (!selectedTaskType || !selectedService) {
      setError('Please select both task type and service');
      return;
    }

    try {
      setIsAdding(true);
      await axios.post(`${API_BASE}/routing/rules`, {
        task_type: selectedTaskType,
        service: selectedService
      });

      setSuccess(`Rule added: ${selectedTaskType} → ${selectedService}`);
      setSelectedTaskType('');
      setSelectedService('');

      // Refresh rules
      await fetchData();

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteRule = async (taskType) => {
    if (!confirm(`Delete routing rule for "${taskType}"?`)) return;

    try {
      await axios.delete(`${API_BASE}/routing/rules/${taskType}`);
      setSuccess(`Rule deleted: ${taskType}`);

      // Refresh rules
      await fetchData();

      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Clear all routing rules?')) return;

    try {
      await axios.post(`${API_BASE}/routing/rules/clear`);
      setSuccess('All routing rules cleared');

      // Refresh rules
      await fetchData();

      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  // Get healthy services for dropdown
  const healthyServices = services?.services
    ? Object.entries(services.services)
        .filter(([_, service]) => service.healthy)
        .map(([name]) => name)
    : [];

  // Get task type info
  const getTaskTypeInfo = (taskTypeName) => {
    return taskTypes.find(t => t.name === taskTypeName);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">⚙️ Task Assignment Rules</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={fetchData}
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem' }}
          >
            🔄 Refresh
          </button>
          {rules.length > 0 && (
            <button
              onClick={handleClearAll}
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem' }}
            >
              🗑️ Clear All
            </button>
          )}
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {/* Description */}
        <p style={{ color: '#8b949e', marginBottom: '20px', fontSize: '0.9rem' }}>
          Configure which LLM service handles specific task types. When a task matches a rule, it will always be routed to the assigned service.
        </p>

        {/* Success/Error Messages */}
        {success && (
          <div
            style={{
              marginBottom: '16px',
              padding: '12px',
              background: '#1e3d1e',
              border: '1px solid #3fb950',
              borderRadius: '6px',
              color: '#3fb950',
            }}
          >
            ✓ {success}
          </div>
        )}

        {error && (
          <div
            style={{
              marginBottom: '16px',
              padding: '12px',
              background: '#3d1e1e',
              border: '1px solid #f85149',
              borderRadius: '6px',
              color: '#f85149',
            }}
          >
            ✗ {error}
          </div>
        )}

        {/* Add New Rule Form */}
        <div
          style={{
            marginBottom: '24px',
            padding: '16px',
            background: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '6px',
          }}
        >
          <h4 style={{ marginBottom: '16px', fontSize: '1rem' }}>Add New Rule</h4>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '12px', alignItems: 'end' }}>
            {/* Task Type Selection */}
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c9d1d9' }}>
                Task Type
              </label>
              <select
                value={selectedTaskType}
                onChange={(e) => setSelectedTaskType(e.target.value)}
                disabled={isAdding || loading}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#c9d1d9',
                  fontSize: '0.95rem',
                }}
              >
                <option value="">Select task type...</option>
                {taskTypes.map((type) => (
                  <option key={type.name} value={type.name}>
                    {type.label}
                  </option>
                ))}
              </select>
              {selectedTaskType && (
                <div style={{ fontSize: '0.8rem', color: '#8b949e', marginTop: '4px' }}>
                  {getTaskTypeInfo(selectedTaskType)?.description}
                </div>
              )}
            </div>

            {/* Service Selection */}
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c9d1d9' }}>
                Assign to Service
              </label>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                disabled={isAdding || loading}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#c9d1d9',
                  fontSize: '0.95rem',
                }}
              >
                <option value="">Select service...</option>
                {healthyServices.map((service) => (
                  <option key={service} value={service}>
                    {service}
                  </option>
                ))}
              </select>
            </div>

            {/* Add Button */}
            <button
              onClick={handleAddRule}
              disabled={isAdding || !selectedTaskType || !selectedService}
              className="btn btn-primary"
              style={{ padding: '10px 20px' }}
            >
              {isAdding ? '⏳ Adding...' : '➕ Add Rule'}
            </button>
          </div>
        </div>

        {/* Existing Rules Table */}
        <div>
          <h4 style={{ marginBottom: '16px', fontSize: '1rem' }}>
            Active Rules ({rules.length})
          </h4>

          {loading ? (
            <div className="loading">Loading rules...</div>
          ) : rules.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div>No routing rules configured</div>
              <div style={{ fontSize: '0.85rem', color: '#8b949e', marginTop: '8px' }}>
                Add rules above to assign task types to specific services
              </div>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d' }}>
                    <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9rem', color: '#8b949e' }}>
                      Task Type
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9rem', color: '#8b949e' }}>
                      Assigned Service
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.9rem', color: '#8b949e' }}>
                      Description
                    </th>
                    <th style={{ padding: '12px', textAlign: 'right', fontSize: '0.9rem', color: '#8b949e' }}>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => {
                    const typeInfo = getTaskTypeInfo(rule.task_type);
                    return (
                      <tr
                        key={rule.task_type}
                        style={{ borderBottom: '1px solid #21262d' }}
                      >
                        <td style={{ padding: '12px' }}>
                          <div style={{ fontWeight: '500', color: '#c9d1d9' }}>
                            {typeInfo?.label || rule.task_type}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#8b949e' }}>
                            {rule.task_type}
                          </div>
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span
                            style={{
                              padding: '4px 12px',
                              background: '#1f6feb',
                              color: 'white',
                              borderRadius: '12px',
                              fontSize: '0.85rem',
                              fontWeight: '500',
                            }}
                          >
                            {rule.service}
                          </span>
                        </td>
                        <td style={{ padding: '12px', fontSize: '0.85rem', color: '#8b949e' }}>
                          {typeInfo?.description || '-'}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleDeleteRule(rule.task_type)}
                            className="btn btn-secondary"
                            style={{ fontSize: '0.85rem', padding: '6px 12px' }}
                          >
                            🗑️ Delete
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskAssignmentManager;
