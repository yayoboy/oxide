/**
 * System Monitor Component
 * Multi-machine system metrics with glassmorphism design
 */
import React from 'react';
import { cn } from '../lib/utils';
import { useMachines } from '../hooks/useMachines';

export const SystemMonitor = () => {
  const { machines: machinesData, loading, error } = useMachines(3000);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="glass rounded-2xl px-8 py-4">
          <div className="text-gh-fg-muted animate-pulse">Loading machine metrics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-2xl p-6 border-2 border-red-500/30 bg-red-500/10">
        <p className="text-red-400">Error loading machine metrics: {error}</p>
      </div>
    );
  }

  const machines = machinesData?.machines || [];
  const onlineCount = machinesData?.online || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold neon-text">System Metrics</h2>
        <div className="flex items-center gap-3">
          <div className="glass rounded-full px-4 py-2 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400 pulse-neon" />
            <span className="text-sm text-gh-fg-muted">{machines.length} Machine(s)</span>
          </div>
          {onlineCount > 0 && (
            <div className="glass rounded-full px-4 py-2 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-cyan-400 pulse-neon" />
              <span className="text-sm font-medium text-cyan-400">{onlineCount} Online</span>
            </div>
          )}
        </div>
      </div>

      {machines.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="glass rounded-3xl p-12 text-center">
            <div className="text-7xl mb-4 opacity-20">💻</div>
            <div className="text-gh-fg-muted text-lg">No machines detected</div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {machines.map((machine) => (
            <MachineCard key={machine.id} machine={machine} />
          ))}
        </div>
      )}
    </div>
  );
};

const MachineCard = ({ machine }) => {
  const { name, status, metrics, location, services } = machine;
  const isOnline = status === 'online';

  const getCpuColor = (percent) => {
    if (percent < 50) return 'from-cyan-500 to-blue-500';
    if (percent < 75) return 'from-yellow-500 to-orange-500';
    return 'from-orange-500 to-red-500';
  };

  const getMemoryColor = (percent) => {
    if (percent < 60) return 'from-cyan-500 to-blue-500';
    if (percent < 80) return 'from-yellow-500 to-orange-500';
    return 'from-orange-500 to-red-500';
  };

  const hasMetrics = metrics && (metrics.cpu_percent != null || metrics.memory_percent != null);

  return (
    <div className="glass glass-hover rounded-2xl p-6 relative overflow-hidden group">
      {/* Background gradient animation */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
        <div className="absolute inset-0 animated-gradient" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-1">{name}</h3>
            <p className="text-sm text-gh-fg-muted font-mono">{location}</p>
          </div>
          <div className={cn(
            'flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium',
            isOnline
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          )}>
            <div className={cn('w-2 h-2 rounded-full', isOnline ? 'bg-cyan-400 pulse-neon' : 'bg-red-400')} />
            {isOnline ? 'Online' : 'Offline'}
          </div>
        </div>

        {/* Metrics */}
        {hasMetrics ? (
          <div className="space-y-4 mb-4">
            {/* CPU */}
            {metrics.cpu_percent != null && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gh-fg-muted">CPU Usage</span>
                  <span className="text-lg font-bold text-white">
                    {metrics.cpu_percent?.toFixed(1)}%
                  </span>
                </div>
                <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'absolute h-full rounded-full transition-all duration-500',
                      'bg-gradient-to-r',
                      getCpuColor(metrics.cpu_percent)
                    )}
                    style={{ width: `${Math.min(metrics.cpu_percent, 100)}%` }}
                  >
                    <div className="absolute inset-0 shimmer" />
                  </div>
                </div>
              </div>
            )}

            {/* Memory */}
            {metrics.memory_percent != null && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gh-fg-muted">Memory Usage</span>
                  <span className="text-lg font-bold text-white">
                    {metrics.memory_percent?.toFixed(1)}%
                  </span>
                </div>
                <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'absolute h-full rounded-full transition-all duration-500',
                      'bg-gradient-to-r',
                      getMemoryColor(metrics.memory_percent)
                    )}
                    style={{ width: `${Math.min(metrics.memory_percent, 100)}%` }}
                  >
                    <div className="absolute inset-0 shimmer" />
                  </div>
                </div>
                {metrics.memory_used_mb && metrics.memory_total_mb && (
                  <div className="mt-1 text-xs text-gh-fg-subtle text-right">
                    {metrics.memory_used_mb?.toFixed(0)} MB / {metrics.memory_total_mb?.toFixed(0)} MB
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="mb-4 p-3 bg-white/5 border border-white/10 rounded-lg">
            <p className="text-xs text-gh-fg-muted text-center">
              Remote metrics unavailable
            </p>
          </div>
        )}

        {/* Services */}
        {services && services.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gh-fg-muted uppercase tracking-wide">
              Services ({services.length})
            </div>
            <div className="space-y-1.5">
              {services.map((service, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-white/5 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'w-1.5 h-1.5 rounded-full',
                      service.healthy ? 'bg-cyan-400' : 'bg-red-400'
                    )} />
                    <span className="text-xs text-white font-medium">{service.name}</span>
                  </div>
                  {service.endpoint && (
                    <span className="text-xs text-gh-fg-subtle font-mono truncate max-w-[150px]">
                      {service.endpoint.replace(/^https?:\/\//, '')}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Neon accent line at bottom */}
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-purple-500 to-magenta-500 opacity-50" />
      </div>
    </div>
  );
};

export default SystemMonitor;
