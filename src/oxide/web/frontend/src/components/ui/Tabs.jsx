/**
 * Tabs Component
 * Modern tab navigation with glassmorphism and neon effects
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
      'glass rounded-2xl p-2 mb-8 inline-flex gap-2',
      'border border-white/10',
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
        'relative px-6 py-3 rounded-xl font-medium transition-all duration-300',
        'flex items-center gap-3',
        isActive
          ? 'text-white'
          : 'text-gh-fg-muted hover:text-gh-fg-DEFAULT'
      )}
    >
      {/* Active indicator with gradient */}
      {isActive && (
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-sm">
          <div className="absolute inset-0 rounded-xl border-2 border-transparent bg-gradient-to-r from-cyan-500 to-purple-500 bg-clip-border opacity-50" />
        </div>
      )}

      {/* Content */}
      <span className="relative z-10 flex items-center gap-2">
        {icon && <span className="text-xl">{icon}</span>}
        {children}
      </span>

      {/* Glow effect on active */}
      {isActive && (
        <div className="absolute inset-0 rounded-xl opacity-30 blur-xl bg-gradient-to-r from-cyan-500 to-purple-500" />
      )}
    </button>
  );
};

export const TabsContent = ({ value, children, activeTab }) => {
  if (activeTab !== value) return null;

  return (
    <div className="animate-fade-in">
      {children}
    </div>
  );
};
