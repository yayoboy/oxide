/**
 * Tabs Component - shadcn/ui base template
 */
import React, { useState } from 'react';
import { cn } from '../../lib/utils';

export const Tabs = ({ defaultValue, children, className }) => {
  const [activeTab, setActiveTab] = useState(defaultValue);

  return (
    <div className={cn('w-full', className)}>
      {React.Children.map(children, child =>
        React.cloneElement(child, { activeTab, setActiveTab })
      )}
    </div>
  );
};

export const TabsList = ({ children, activeTab, setActiveTab, className }) => {
  return (
    <div className={cn(
      'inline-flex h-10 items-center justify-center rounded-md bg-gh-canvas-subtle p-1 border border-gh-border mb-6',
      className
    )}>
      {React.Children.map(children, child =>
        React.cloneElement(child, { activeTab, setActiveTab })
      )}
    </div>
  );
};

export const TabsTrigger = ({ value, children, activeTab, setActiveTab, icon }) => {
  const isActive = activeTab === value;

  return (
    <button
      onClick={() => setActiveTab(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gh-accent-primary',
        'disabled:pointer-events-none disabled:opacity-50',
        'gap-2',
        isActive
          ? 'bg-gh-canvas text-gh-fg shadow-sm'
          : 'text-gh-fg-muted hover:bg-gh-border-muted hover:text-gh-fg'
      )}
    >
      {icon && <span>{icon}</span>}
      {children}
    </button>
  );
};

export const TabsContent = ({ value, children, activeTab }) => {
  if (activeTab !== value) return null;

  return (
    <div className="mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gh-accent-primary">
      {children}
    </div>
  );
};
