/**
 * Dialog Component
 * Modal dialog for user interactions
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Dialog = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog content */}
      <div className="relative z-50 w-full max-w-lg">
        {children}
      </div>
    </div>
  );
};

export const DialogContent = ({ children, className }) => (
  <div className={cn(
    "glass rounded-2xl p-6 border-2 border-white/20 shadow-2xl",
    "animate-fade-in",
    className
  )}>
    {children}
  </div>
);

export const DialogHeader = ({ children, className }) => (
  <div className={cn("space-y-2 mb-4", className)}>
    {children}
  </div>
);

export const DialogTitle = ({ children, className }) => (
  <h2 className={cn("text-xl font-bold text-white", className)}>
    {children}
  </h2>
);

export const DialogDescription = ({ children, className }) => (
  <p className={cn("text-sm text-gh-fg-muted", className)}>
    {children}
  </p>
);

export const DialogFooter = ({ children, className }) => (
  <div className={cn("flex justify-end gap-3 mt-6", className)}>
    {children}
  </div>
);

export default Dialog;
