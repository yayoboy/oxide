/**
 * Compact System Bar Component
 * Horizontal system metrics bar for dashboard header
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const CompactSystemBar = ({ system }) => {
  if (!system) return null;

  const getColor = (percent, thresholds = { low: 50, medium: 75 }) => {
    if (percent < thresholds.low) return 'from-cyan-500 to-blue-500';
    if (percent < thresholds.medium) return 'from-yellow-500 to-orange-500';
    return 'from-orange-500 to-red-500';
  };

  return (
    <div className="glass rounded-lg px-4 py-2 flex items-center gap-6">
      {/* CPU */}
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="text-sm text-gh-fg-muted">CPU</span>
        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full bg-gradient-to-r transition-all duration-500",
              getColor(system?.cpu_percent || 0)
            )}
            style={{ width: `${Math.min(system?.cpu_percent || 0, 100)}%` }}
          >
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>
        <span className="text-sm font-bold text-white w-10 text-right">
          {system?.cpu_percent?.toFixed(0) || 0}%
        </span>
      </div>

      {/* Memory */}
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="text-sm text-gh-fg-muted">RAM</span>
        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full bg-gradient-to-r transition-all duration-500",
              getColor(system?.memory_percent || 0, { low: 60, medium: 80 })
            )}
            style={{ width: `${Math.min(system?.memory_percent || 0, 100)}%` }}
          >
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>
        <span className="text-sm font-bold text-white w-10 text-right">
          {system?.memory_percent?.toFixed(0) || 0}%
        </span>
      </div>

      {/* Disk (if available) */}
      {system?.disk_percent != null && (
        <div className="flex items-center gap-2 min-w-[120px]">
          <span className="text-sm text-gh-fg-muted">Disk</span>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
              style={{ width: `${Math.min(system?.disk_percent || 0, 100)}%` }}
            >
              <div className="absolute inset-0 shimmer" />
            </div>
          </div>
          <span className="text-sm font-bold text-white w-10 text-right">
            {system?.disk_percent?.toFixed(0) || 0}%
          </span>
        </div>
      )}
    </div>
  );
};

export default CompactSystemBar;
