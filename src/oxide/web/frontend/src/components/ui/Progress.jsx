/**
 * Progress Component
 * Progress bar with optional label
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Progress = ({ value = 0, max = 100, className, showLabel = false }) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const getColor = () => {
    if (percentage < 33) return 'from-red-500 to-orange-500';
    if (percentage < 66) return 'from-yellow-500 to-cyan-500';
    return 'from-cyan-500 to-green-500';
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full bg-gradient-to-r transition-all duration-500 relative",
            getColor()
          )}
          style={{ width: `${percentage}%` }}
        >
          <div className="absolute inset-0 shimmer" />
        </div>
      </div>
      {showLabel && (
        <div className="text-xs text-gh-fg-muted mt-1 text-right">
          {percentage.toFixed(0)}%
        </div>
      )}
    </div>
  );
};

export default Progress;
