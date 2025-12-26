/**
 * Switch Component
 * Toggle switch for boolean settings
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Switch = ({ checked, onCheckedChange, disabled = false, className }) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onCheckedChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full",
        "transition-colors duration-200",
        "focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2",
        checked ? 'bg-cyan-500' : 'bg-white/20',
        disabled && 'opacity-50 cursor-not-allowed',
        !disabled && 'cursor-pointer',
        className
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white shadow-lg",
          "transition-transform duration-200",
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  );
};

export default Switch;
