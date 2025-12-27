/**
 * Ultra Compact Dashboard
 * Maximum information density with enhanced visual hierarchy
 * Combines service matrix, LLM metrics, and system stats in minimal space
 */
import React, { useState } from 'react';
import { ServiceHealthMatrix } from './ui/ServiceHealthMatrix';
import { EnhancedLLMMetrics } from './ui/EnhancedLLMMetrics';
import { CompactSystemBar } from './ui/CompactSystemBar';
import { MetricPill } from './ui/MetricPill';
import { cn } from '../lib/utils';

/**
 * Quick Stats Bar - Inline metrics at a glance
 */
const QuickStatsBar = ({ services, metrics }) => {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Services */}
      <MetricPill
        icon="🔧"
        label="Services"
        value={`${services?.healthy || 0}/${services?.total || 0}`}
        status={services?.healthy === services?.total ? 'success' : 'warning'}
      />

      {/* Active Tasks */}
      <MetricPill
        icon="⚡"
        label="Active"
        value={metrics?.active_tasks || 0}
        status="info"
      />

      {/* Total Executions */}
      <MetricPill
        icon="📊"
        label="Total"
        value={metrics?.total_executions || 0}
        status="neutral"
      />

      {/* Success Rate */}
      {metrics?.success_rate !== undefined && (
        <MetricPill
          icon="✅"
          label="Success"
          value={`${metrics.success_rate.toFixed(0)}%`}
          status={metrics.success_rate > 95 ? 'success' : 'warning'}
        />
      )}

      {/* Average Response Time */}
      {metrics?.avg_response_time_ms !== undefined && (
        <MetricPill
          icon="⏱️"
          label="Avg Time"
          value={`${metrics.avg_response_time_ms.toFixed(0)}ms`}
          status="neutral"
        />
      )}
    </div>
  );
};

/**
 * Compact Provider Stats - Counts by type
 */
const ProviderStats = ({ services }) => {
  const categorize = () => {
    if (!services?.services) return { cli: 0, local: 0, remote: 0 };

    const counts = { cli: 0, local: 0, remote: 0 };

    Object.values(services.services).forEach((status) => {
      const info = status.info || {};
      if (info.type === 'cli') {
        counts.cli++;
      } else if (info.type === 'http') {
        const baseUrl = info.base_url || '';
        if (baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1')) {
          counts.local++;
        } else {
          counts.remote++;
        }
      }
    });

    return counts;
  };

  const counts = categorize();

  const StatItem = ({ icon, label, count, color }) => (
    <div className={cn(
      "flex items-center gap-2 px-3 py-1.5 rounded-lg border",
      `bg-${color}-500/10 border-${color}-500/30`
    )}>
      <span className="text-sm">{icon}</span>
      <span className="text-xs text-gh-fg-muted">{label}:</span>
      <span className={cn("text-sm font-bold", `text-${color}-400`)}>
        {count}
      </span>
    </div>
  );

  return (
    <div className="flex items-center gap-2">
      <StatItem icon="⚡" label="CLI" count={counts.cli} color="blue" />
      <StatItem icon="🏠" label="Local" count={counts.local} color="green" />
      <StatItem icon="🌐" label="Remote" count={counts.remote} color="purple" />
    </div>
  );
};

/**
 * Layout Toggle Component
 */
const LayoutToggle = ({ layout, onChange }) => {
  const options = [
    { value: 'matrix', icon: '⊞', label: 'Matrix' },
    { value: 'list', icon: '☰', label: 'List' },
    { value: 'hybrid', icon: '⊟', label: 'Hybrid' }
  ];

  return (
    <div className="flex items-center gap-1 glass rounded-lg p-1">
      {options.map(option => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "px-3 py-1 rounded text-xs font-medium transition-all",
            layout === option.value
              ? 'bg-cyan-500/30 text-cyan-400'
              : 'text-gh-fg-muted hover:text-white hover:bg-white/5'
          )}
          title={option.label}
        >
          <span className="mr-1">{option.icon}</span>
          {option.label}
        </button>
      ))}
    </div>
  );
};

/**
 * Main Ultra Compact Dashboard Component
 */
export const UltraCompactDashboard = ({ services, metrics }) => {
  const [layout, setLayout] = useState('matrix'); // matrix | list | hybrid
  const [showLLMMetrics, setShowLLMMetrics] = useState(true);

  const systemMetrics = metrics?.system || {};
  const llmMetrics = metrics?.llm || {};

  return (
    <div className="space-y-4" data-testid="dashboard">
      {/* Top control bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4" data-testid="quick-stats">
        {/* Quick stats */}
        <QuickStatsBar services={services} metrics={metrics} />

        {/* Layout controls */}
        <div className="flex items-center gap-3">
          {/* WebSocket indicator */}
          <div
            className="flex items-center gap-1.5 glass rounded-lg px-2 py-1 border border-cyan-500/30"
            data-testid="ws-indicator"
            title="WebSocket Connection"
          >
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs text-cyan-400 font-medium">Live</span>
          </div>

          <ProviderStats services={services} />
          <LayoutToggle layout={layout} onChange={setLayout} />
        </div>
      </div>

      {/* System metrics bar */}
      <CompactSystemBar system={systemMetrics} />

      {/* LLM Metrics - Collapsible */}
      {llmMetrics && Object.keys(llmMetrics).length > 0 && (
        <div className="relative">
          <button
            onClick={() => setShowLLMMetrics(!showLLMMetrics)}
            className="absolute top-2 right-2 z-10 glass rounded-lg px-2 py-1 text-xs text-gh-fg-muted hover:text-white transition-colors"
          >
            {showLLMMetrics ? '▼ Hide' : '▶ Show'} Metrics
          </button>

          {showLLMMetrics && (
            <div data-testid="llm-metrics">
              <EnhancedLLMMetrics
                llmMetrics={llmMetrics}
                layout={layout === 'matrix' ? 'grid' : 'compact'}
              />
            </div>
          )}
        </div>
      )}

      {/* Services visualization - Layout dependent */}
      {layout === 'matrix' && (
        <ServiceHealthMatrix services={services} />
      )}

      {layout === 'list' && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Services List View</h3>
          {/* Import and use original CompactDashboard provider sections here */}
          <div className="text-sm text-gh-fg-muted">
            List view - Use original CompactDashboard sections
          </div>
        </div>
      )}

      {layout === 'hybrid' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ServiceHealthMatrix services={services} />
          <div className="glass rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Recent Activity</h3>
            <div className="text-sm text-gh-fg-muted">
              Recent tasks and executions
            </div>
          </div>
        </div>
      )}

      {/* Footer stats */}
      <div className="glass rounded-lg p-3 flex items-center justify-between text-xs text-gh-fg-muted">
        <div>
          Last updated: {new Date().toLocaleTimeString()}
        </div>
        <div className="flex items-center gap-4">
          <span>Uptime: 99.9%</span>
          <span>Avg Response: {metrics?.avg_response_time_ms?.toFixed(0) || 0}ms</span>
        </div>
      </div>
    </div>
  );
};

export default UltraCompactDashboard;
