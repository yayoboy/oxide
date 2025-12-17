/**
 * Task History Component
 * Displays recent task execution history
 */
import React, { useState, useEffect } from 'react';
import { tasksAPI } from '../api/client';

const TaskHistory = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTasks = async () => {
    try {
      const response = await tasksAPI.list(null, 10);
      setTasks(response.data.tasks || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();

    // Refresh every 3 seconds
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status) => {
    const statusMap = {
      completed: { class: 'badge-success', label: 'Completed' },
      running: { class: 'badge-warning', label: 'Running' },
      failed: { class: 'badge-error', label: 'Failed' },
      queued: { class: 'badge-info', label: 'Queued' },
    };

    const config = statusMap[status] || { class: 'badge-info', label: status };
    return <span className={`badge ${config.class}`}>{config.label}</span>;
  };

  const formatDuration = (duration) => {
    if (!duration) return 'N/A';
    if (duration < 1) return `${(duration * 1000).toFixed(0)}ms`;
    return `${duration.toFixed(2)}s`;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
  };

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">📝 Recent Tasks</h3>
        </div>
        <div className="loading">Loading tasks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">📝 Recent Tasks</h3>
        </div>
        <div className="error">Error loading tasks: {error}</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">📝 Recent Tasks</h3>
        <button className="btn btn-secondary" onClick={fetchTasks}>
          Refresh
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <div>No tasks yet</div>
        </div>
      ) : (
        <div>
          {tasks.map((task) => (
            <div key={task.id} className="task-item">
              <div className="task-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {getStatusBadge(task.status)}
                  <span className="task-meta">
                    {formatTimestamp(task.created_at)}
                  </span>
                </div>
                {task.duration && (
                  <span className="task-meta">
                    ⏱️ {formatDuration(task.duration)}
                  </span>
                )}
              </div>

              <div className="task-prompt">
                {task.prompt?.substring(0, 150) || 'No prompt'}
                {task.prompt?.length > 150 && '...'}
              </div>

              {task.files && task.files.length > 0 && (
                <div className="task-meta" style={{ marginTop: '8px' }}>
                  📁 {task.files.length} file(s)
                </div>
              )}

              {task.error && (
                <div className="error" style={{ marginTop: '10px', fontSize: '0.85rem' }}>
                  {task.error}
                </div>
              )}

              {task.status === 'completed' && task.result && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '10px',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                    color: '#8b949e',
                    maxHeight: '100px',
                    overflow: 'hidden',
                  }}
                >
                  {task.result.substring(0, 200)}
                  {task.result.length > 200 && '...'}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TaskHistory;
