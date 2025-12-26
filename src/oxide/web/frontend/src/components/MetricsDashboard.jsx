/**
 * Metrics Dashboard Component
 * Displays real-time system metrics with modern UI
 */
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { MetricCard, ProgressBar } from './ui/MetricCard';
import { Badge } from './ui/Badge';
import { getPercentageColor } from '../lib/utils';

const MetricsDashboard = ({ metrics }) => {
  if (!metrics) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gh-fg-muted animate-pulse">Loading metrics...</div>
      </div>
    );
  }

  const { services, tasks, system, websocket } = metrics;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* Services Overview */}
      <Card variant="interactive">
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">🔧</span>
            Services
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Enabled"
              value={services?.enabled || 0}
              valueColor="text-gh-success"
              icon="✓"
            />
            <MetricCard
              label="Healthy"
              value={services?.healthy || 0}
              valueColor="text-gh-accent-primary"
              icon="💚"
            />
          </div>
          {services?.unhealthy > 0 && (
            <div className="mt-4 p-3 bg-gh-danger/10 border border-gh-danger rounded-md">
              <p className="text-sm text-gh-danger font-medium">
                ⚠️ {services.unhealthy} service(s) unavailable
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tasks Overview */}
      <Card variant="interactive">
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">📊</span>
            Tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Completed"
              value={tasks?.completed || 0}
              valueColor="text-gh-success"
            />
            <MetricCard
              label="Running"
              value={tasks?.running || 0}
              valueColor="text-gh-attention"
            />
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="space-y-1">
              <span className="text-xs text-gh-fg-muted">Total</span>
              <div className="text-xl font-semibold text-gh-fg-muted">{tasks?.total || 0}</div>
            </div>
            <div className="space-y-1">
              <span className="text-xs text-gh-fg-muted">Failed</span>
              <div className="text-xl font-semibold text-gh-danger">{tasks?.failed || 0}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Resources */}
      <Card variant="interactive">
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">💻</span>
            System
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gh-fg-muted">CPU Usage</span>
              <span className={`text-lg font-bold ${getPercentageColor(system?.cpu_percent)}`}>
                {system?.cpu_percent?.toFixed(1) || 0}%
              </span>
            </div>
            <ProgressBar
              value={system?.cpu_percent || 0}
              variant={
                system?.cpu_percent < 50 ? 'success' :
                system?.cpu_percent < 75 ? 'warning' : 'danger'
              }
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gh-fg-muted">Memory Usage</span>
              <span className={`text-lg font-bold ${getPercentageColor(system?.memory_percent, { low: 60, medium: 80 })}`}>
                {system?.memory_percent?.toFixed(1) || 0}%
              </span>
            </div>
            <ProgressBar
              value={system?.memory_percent || 0}
              variant={
                system?.memory_percent < 60 ? 'success' :
                system?.memory_percent < 80 ? 'warning' : 'danger'
              }
            />
            <div className="text-xs text-gh-fg-subtle text-right">
              {system?.memory_used_mb?.toFixed(0) || 0} MB / {system?.memory_total_mb?.toFixed(0) || 0} MB
            </div>
          </div>
        </CardContent>
      </Card>

      {/* WebSocket Status */}
      <Card variant="interactive">
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">🔌</span>
            WebSocket
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MetricCard
            label="Active Connections"
            value={websocket?.connections || 0}
            valueColor="text-gh-accent-primary"
          />
          <div className="mt-4 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${websocket?.connections > 0 ? 'bg-gh-success animate-pulse' : 'bg-gh-fg-subtle'}`} />
            <span className="text-sm text-gh-fg-muted">
              Real-time updates {websocket?.connections > 0 ? 'enabled' : 'disabled'}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MetricsDashboard;
