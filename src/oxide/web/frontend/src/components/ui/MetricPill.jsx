/**
 * Metric Pill Component - shadcn/ui base template
 * Compact inline metric display for dashboard header
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const MetricPill = ({ icon, label, value, status = 'neutral', className }) => {
  const statusColors = {
    success: 'bg-gh-success/10 border-gh-success/20 text-gh-success',
    warning: 'bg-gh-attention/10 border-gh-attention/20 text-gh-attention',
    error: 'bg-gh-danger/10 border-gh-danger/20 text-gh-danger',
    info: 'bg-gh-accent-primary/10 border-gh-accent-primary/20 text-gh-accent-primary',
    neutral: 'bg-gh-canvas-subtle border-gh-border text-gh-fg'
  };

  // Generate test ID from label
  const testId = `metric-pill-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div
      className={cn(
        "rounded-md px-3 py-1.5 border flex items-center gap-2 transition-colors",
        statusColors[status],
        className
      )}
      data-testid={testId}
    >
      {icon && <span className="text-sm">{icon}</span>}
      <span className="text-xs text-gh-fg-muted whitespace-nowrap">{label}:</span>
      <span className="text-sm font-semibold whitespace-nowrap">{value}</span>
    </div>
  );
};

export default MetricPill;
