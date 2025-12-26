/**
 * Task Assignment Manager Component
 * Manages custom routing rules: assign specific LLM services to task types
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useServices } from '../hooks/useServices';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { FormField, Select } from './ui/Input';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './ui/Table';

const API_BASE = 'http://localhost:8000/api';

const TaskAssignmentManager = () => {
  const [rules, setRules] = useState([]);
  const [taskTypes, setTaskTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [selectedTaskType, setSelectedTaskType] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const { services } = useServices();

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
      await fetchData();
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
      await fetchData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const healthyServices = services?.services
    ? Object.entries(services.services)
        .filter(([_, service]) => service.healthy)
        .map(([name]) => name)
    : [];

  const getTaskTypeInfo = (taskTypeName) => {
    return taskTypes.find(t => t.name === taskTypeName);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="text-2xl">⚙️</span>
          Task Assignment Rules
        </CardTitle>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={fetchData}>
            🔄 Refresh
          </Button>
          {rules.length > 0 && (
            <Button variant="ghost" size="sm" onClick={handleClearAll}>
              🗑️ Clear All
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Description */}
        <p className="text-sm text-gh-fg-muted">
          Configure which LLM service handles specific task types. When a task matches a rule, it will always be routed to the assigned service.
        </p>

        {/* Success/Error Messages */}
        {success && (
          <div className="p-4 bg-gh-success/10 border border-gh-success rounded-md animate-slide-up">
            <span className="text-gh-success font-medium">✓ {success}</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-gh-danger/10 border border-gh-danger rounded-md animate-slide-up">
            <span className="text-gh-danger font-medium">✗ {error}</span>
          </div>
        )}

        {/* Add New Rule Form */}
        <div className="p-4 bg-gh-canvas border border-gh-border rounded-lg space-y-4">
          <h4 className="text-base font-semibold text-gh-fg-DEFAULT">Add New Rule</h4>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Task Type Selection */}
            <FormField
              label="Task Type"
              description={
                selectedTaskType
                  ? getTaskTypeInfo(selectedTaskType)?.description
                  : 'Select a task type'
              }
            >
              <Select
                value={selectedTaskType}
                onChange={(e) => setSelectedTaskType(e.target.value)}
                disabled={isAdding || loading}
              >
                <option value="">Select task type...</option>
                {taskTypes.map((type) => (
                  <option key={type.name} value={type.name}>
                    {type.label}
                  </option>
                ))}
              </Select>
            </FormField>

            {/* Service Selection */}
            <FormField label="Assign to Service" description="Select the LLM service">
              <Select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                disabled={isAdding || loading}
              >
                <option value="">Select service...</option>
                {healthyServices.map((service) => (
                  <option key={service} value={service}>
                    {service}
                  </option>
                ))}
              </Select>
            </FormField>

            {/* Add Button */}
            <div className="flex items-end">
              <Button
                onClick={handleAddRule}
                disabled={isAdding || !selectedTaskType || !selectedService}
                variant="primary"
                className="w-full"
              >
                {isAdding ? '⏳ Adding...' : '➕ Add Rule'}
              </Button>
            </div>
          </div>
        </div>

        {/* Existing Rules Table */}
        <div className="space-y-4">
          <h4 className="text-base font-semibold text-gh-fg-DEFAULT">
            Active Rules ({rules.length})
          </h4>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gh-fg-muted animate-pulse">Loading rules...</div>
            </div>
          ) : rules.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-6xl mb-4 opacity-20">📋</div>
              <div className="text-gh-fg-muted">No routing rules configured</div>
              <div className="text-sm text-gh-fg-subtle mt-2">
                Add rules above to assign task types to specific services
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task Type</TableHead>
                  <TableHead>Assigned Service</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => {
                  const typeInfo = getTaskTypeInfo(rule.task_type);
                  return (
                    <TableRow key={rule.task_type}>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="font-medium text-gh-fg-DEFAULT">
                            {typeInfo?.label || rule.task_type}
                          </div>
                          <div className="text-xs text-gh-fg-subtle font-mono">
                            {rule.task_type}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="info">{rule.service}</Badge>
                      </TableCell>
                      <TableCell className="text-gh-fg-subtle">
                        {typeInfo?.description || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          onClick={() => handleDeleteRule(rule.task_type)}
                          variant="ghost"
                          size="sm"
                        >
                          🗑️ Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default TaskAssignmentManager;
