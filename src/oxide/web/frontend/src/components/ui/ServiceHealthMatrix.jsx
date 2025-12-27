/**
 * Service Health Matrix Component
 * Ultra-compact grid visualization of all services with visual health indicators
 */
import React, { useState } from 'react';
import { cn } from '../../lib/utils';

/**
 * Service Health Cell - Single service indicator
 */
const ServiceCell = ({ service, theme, onClick }) => {
  const { name, healthy, info } = service;
  const model = info?.default_model || info?.model || 'auto';

  const statusColors = {
    healthy: `bg-gradient-to-br ${theme.gradient} shadow-lg ${theme.glow}`,
    unhealthy: 'bg-gradient-to-br from-red-500/30 to-red-700/30 shadow-red-500/20',
    unknown: 'bg-gradient-to-br from-gray-500/20 to-gray-700/20'
  };

  const status = healthy ? 'healthy' : 'unhealthy';

  return (
    <div
      onClick={onClick}
      className={cn(
        "relative group cursor-pointer rounded-lg p-3 transition-all duration-300",
        "hover:scale-105 hover:z-10",
        "border border-white/10",
        statusColors[status]
      )}
      data-testid="service-cell"
    >
      {/* Pulse effect for healthy services */}
      {healthy && (
        <div className="absolute inset-0 rounded-lg bg-white/10 animate-pulse" />
      )}

      {/* Status dot */}
      <div className={cn(
        "absolute top-1 right-1 w-2 h-2 rounded-full",
        healthy ? 'bg-cyan-400 animate-pulse' : 'bg-red-400'
      )} />

      {/* Service icon/initial */}
      <div className="text-center mb-1">
        <div className={cn(
          "text-lg font-bold",
          healthy ? 'text-white' : 'text-red-300'
        )}>
          {name.substring(0, 2).toUpperCase()}
        </div>
      </div>

      {/* Service name */}
      <div className="text-xs text-center text-white/90 font-medium truncate">
        {name}
      </div>

      {/* Hover tooltip */}
      <div className={cn(
        "absolute left-1/2 -translate-x-1/2 bottom-full mb-2 px-3 py-2",
        "bg-gh-canvas-subtle border border-white/20 rounded-lg shadow-xl",
        "opacity-0 group-hover:opacity-100 pointer-events-none",
        "transition-all duration-200 z-50 min-w-[200px]"
      )}>
        <div className="text-sm font-semibold text-white mb-1">{name}</div>
        <div className="text-xs text-gh-fg-muted space-y-1">
          <div>Model: {model}</div>
          <div>Status: {healthy ? 'Online' : 'Offline'}</div>
          {info?.base_url && (
            <div className="truncate">URL: {info.base_url}</div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Provider Section Header
 */
const SectionHeader = ({ theme, count, healthyCount }) => {
  return (
    <div className={cn(
      "flex items-center justify-between p-2 rounded-lg mb-2",
      theme.bg,
      "border",
      theme.border
    )}>
      <div className="flex items-center gap-2">
        <span className="text-lg">{theme.icon}</span>
        <span className="text-sm font-semibold text-white">{theme.label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gh-fg-muted">
          {healthyCount}/{count}
        </span>
        <div className={cn(
          "w-2 h-2 rounded-full",
          healthyCount === count ? 'bg-green-400 animate-pulse' :
          healthyCount > 0 ? 'bg-yellow-400' : 'bg-red-400'
        )} />
      </div>
    </div>
  );
};

/**
 * Provider Themes
 */
const PROVIDER_THEMES = {
  cli: {
    gradient: 'from-blue-500 to-cyan-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    glow: 'shadow-blue-500/20',
    icon: '⚡',
    label: 'CLI'
  },
  local: {
    gradient: 'from-green-500 to-emerald-500',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    glow: 'shadow-green-500/20',
    icon: '🏠',
    label: 'Local'
  },
  remote: {
    gradient: 'from-purple-500 to-magenta-500',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    glow: 'shadow-purple-500/20',
    icon: '🌐',
    label: 'Remote'
  }
};

/**
 * Main Service Health Matrix Component
 */
export const ServiceHealthMatrix = ({ services }) => {
  const [selectedService, setSelectedService] = useState(null);

  // Categorize services by type
  const categorizeServices = () => {
    if (!services?.services) return { cli: [], local: [], remote: [] };

    const categories = { cli: [], local: [], remote: [] };

    Object.entries(services.services).forEach(([name, status]) => {
      const info = status.info || {};

      if (info.type === 'cli') {
        categories.cli.push({ name, ...status });
      } else if (info.type === 'http') {
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

  const renderSection = (type, serviceList) => {
    if (serviceList.length === 0) return null;

    const theme = PROVIDER_THEMES[type];
    const healthyCount = serviceList.filter(s => s.healthy).length;

    return (
      <div key={type} className="space-y-2">
        <SectionHeader
          theme={theme}
          count={serviceList.length}
          healthyCount={healthyCount}
        />

        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
          {serviceList.map(service => (
            <ServiceCell
              key={service.name}
              service={service}
              theme={theme}
              onClick={() => setSelectedService(service)}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="glass rounded-xl p-4 space-y-4" data-testid="service-health-matrix">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔧</span>
          <div>
            <h3 className="text-sm font-semibold text-white">Service Health Matrix</h3>
            <p className="text-xs text-gh-fg-subtle">Visual status overview</p>
          </div>
        </div>

        {/* Overall health indicator */}
        <div className="flex items-center gap-2 glass rounded-lg px-3 py-1.5">
          <span className="text-xs text-gh-fg-muted">Overall:</span>
          <span className={cn(
            "text-sm font-bold",
            services?.healthy === services?.total ? 'text-green-400' :
            services?.healthy > 0 ? 'text-yellow-400' : 'text-red-400'
          )}>
            {((services?.healthy / services?.total) * 100 || 0).toFixed(0)}%
          </span>
        </div>
      </div>

      {renderSection('cli', cli)}
      {renderSection('local', local)}
      {renderSection('remote', remote)}

      {/* Empty state */}
      {cli.length === 0 && local.length === 0 && remote.length === 0 && (
        <div className="text-center py-8 text-gh-fg-muted">
          <div className="text-4xl mb-2">🔧</div>
          <div className="text-sm">No services configured</div>
        </div>
      )}
    </div>
  );
};

export default ServiceHealthMatrix;
