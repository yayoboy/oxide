/**
 * Theme Toggle Component
 * Allows users to switch between light, dark, and system theme
 */
import React from 'react';
import { useTheme } from 'next-themes';
import { cn } from '../lib/utils';

export function ThemeToggle({ className }) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  // Avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <button className={cn(
        "rounded-lg p-2 glass border border-white/10",
        className
      )}>
        <span className="text-xl">🌗</span>
      </button>
    );
  }

  const currentTheme = theme === 'system' ? resolvedTheme : theme;

  const cycleTheme = () => {
    if (currentTheme === 'dark') {
      setTheme('light');
    } else if (currentTheme === 'light') {
      setTheme('system');
    } else {
      setTheme('dark');
    }
  };

  const getIcon = () => {
    if (theme === 'system') return '🖥️';
    if (currentTheme === 'dark') return '🌙';
    return '☀️';
  };

  const getLabel = () => {
    if (theme === 'system') return 'System';
    if (currentTheme === 'dark') return 'Dark';
    return 'Light';
  };

  return (
    <button
      onClick={cycleTheme}
      className={cn(
        "rounded-lg px-3 py-2 glass border border-white/10",
        "hover:bg-white/10 transition-all duration-200",
        "flex items-center gap-2 group",
        className
      )}
      title={`Current theme: ${getLabel()}. Click to cycle.`}
    >
      <span className="text-xl transition-transform group-hover:scale-110">
        {getIcon()}
      </span>
      <span className="text-sm font-medium text-gh-fg-DEFAULT hidden sm:inline">
        {getLabel()}
      </span>
    </button>
  );
}

export default ThemeToggle;
