/**
 * Task History Component
 * Displays recent task execution history with modern UI and WebSocket updates
 */
import React, { useState, useEffect, useCallback } from 'react';
import { tasksAPI } from '../api/client';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { formatDuration, formatTimestamp } from '../lib/utils';
import { useWebSocket } from '../hooks/useWebSocket';

const TaskHistory = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { connected, subscribe } = useWebSocket();

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const response = await tasksAPI.list(null, 10);
      setTasks(response.data.tasks || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Subscribe to task events via WebSocket
  useEffect(() => {
    if (connected) {
      // Subscribe to task_start events
      const unsubStart = subscribe('task_start', (message) => {
        // Refresh task list when a new task starts
        fetchTasks();
      });

      // Subscribe to task_complete events
      const unsubComplete = subscribe('task_complete', (message) => {
        // Refresh task list when a task completes
        fetchTasks();
      });

      // Subscribe to task_progress events
      const unsubProgress = subscribe('task_progress', (message) => {
        // Update specific task progress if needed
        setTasks(prevTasks =>
          prevTasks.map(task =>
            task.task_id === message.task_id
              ? { ...task, status: 'running' }
              : task
          )
        );
      });

      return () => {
        unsubStart();
        unsubComplete();
        unsubProgress();
      };
    }
  }, [connected, subscribe, fetchTasks]);

  const getStatusBadge = (status) => {
    const statusMap = {
      completed: 'success',
      running: 'warning',
      failed: 'error',
      queued: 'info',
    };
    return statusMap[status] || 'default';
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">📝</span>
            Recent Tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-gh-fg-muted animate-pulse">Loading tasks...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">📝</span>
            Recent Tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-gh-danger/10 border border-gh-danger rounded-md text-gh-danger">
            Error loading tasks: {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="text-2xl">📝</span>
          Recent Tasks
        </CardTitle>
        <Button variant="secondary" size="sm" onClick={fetchTasks}>
          🔄 Refresh
        </Button>
      </CardHeader>

      <CardContent>
        {tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="text-6xl mb-4 opacity-20">📭</div>
            <div className="text-gh-fg-muted">No tasks yet</div>
            <div className="text-sm text-gh-fg-subtle mt-2">
              Execute a task to see it appear here
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="p-4 bg-gh-canvas rounded-lg border border-gh-border hover:border-gh-accent-primary/50 transition-all duration-200 animate-slide-up"
              >
                {/* Task Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    <Badge variant={getStatusBadge(task.status)}>
                      {task.status}
                    </Badge>
                    {task.service && (
                      <Badge variant="default">
                        🤖 {task.service}
                      </Badge>
                    )}
                    {task.task_type && (
                      <Badge variant="outline">
                        {task.task_type}
                      </Badge>
                    )}
                    <span className="text-xs text-gh-fg-muted">
                      {formatTimestamp(task.created_at)}
                    </span>
                  </div>
                  {task.duration && (
                    <div className="flex items-center gap-1 text-xs text-gh-fg-subtle">
                      <span>⏱️</span>
                      <span>{formatDuration(task.duration)}</span>
                    </div>
                  )}
                </div>

                {/* Task Prompt */}
                <div className="text-sm text-gh-fg-DEFAULT mb-3">
                  {task.prompt?.substring(0, 150) || 'No prompt'}
                  {task.prompt?.length > 150 && (
                    <span className="text-gh-fg-subtle">...</span>
                  )}
                </div>

                {/* Task Files */}
                {task.files && task.files.length > 0 && (
                  <div className="text-xs text-gh-fg-subtle mb-2">
                    📁 {task.files.length} file(s)
                  </div>
                )}

                {/* Task Error */}
                {task.error && (
                  <div className="mt-3 p-3 bg-gh-danger/10 border border-gh-danger rounded-md text-sm text-gh-danger">
                    <div className="font-semibold mb-1">Error:</div>
                    <div className="text-xs">{task.error}</div>
                  </div>
                )}

                {/* Task Result */}
                {task.status === 'completed' && task.result && (
                  <div className="mt-3 p-3 bg-gh-canvas-subtle border border-gh-border rounded-md">
                    <div className="text-xs text-gh-fg-muted mb-2">Result:</div>
                    <div className="text-xs text-gh-fg-subtle font-mono overflow-hidden text-ellipsis">
                      {task.result.substring(0, 200)}
                      {task.result.length > 200 && (
                        <span className="text-gh-accent-primary cursor-pointer hover:underline ml-2">
                          Show more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TaskHistory;
