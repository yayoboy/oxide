/**
 * Input Components
 * Glassmorphism form inputs
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Input = React.forwardRef(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'w-full px-4 py-3 glass rounded-xl border border-white/10',
          'text-white text-sm placeholder:text-gh-fg-subtle',
          'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'transition-all duration-200',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export const Textarea = React.forwardRef(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'w-full px-4 py-3 glass rounded-xl border border-white/10',
          'text-white text-sm placeholder:text-gh-fg-subtle',
          'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'transition-all duration-200 resize-vertical',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';

export const Select = React.forwardRef(
  ({ className, children, ...props }, ref) => {
    return (
      <select
        className={cn(
          'w-full px-4 py-3 glass rounded-xl border border-white/10',
          'text-white text-sm',
          'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'transition-all duration-200 cursor-pointer',
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    );
  }
);
Select.displayName = 'Select';

export const Label = React.forwardRef(
  ({ className, ...props }, ref) => {
    return (
      <label
        className={cn(
          'block text-sm font-medium text-white mb-2',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Label.displayName = 'Label';

export const FormField = ({ label, description, error, children, required }) => {
  return (
    <div className="space-y-2">
      {label && (
        <Label>
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </Label>
      )}
      {children}
      {description && (
        <p className="text-xs text-gh-fg-subtle">{description}</p>
      )}
      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
};
