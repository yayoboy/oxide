/**
 * Button Component - shadcn/ui base template
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Button = React.forwardRef(
  ({ className, children, variant = 'default', size = 'default', disabled, ...props }, ref) => {
    const variants = {
      default: 'bg-gh-accent-primary text-white hover:bg-gh-accent-emphasis',
      destructive: 'bg-gh-danger text-white hover:bg-gh-danger-emphasis',
      outline: 'border border-gh-border bg-gh-canvas hover:bg-gh-canvas-subtle hover:text-gh-fg',
      secondary: 'bg-gh-canvas-subtle text-gh-fg hover:bg-gh-border-muted',
      ghost: 'hover:bg-gh-canvas-subtle hover:text-gh-fg',
      link: 'text-gh-accent-primary underline-offset-4 hover:underline',
    };

    const sizes = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 rounded-md px-3',
      lg: 'h-11 rounded-md px-8',
      icon: 'h-10 w-10',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gh-accent-primary focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          variants[variant],
          sizes[size],
          className
        )}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
