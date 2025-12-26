/**
 * Badge Component
 * Glassmorphism badges with neon effects
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Badge = React.forwardRef(({ className, children, variant = 'default', ...props }, ref) => {
  const variants = {
    default: 'bg-white/10 text-gh-fg-DEFAULT border-white/20',
    success: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    info: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  return (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wide',
        'backdrop-blur-sm border',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
});
Badge.displayName = 'Badge';
