/**
 * Compact Dashboard - Unified view with provider separation
 * Displays CLI, Local, and Remote providers separately with immediate metrics
 * Enhanced with visual provider themes and compact layout
 */
import React from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { StatusIndicator } from './ui/StatusIndicator';
import { MetricCard } from './ui/MetricCard';
import { MetricPill } from './ui/MetricPill';
import { CompactSystemBar } from './ui/CompactSystemBar';
import { LLMMetricsPanel } from './ui/LLMMetricsPanel';
import { cn } from '../lib/utils';

// Provider visual themes for clear separation
const PROVIDER_THEMES = {
  cli: {
    gradient: 'from-blue-500 to-cyan-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    icon: '⚡',
    label: 'CLI Providers',
    subtitle: 'Direct command-line tools'
  },
  local: {
    gradient: 'from-green-500 to-emerald-500',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    icon: '🏠',
    label: 'Local Services',
    subtitle: 'Running on this machine'
  },
  remote: {
    gradient: 'from-purple-500 to-magenta-500',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    icon: '🌐',
    label: 'Remote Services',
    subtitle: 'External API endpoints'
  }
};

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
    <div className="space-y-4">
      {/* Compact top bar with key metrics + system status */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <MetricPill
            icon="🔧"
            label="Services"
            value={`${services?.healthy || 0}/${services?.total || 0}`}
            status={services?.healthy === services?.total ? 'success' : 'warning'}
          />
          <MetricPill
            icon="⚡"
            label="Active"
            value={metrics?.active_tasks || 0}
            status="info"
          />
          <MetricPill
            icon="📊"
            label="Total"
            value={metrics?.total_executions || 0}
            status="neutral"
          />
        </div>

        <CompactSystemBar system={systemMetrics} />
      </div>

      {/* LLM Metrics - if available */}
      <LLMMetricsPanel llmMetrics={llmMetrics} />

      {/* Provider sections - 3 column grid with enhanced visual separation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ProviderSection type="cli" services={cli} />
        <ProviderSection type="local" services={local} />
        <ProviderSection type="remote" services={remote} />
      </div>
    </div>
  );
};

/**
 * Provider Section Component
 * Enhanced visual separation with color-coded themes
 */
const ProviderSection = ({ type, services }) => {
  const theme = PROVIDER_THEMES[type];
  const allHealthy = services.length > 0 && services.every(s => s.healthy);

  return (
    <div className={cn(
      "relative rounded-xl border-2 overflow-hidden transition-all hover:scale-[1.02]",
      theme.border,
      theme.bg
    )}>
      {/* Gradient top accent */}
      <div className={cn(
        "absolute top-0 left-0 right-0 h-1 bg-gradient-to-r",
        theme.gradient
      )} />

      {/* Header - compact */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-xl">{theme.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-white">{theme.label}</h3>
            <p className="text-xs text-gh-fg-subtle">{theme.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={services.length > 0 ? 'success' : 'secondary'} size="sm">
            {services.length}
          </Badge>
          <StatusIndicator
            status={allHealthy ? 'online' : services.length > 0 ? 'degraded' : 'offline'}
            size="sm"
          />
        </div>
      </div>

      {/* Service list - compact */}
      <div className="p-3 space-y-2">
        {services.length > 0 ? (
          services.map(service => (
            <CompactServiceRow key={service.name} service={service} theme={theme} />
          ))
        ) : (
          <EmptyState icon={theme.icon} text={`No ${type} providers`} />
        )}
      </div>
    </div>
  );
};

/**
 * Compact service row component
 */
const CompactServiceRow = ({ service, theme }) => {
  const { name, healthy, info } = service;
  const [expanded, setExpanded] = React.useState(false);
  const model = info?.default_model || info?.model || 'auto-detect';

  return (
    <div className="glass rounded-lg p-2 hover:bg-white/5 transition-all">
      <div
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Status dot */}
        <div className={cn(
          'w-2 h-2 rounded-full flex-shrink-0',
          healthy ? 'bg-cyan-400 pulse-neon' : 'bg-red-400'
        )} />

        {/* Name + Model in one line */}
        <div className="flex-1 min-w-0 flex items-baseline gap-2">
          <span className="text-sm font-medium text-white truncate">
            {name}
          </span>
          <span className="text-xs text-gh-fg-subtle truncate">
            {model}
          </span>
        </div>

        {/* Inline metrics for HTTP services */}
        {info?.base_url && healthy && (
          <div className="hidden md:flex items-center gap-2 text-xs">
            <span className="text-cyan-400">⚡ ~0ms</span>
            <span className="text-purple-400">📊 Ready</span>
          </div>
        )}

        {/* Status badge */}
        <div className={cn(
          'w-10 h-5 rounded text-xs font-medium flex items-center justify-center flex-shrink-0',
          healthy
            ? 'bg-cyan-500/20 text-cyan-400'
            : 'bg-red-500/20 text-red-400'
        )}>
          {healthy ? 'UP' : 'DN'}
        </div>
      </div>

      {/* Expandable details */}
      {expanded && info?.base_url && (
        <div className="mt-2 pt-2 border-t border-white/5 text-xs">
          <span className="text-gh-fg-subtle font-mono break-all">{info.base_url}</span>
        </div>
      )}
    </div>
  );
};

/**
 * Legacy service row component (kept for backward compatibility)
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
