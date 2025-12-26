/**
 * Card Component
 * Glassmorphism card with neon effects
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Card = React.forwardRef(({ className, children, variant = 'default', ...props }, ref) => {
  const variants = {
    default: 'glass',
    elevated: 'glass shadow-2xl',
    interactive: 'glass glass-hover',
    neon: 'gradient-border',
  };

  return (
    <div
      ref={ref}
      className={cn(
        'rounded-2xl p-6 animate-fade-in relative overflow-hidden',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
});
Card.displayName = 'Card';

export const CardHeader = React.forwardRef(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center justify-between mb-6 pb-4 border-b border-white/10', className)}
    {...props}
  >
    {children}
  </div>
));
CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef(({ className, children, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-xl font-bold text-white flex items-center gap-3', className)}
    {...props}
  >
    {children}
  </h3>
));
CardTitle.displayName = 'CardTitle';

export const CardDescription = React.forwardRef(({ className, children, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-gh-fg-muted mt-1', className)}
    {...props}
  >
    {children}
  </p>
));
CardDescription.displayName = 'CardDescription';

export const CardContent = React.forwardRef(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('space-y-4', className)}
    {...props}
  >
    {children}
  </div>
));
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center justify-between mt-6 pt-4 border-t border-white/10', className)}
    {...props}
  >
    {children}
  </div>
));
CardFooter.displayName = 'CardFooter';
