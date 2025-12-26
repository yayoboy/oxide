/**
 * Metric Pill Component
 * Compact inline metric display for dashboard header
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const MetricPill = ({ icon, label, value, status = 'neutral', className }) => {
  const statusColors = {
    success: 'bg-cyan-500/20 border-cyan-500/30 text-cyan-400',
    warning: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400',
    error: 'bg-red-500/20 border-red-500/30 text-red-400',
    info: 'bg-purple-500/20 border-purple-500/30 text-purple-400',
    neutral: 'bg-white/10 border-white/20 text-white'
  };

  return (
    <div className={cn(
      "rounded-full px-3 py-1.5 border flex items-center gap-2 transition-all hover:scale-105",
      statusColors[status],
      className
    )}>
      {icon && <span className="text-sm">{icon}</span>}
      <span className="text-xs text-gh-fg-muted whitespace-nowrap">{label}:</span>
      <span className="text-sm font-bold whitespace-nowrap">{value}</span>
    </div>
  );
};

export default MetricPill;
