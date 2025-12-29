/**
 * Oxide LLM Orchestrator - Minimal Web UI
 * Fast, clean, essential interface
 */
import React, { useState } from 'react';
import MinimalDashboard from './components/MinimalDashboard';
import TaskHistory from './components/TaskHistory';
import TaskExecutor from './components/TaskExecutor';
import { useServices } from './hooks/useServices';
import { useMetrics } from './hooks/useMetrics';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { services, loading: servicesLoading, error: servicesError } = useServices();
  const { metrics, loading: metricsLoading } = useMetrics();
  const { connected: wsConnected } = useWebSocket();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [taskHistoryKey, setTaskHistoryKey] = useState(0);

  // Theme toggle
  const [isDark, setIsDark] = useState(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );

  React.useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
      {/* Header - Minimal */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                Ox
              </div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Oxide Orchestrator
              </h1>
            </div>

            {/* Status + Theme */}
            <div className="flex items-center gap-3">
              {/* WebSocket Status */}
              {wsConnected && (
                <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="hidden sm:inline">Live</span>
                </div>
              )}

              {/* Services Count */}
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {services?.healthy || 0}/{services?.total || 0}
                </span>
                <span className="hidden sm:inline ml-1">services</span>
              </div>

              {/* Theme Toggle */}
              <button
                onClick={() => setIsDark(!isDark)}
                className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Toggle theme"
              >
                {isDark ? '☀️' : '🌙'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - Minimal */}
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-6">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: '📊' },
              { id: 'execute', label: 'Execute', icon: '⚡' },
              { id: 'history', label: 'History', icon: '📜' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-1 py-4 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
              >
                <span>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error State */}
        {servicesError && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">
              ⚠️ Error loading services: {servicesError}
            </p>
          </div>
        )}

        {/* Loading State */}
        {(servicesLoading || metricsLoading) && activeTab === 'dashboard' ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-600 dark:text-gray-400 animate-pulse">
              Loading dashboard...
            </div>
          </div>
        ) : null}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && !servicesLoading && !metricsLoading && (
          <MinimalDashboard services={services} metrics={metrics} />
        )}

        {/* Execute Tab */}
        {activeTab === 'execute' && (
          <TaskExecutor onTaskCompleted={() => setTaskHistoryKey((prev) => prev + 1)} />
        )}

        {/* History Tab */}
        {activeTab === 'history' && <TaskHistory key={taskHistoryKey} />}
      </main>

      {/* Footer - Minimal */}
      <footer className="border-t border-gray-200 dark:border-gray-800 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <div>Oxide v0.1.0</div>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              API Docs →
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
