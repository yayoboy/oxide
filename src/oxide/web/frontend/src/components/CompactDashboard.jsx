/**
 * Compact Dashboard - Unified view with provider separation
 * Displays CLI, Local, and Remote providers separately with immediate metrics
 */
import React from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { StatusIndicator } from './ui/StatusIndicator';
import { MetricCard } from './ui/MetricCard';

const CompactDashboard = ({ services, metrics }) => {
  // Categorize services by type
  const categorizeServices = () => {
    if (!services?.services) return { cli: [], local: [], remote: [] };

    const categories = { cli: [], local: [], remote: [] };

    Object.entries(services.services).forEach(([name, status]) => {
      const info = status.info || {};

      if (info.type === 'cli') {
        categories.cli.push({ name, ...status });
      } else if (info.type === 'http') {
        // Determine if local or remote based on URL
        const baseUrl = info.base_url || '';
        if (baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1')) {
          categories.local.push({ name, ...status });
        } else {
          categories.remote.push({ name, ...status });
        }
      }
    });

    return categories;
  };

  const { cli, local, remote } = categorizeServices();

  // Extract system and LLM metrics
  const systemMetrics = metrics?.system || {};
  const llmMetrics = metrics?.llm || {};

  return (
    <div className="space-y-6">
      {/* Top-level Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Services"
          value={services?.total || 0}
          subtitle={`${services?.healthy || 0} healthy`}
          status={services?.healthy === services?.total ? 'success' : 'warning'}
          icon="🔧"
        />
        <MetricCard
          title="Active Tasks"
          value={metrics?.active_tasks || 0}
          subtitle="executing now"
          status="info"
          icon="⚡"
        />
        <MetricCard
          title="Total Executions"
          value={metrics?.total_executions || 0}
          subtitle="all time"
          status="neutral"
          icon="📊"
        />
        <MetricCard
          title="System Load"
          value={`${systemMetrics.cpu_percent || 0}%`}
          subtitle={`${systemMetrics.memory_percent || 0}% RAM`}
          status={systemMetrics.cpu_percent > 80 ? 'error' : 'success'}
          icon="💻"
        />
      </div>

      {/* Services Grid - Separated by Type */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* CLI Providers */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="text-2xl">💻</div>
              <h3 className="text-lg font-semibold">CLI Providers</h3>
            </div>
            <Badge variant={cli.length > 0 ? 'success' : 'secondary'}>
              {cli.length}
            </Badge>
          </div>
          <div className="space-y-3">
            {cli.length > 0 ? (
              cli.map((service) => (
                <ServiceRow key={service.name} service={service} />
              ))
            ) : (
              <EmptyState icon="💻" text="No CLI providers" />
            )}
          </div>
        </Card>

        {/* Local Providers */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="text-2xl">🏠</div>
              <h3 className="text-lg font-semibold">Local Providers</h3>
            </div>
            <Badge variant={local.length > 0 ? 'success' : 'secondary'}>
              {local.length}
            </Badge>
          </div>
          <div className="space-y-3">
            {local.length > 0 ? (
              local.map((service) => (
                <ServiceRow key={service.name} service={service} showMetrics />
              ))
            ) : (
              <EmptyState icon="🏠" text="No local providers" />
            )}
          </div>
        </Card>

        {/* Remote Providers */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="text-2xl">🌐</div>
              <h3 className="text-lg font-semibold">Remote Providers</h3>
            </div>
            <Badge variant={remote.length > 0 ? 'success' : 'secondary'}>
              {remote.length}
            </Badge>
          </div>
          <div className="space-y-3">
            {remote.length > 0 ? (
              remote.map((service) => (
                <ServiceRow key={service.name} service={service} showMetrics />
              ))
            ) : (
              <EmptyState icon="🌐" text="No remote providers" />
            )}
          </div>
        </Card>
      </div>

      {/* LLM Metrics Section */}
      {llmMetrics && Object.keys(llmMetrics).length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="text-2xl">🤖</div>
            <h3 className="text-lg font-semibold">LLM Performance Metrics</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(llmMetrics).map(([key, value]) => (
              <div key={key} className="text-center">
                <div className="text-2xl font-bold text-cyan-400">{value}</div>
                <div className="text-sm text-gh-fg-muted capitalize">
                  {key.replace(/_/g, ' ')}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

/**
 * Compact service row component
 */
const ServiceRow = ({ service, showMetrics = false }) => {
  const { name, healthy, info } = service;
  const model = info?.default_model || info?.model || 'auto-detect';

  return (
    <div className="glass rounded-lg p-3 hover:bg-white/5 transition-all group">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <StatusIndicator status={healthy ? 'online' : 'offline'} size="sm" />
          <span className="font-medium text-sm truncate">{name}</span>
        </div>
        <Badge variant={healthy ? 'success' : 'error'} size="sm">
          {healthy ? 'UP' : 'DOWN'}
        </Badge>
      </div>

      {/* Model Info */}
      <div className="text-xs text-gh-fg-muted truncate mb-1">
        Model: {model}
      </div>

      {/* Metrics for HTTP services */}
      {showMetrics && healthy && info?.base_url && (
        <div className="flex items-center gap-3 text-xs text-gh-fg-muted mt-2 pt-2 border-t border-white/5">
          <div className="flex items-center gap-1">
            <span className="text-cyan-400">⚡</span>
            <span>~0ms</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-purple-400">📊</span>
            <span>Ready</span>
          </div>
        </div>
      )}

      {/* Base URL for HTTP services */}
      {info?.base_url && (
        <div className="text-xs text-gh-fg-muted truncate opacity-0 group-hover:opacity-100 transition-opacity">
          {info.base_url}
        </div>
      )}
    </div>
  );
};

/**
 * Empty state component
 */
const EmptyState = ({ icon, text }) => (
  <div className="text-center py-8 opacity-40">
    <div className="text-4xl mb-2">{icon}</div>
    <div className="text-sm text-gh-fg-muted">{text}</div>
  </div>
);

export default CompactDashboard;
