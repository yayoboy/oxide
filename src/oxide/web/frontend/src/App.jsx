/**
 * Main App Component
 * Oxide LLM Orchestrator Dashboard with Glassmorphism UI
 */
import React, { useState } from 'react';
import ThemeProvider from './components/ThemeProvider';
import ThemeToggle from './components/ThemeToggle';
import CompactDashboard from './components/CompactDashboard';
import TaskHistory from './components/TaskHistory';
import TaskExecutor from './components/TaskExecutor';
import TaskAssignmentManager from './components/TaskAssignmentManager';
import SystemMonitor from './components/SystemMonitor';
import ConfigurationPanel from './components/ConfigurationPanel';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/Tabs';
import { useServices } from './hooks/useServices';
import { useMetrics } from './hooks/useMetrics';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { services, loading: servicesLoading, error: servicesError } = useServices();
  const { metrics, loading: metricsLoading } = useMetrics();
  const { connected: wsConnected } = useWebSocket();
  const [taskHistoryKey, setTaskHistoryKey] = useState(0);

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gh-canvas">
      {/* Header - shadcn/ui style */}
      <header className="sticky top-0 z-50 border-b border-gh-border bg-gh-canvas">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Logo and Title */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-gh-accent-emphasis/10 border border-gh-accent-primary/20 flex items-center justify-center">
                <span className="text-lg">🔬</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gh-fg">
                  Oxide LLM Orchestrator
                </h1>
                <p className="text-xs text-gh-fg-muted">
                  AI Resource Management
                </p>
              </div>
            </div>

            {/* Compact Metrics + Theme Toggle */}
            <div className="flex items-center gap-2">
              {/* Theme Toggle */}
              <ThemeToggle />

              {/* WebSocket Status */}
              {wsConnected && (
                <div className="rounded-md border border-gh-border bg-gh-canvas-subtle px-3 py-1.5 flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-gh-success rounded-full pulse-dot" />
                  <span className="text-xs text-gh-fg-muted">Live</span>
                </div>
              )}

              {/* Services Status */}
              <div className="rounded-md border border-gh-border bg-gh-canvas-subtle px-3 py-1.5">
                <span className="text-xs text-gh-fg-muted mr-2">Services:</span>
                <span className="text-sm font-medium text-gh-fg">
                  {services?.healthy || 0}/{services?.total || 0}
                </span>
              </div>

              {/* Active Tasks */}
              {metrics?.active_tasks !== undefined && (
                <div className="rounded-md border border-gh-border bg-gh-canvas-subtle px-3 py-1.5">
                  <span className="text-xs text-gh-fg-muted mr-2">Active:</span>
                  <span className="text-sm font-medium text-gh-accent-primary">
                    {metrics.active_tasks}
                  </span>
                </div>
              )}

              {/* System Load */}
              {metrics?.system?.cpu_percent !== undefined && (
                <div className="rounded-md border border-gh-border bg-gh-canvas-subtle px-3 py-1.5">
                  <span className="text-xs text-gh-fg-muted mr-2">CPU:</span>
                  <span className={`text-sm font-medium ${
                    metrics.system.cpu_percent > 80 ? 'text-gh-danger' :
                    metrics.system.cpu_percent > 50 ? 'text-gh-attention' :
                    'text-gh-success'
                  }`}>
                    {metrics.system.cpu_percent}%
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        <Tabs defaultValue="dashboard">
          <TabsList>
            <TabsTrigger value="dashboard" icon="📊">
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="tasks" icon="⚡">
              Execute Tasks
            </TabsTrigger>
            <TabsTrigger value="history" icon="📜">
              Task History
            </TabsTrigger>
            <TabsTrigger value="routing" icon="🔀">
              Routing Rules
            </TabsTrigger>
            <TabsTrigger value="monitor" icon="💻">
              System Monitor
            </TabsTrigger>
            <TabsTrigger value="config" icon="⚙️">
              Configuration
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab - Compact unified view */}
          <TabsContent value="dashboard">
            {servicesLoading || metricsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="glass rounded-2xl px-8 py-4">
                  <div className="text-gh-fg-muted animate-pulse">Loading dashboard...</div>
                </div>
              </div>
            ) : servicesError ? (
              <div className="glass rounded-2xl p-6 border-2 border-red-500/30 bg-red-500/10">
                <p className="text-red-400">Error loading services: {servicesError}</p>
              </div>
            ) : (
              <CompactDashboard services={services} metrics={metrics} />
            )}
          </TabsContent>

          {/* Execute Tasks Tab */}
          <TabsContent value="tasks">
            <TaskExecutor onTaskCompleted={() => setTaskHistoryKey((prev) => prev + 1)} />
          </TabsContent>

          {/* Task History Tab */}
          <TabsContent value="history">
            <TaskHistory key={taskHistoryKey} />
          </TabsContent>

          {/* Routing Tab */}
          <TabsContent value="routing">
            <TaskAssignmentManager />
          </TabsContent>

          {/* System Monitor Tab */}
          <TabsContent value="monitor">
            <SystemMonitor />
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent value="config">
            <ConfigurationPanel />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <footer className="mt-16 py-6 border-t border-gh-border">
          <div className="text-center">
            <p className="text-sm text-gh-fg-muted">
              Oxide v0.1.0 · LLM Orchestration
            </p>
            <p className="text-sm mt-2">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gh-accent-primary hover:underline"
              >
                API Documentation
              </a>
            </p>
          </div>
        </footer>
      </main>
    </div>
    </ThemeProvider>
  );
}

export default App;
