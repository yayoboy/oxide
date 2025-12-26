/**
 * MetricCard Component
 * Displays individual metrics with labels and values
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const MetricCard = ({ label, value, icon, trend, className, valueColor }) => {
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gh-fg-muted">{label}</span>
        {icon && <span className="text-gh-fg-subtle">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={cn('text-3xl font-bold', valueColor || 'text-gh-fg-DEFAULT')}>
          {value}
        </span>
        {trend && (
          <span className={cn(
            'text-xs font-medium',
            trend.direction === 'up' ? 'text-gh-success' : 'text-gh-danger'
          )}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.value}
          </span>
        )}
      </div>
    </div>
  );
};

export const ProgressBar = ({ value, max = 100, variant = 'default', showLabel = false }) => {
  const percentage = (value / max) * 100;

  const getColor = () => {
    if (variant === 'success' || percentage < 50) return 'bg-gh-success';
    if (variant === 'warning' || percentage < 75) return 'bg-gh-attention';
    if (variant === 'danger' || percentage >= 75) return 'bg-gh-danger';
    return 'bg-gh-accent-primary';
  };

  return (
    <div className="space-y-2">
      {showLabel && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gh-fg-muted">Progress</span>
          <span className={cn('font-semibold', getColor().replace('bg-', 'text-'))}>
            {percentage.toFixed(1)}%
          </span>
        </div>
      )}
      <div className="h-2 bg-gh-canvas rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-500 ease-out', getColor())}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
};
