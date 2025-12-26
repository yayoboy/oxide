/**
 * StatusIndicator Component
 * Visual indicator for service/system health status
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const StatusIndicator = ({ status = 'unknown', label, showLabel = true, size = 'default' }) => {
  const statusConfig = {
    healthy: {
      color: 'bg-gh-success',
      label: 'Healthy',
      pulse: true,
    },
    unhealthy: {
      color: 'bg-gh-danger',
      label: 'Unhealthy',
      pulse: true,
    },
    warning: {
      color: 'bg-gh-attention',
      label: 'Warning',
      pulse: false,
    },
    unknown: {
      color: 'bg-gh-fg-subtle',
      label: 'Unknown',
      pulse: false,
    },
  };

  const sizes = {
    sm: 'w-2 h-2',
    default: 'w-2.5 h-2.5',
    lg: 'w-3 h-3',
  };

  const config = statusConfig[status] || statusConfig.unknown;

  return (
    <div className="inline-flex items-center gap-2">
      <span className="relative inline-flex">
        <span
          className={cn(
            'rounded-full',
            sizes[size],
            config.color
          )}
        />
        {config.pulse && (
          <span
            className={cn(
              'absolute inline-flex rounded-full opacity-75 animate-ping',
              sizes[size],
              config.color
            )}
          />
        )}
      </span>
      {showLabel && (
        <span className="text-sm text-gh-fg-DEFAULT font-medium">
          {label || config.label}
        </span>
      )}
    </div>
  );
};
