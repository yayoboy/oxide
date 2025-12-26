/**
 * Main App Component
 * Oxide LLM Orchestrator Dashboard with Glassmorphism UI
 */
import React, { useState } from 'react';
import CompactDashboard from './components/CompactDashboard';
import TaskHistory from './components/TaskHistory';
import TaskExecutor from './components/TaskExecutor';
import TaskAssignmentManager from './components/TaskAssignmentManager';
import SystemMonitor from './components/SystemMonitor';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/Tabs';
import { useServices } from './hooks/useServices';
import { useMetrics } from './hooks/useMetrics';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { services, loading: servicesLoading, error: servicesError } = useServices(5000);
  const { metrics, loading: metricsLoading } = useMetrics(2000);
  const { connected: wsConnected } = useWebSocket();
  const [taskHistoryKey, setTaskHistoryKey] = useState(0);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background particles */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 w-80 h-80 bg-magenta-500/10 rounded-full blur-3xl animate-pulse delay-2000" />
      </div>

      {/* Header - Compact with inline metrics */}
      <header className="sticky top-0 z-50 backdrop-blur-xl border-b border-white/10">
        <div className="glass">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Logo and Title */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center text-xl neon-glow">
                  🔬
                </div>
                <div>
                  <h1 className="text-xl font-bold neon-text">
                    Oxide LLM Orchestrator
                  </h1>
                  <p className="text-xs text-gh-fg-muted">
                    Intelligent AI Resource Management
                  </p>
                </div>
              </div>

              {/* Compact Metrics */}
              <div className="flex items-center gap-3">
                {/* WebSocket Status */}
                {wsConnected && (
                  <div className="glass rounded-full px-3 py-1.5 flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full pulse-neon" />
                    <span className="text-xs font-medium text-cyan-400">Live</span>
                  </div>
                )}

                {/* Services Status */}
                <div className="glass rounded-lg px-3 py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gh-fg-muted">Services:</span>
                    <span className="text-sm font-bold text-white">
                      {services?.healthy || 0}/{services?.total || 0}
                    </span>
                  </div>
                </div>

                {/* Active Tasks */}
                {metrics?.active_tasks !== undefined && (
                  <div className="glass rounded-lg px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gh-fg-muted">Active:</span>
                      <span className="text-sm font-bold text-cyan-400">
                        {metrics.active_tasks}
                      </span>
                    </div>
                  </div>
                )}

                {/* System Load */}
                {metrics?.system?.cpu_percent !== undefined && (
                  <div className="glass rounded-lg px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gh-fg-muted">CPU:</span>
                      <span className={`text-sm font-bold ${
                        metrics.system.cpu_percent > 80 ? 'text-red-400' :
                        metrics.system.cpu_percent > 50 ? 'text-yellow-400' :
                        'text-green-400'
                      }`}>
                        {metrics.system.cpu_percent}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
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
        </Tabs>

        {/* Footer */}
        <footer className="mt-16 text-center py-8 border-t border-white/10">
          <div className="glass inline-block rounded-2xl px-6 py-4">
            <p className="text-sm text-gh-fg-muted">
              Oxide v0.1.0 - Intelligent LLM Orchestration
            </p>
            <p className="text-sm mt-2">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-400 hover:text-cyan-300 transition-colors hover:underline"
              >
                API Documentation →
              </a>
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
