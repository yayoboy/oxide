/**
 * Badge Component - shadcn/ui base template
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Badge = React.forwardRef(({ className, children, variant = 'default', size = 'default', ...props }, ref) => {
  const variants = {
    default: 'border-transparent bg-gh-border text-gh-fg',
    secondary: 'border-transparent bg-gh-canvas-subtle text-gh-fg-muted',
    success: 'border-transparent bg-gh-success/10 text-gh-success',
    error: 'border-transparent bg-gh-danger/10 text-gh-danger',
    warning: 'border-transparent bg-gh-attention/10 text-gh-attention',
    outline: 'text-gh-fg border-gh-border',
  };

  const sizes = {
    default: 'px-2.5 py-0.5 text-xs',
    sm: 'px-2 py-0.5 text-[10px]',
    lg: 'px-3 py-1 text-sm',
  };

  return (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-full border font-semibold transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-gh-accent-primary focus:ring-offset-2',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
});
Badge.displayName = 'Badge';
