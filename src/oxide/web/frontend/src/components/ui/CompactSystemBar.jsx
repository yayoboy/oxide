/**
 * Compact System Bar Component - shadcn/ui base template
 * Horizontal system metrics bar for dashboard header
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const CompactSystemBar = ({ system }) => {
  if (!system) return null;

  const getColor = (percent, thresholds = { low: 50, medium: 75 }) => {
    if (percent < thresholds.low) return 'bg-gh-success';
    if (percent < thresholds.medium) return 'bg-gh-attention';
    return 'bg-gh-danger';
  };

  const getTextColor = (percent, thresholds = { low: 50, medium: 75 }) => {
    if (percent < thresholds.low) return 'text-gh-success';
    if (percent < thresholds.medium) return 'text-gh-attention';
    return 'text-gh-danger';
  };

  return (
    <div className="rounded-md border border-gh-border bg-gh-canvas-subtle px-4 py-2 flex items-center gap-6" data-testid="system-bar">
      {/* CPU */}
      <div className="flex items-center gap-2 min-w-[100px]" data-testid="cpu-bar">
        <span className="text-xs text-gh-fg-muted">CPU</span>
        <div className="flex-1 h-1.5 bg-gh-border rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-300",
              getColor(system?.cpu_percent || 0)
            )}
            style={{ width: `${Math.min(system?.cpu_percent || 0, 100)}%` }}
          />
        </div>
        <span className={cn(
          "text-xs font-medium w-8 text-right",
          getTextColor(system?.cpu_percent || 0)
        )}>
          {system?.cpu_percent?.toFixed(0) || 0}%
        </span>
      </div>

      {/* Memory */}
      <div className="flex items-center gap-2 min-w-[100px]" data-testid="memory-bar">
        <span className="text-xs text-gh-fg-muted">RAM</span>
        <div className="flex-1 h-1.5 bg-gh-border rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-300",
              getColor(system?.memory_percent || 0, { low: 60, medium: 80 })
            )}
            style={{ width: `${Math.min(system?.memory_percent || 0, 100)}%` }}
          />
        </div>
        <span className={cn(
          "text-xs font-medium w-8 text-right",
          getTextColor(system?.memory_percent || 0, { low: 60, medium: 80 })
        )}>
          {system?.memory_percent?.toFixed(0) || 0}%
        </span>
      </div>

      {/* Disk (if available) */}
      {system?.disk_percent != null && (
        <div className="flex items-center gap-2 min-w-[100px]">
          <span className="text-xs text-gh-fg-muted">Disk</span>
          <div className="flex-1 h-1.5 bg-gh-border rounded-full overflow-hidden">
            <div
              className="h-full bg-gh-accent-primary transition-all duration-300"
              style={{ width: `${Math.min(system?.disk_percent || 0, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gh-accent-primary w-8 text-right">
            {system?.disk_percent?.toFixed(0) || 0}%
          </span>
        </div>
      )}
    </div>
  );
};

export default CompactSystemBar;
