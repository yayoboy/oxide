/**
 * Toast Component
 * Notification toasts with auto-dismiss
 */
import React, { useState, useEffect, createContext, useContext } from 'react';
import { cn } from '../../lib/utils';

const ToastContext = createContext();

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = (toast) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { ...toast, id }]);

    // Auto dismiss after duration
    setTimeout(() => {
      removeToast(id);
    }, toast.duration || 3000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

const ToastContainer = ({ toasts, onRemove }) => {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onClose={() => onRemove(toast.id)} />
      ))}
    </div>
  );
};

const Toast = ({ title, description, variant = 'default', onClose }) => {
  const variantStyles = {
    default: 'border-cyan-500/30 bg-cyan-500/10',
    success: 'border-green-500/30 bg-green-500/10',
    error: 'border-red-500/30 bg-red-500/10',
    warning: 'border-yellow-500/30 bg-yellow-500/10',
  };

  return (
    <div className={cn(
      "glass rounded-xl p-4 border-2 shadow-xl pointer-events-auto",
      "min-w-[300px] max-w-md",
      "animate-slide-up",
      variantStyles[variant]
    )}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          {title && (
            <div className="font-semibold text-white mb-1">{title}</div>
          )}
          {description && (
            <div className="text-sm text-gh-fg-muted">{description}</div>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gh-fg-subtle hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default Toast;
