/**
 * Button Component
 * Glassmorphism button with neon effects
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Button = React.forwardRef(
  ({ className, children, variant = 'default', size = 'default', disabled, ...props }, ref) => {
    const variants = {
      default: 'glass glass-hover text-white',
      primary: 'bg-gradient-to-r from-cyan-500 to-purple-500 text-white hover:from-cyan-400 hover:to-purple-400 shadow-lg neon-glow',
      secondary: 'glass border-white/20 text-gh-fg-DEFAULT hover:border-white/40',
      ghost: 'text-gh-fg-DEFAULT hover:bg-white/10',
      danger: 'bg-gradient-to-r from-red-500 to-pink-500 text-white hover:from-red-400 hover:to-pink-400 shadow-lg',
    };

    const sizes = {
      default: 'px-6 py-3 text-sm',
      sm: 'px-4 py-2 text-xs',
      lg: 'px-8 py-4 text-base',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-300',
          'focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-transparent',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:translate-y-0',
          'hover:-translate-y-0.5 active:translate-y-0',
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
