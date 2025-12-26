/**
 * Main App Component
 * Oxide LLM Orchestrator Dashboard with Glassmorphism UI
 */
import React, { useState } from 'react';
import ServiceCard from './components/ServiceCard';
import MetricsDashboard from './components/MetricsDashboard';
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

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl border-b border-white/10">
        <div className="glass">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center text-2xl neon-glow">
                  🔬
                </div>
                <div>
                  <h1 className="text-3xl font-bold neon-text">
                    Oxide LLM Orchestrator
                  </h1>
                  <p className="text-sm text-gh-fg-muted mt-1">
                    Intelligent AI Resource Management
                  </p>
                </div>
              </div>

              {/* Status Indicator */}
              <div className="flex items-center gap-4">
                {wsConnected && (
                  <div className="glass rounded-full px-4 py-2 flex items-center gap-2 neon-glow">
                    <div className="w-2 h-2 bg-cyan-400 rounded-full pulse-neon" />
                    <span className="text-sm font-medium text-cyan-400">Live</span>
                  </div>
                )}
                <div className="text-right">
                  <div className="text-sm text-gh-fg-muted">Services</div>
                  <div className="text-lg font-bold text-white">
                    {services?.healthy || 0}/{services?.enabled || 0}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview" icon="📊">
              Overview
            </TabsTrigger>
            <TabsTrigger value="monitor" icon="💻">
              System Monitor
            </TabsTrigger>
            <TabsTrigger value="services" icon="🔧">
              Services
            </TabsTrigger>
            <TabsTrigger value="tasks" icon="⚡">
              Tasks
            </TabsTrigger>
            <TabsTrigger value="routing" icon="🔀">
              Routing
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="space-y-8">
              {/* Quick Stats */}
              {metricsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="glass rounded-2xl px-8 py-4">
                    <div className="text-gh-fg-muted animate-pulse">Loading metrics...</div>
                  </div>
                </div>
              ) : (
                <MetricsDashboard metrics={metrics} />
              )}

              {/* Task Executor */}
              <TaskExecutor onTaskCompleted={() => setTaskHistoryKey((prev) => prev + 1)} />

              {/* Recent Tasks */}
              <TaskHistory key={taskHistoryKey} />
            </div>
          </TabsContent>

          {/* System Monitor Tab */}
          <TabsContent value="monitor">
            <SystemMonitor />
          </TabsContent>

          {/* Services Tab */}
          <TabsContent value="services">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold neon-text">LLM Services</h2>
                {services && (
                  <div className="flex items-center gap-3">
                    <div className="glass rounded-full px-4 py-2 flex items-center gap-2">
                      <div className="w-2 h-2 bg-cyan-400 rounded-full pulse-neon" />
                      <span className="text-sm font-medium text-cyan-400">
                        {services.healthy} Healthy
                      </span>
                    </div>
                    {services.total - services.healthy > 0 && (
                      <div className="glass rounded-full px-4 py-2 flex items-center gap-2 border-red-500/30">
                        <div className="w-2 h-2 bg-red-400 rounded-full" />
                        <span className="text-sm font-medium text-red-400">
                          {services.total - services.healthy} Offline
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {servicesLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="glass rounded-2xl px-8 py-4">
                    <div className="text-gh-fg-muted animate-pulse">Loading services...</div>
                  </div>
                </div>
              ) : servicesError ? (
                <div className="glass rounded-2xl p-6 border-2 border-red-500/30 bg-red-500/10">
                  <p className="text-red-400">Error loading services: {servicesError}</p>
                </div>
              ) : services && services.services ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {Object.entries(services.services).map(([name, status]) => (
                    <ServiceCard key={name} name={name} status={status} />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="glass rounded-3xl p-12 text-center">
                    <div className="text-7xl mb-4 opacity-20">⚙️</div>
                    <div className="text-gh-fg-muted text-lg">No services configured</div>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Tasks Tab */}
          <TabsContent value="tasks">
            <div className="space-y-8">
              <TaskExecutor onTaskCompleted={() => setTaskHistoryKey((prev) => prev + 1)} />
              <TaskHistory key={taskHistoryKey} />
            </div>
          </TabsContent>

          {/* Routing Tab */}
          <TabsContent value="routing">
            <TaskAssignmentManager />
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
