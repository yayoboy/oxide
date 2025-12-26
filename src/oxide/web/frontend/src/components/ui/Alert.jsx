/**
 * Alert Component
 * Inline alert messages
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Alert = ({ children, variant = 'default', className }) => {
  const variantStyles = {
    default: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400',
    success: 'border-green-500/30 bg-green-500/10 text-green-400',
    warning: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
    error: 'border-red-500/30 bg-red-500/10 text-red-400',
    info: 'border-purple-500/30 bg-purple-500/10 text-purple-400',
  };

  return (
    <div className={cn(
      "glass rounded-xl p-4 border-2",
      variantStyles[variant],
      className
    )}>
      {children}
    </div>
  );
};

export const AlertTitle = ({ children, className }) => (
  <div className={cn("font-semibold mb-1", className)}>
    {children}
  </div>
);

export const AlertDescription = ({ children, className }) => (
  <div className={cn("text-sm opacity-90", className)}>
    {children}
  </div>
);

export default Alert;
