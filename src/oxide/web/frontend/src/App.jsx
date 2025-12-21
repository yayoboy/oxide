/**
 * Main App Component
 * Oxide LLM Orchestrator Dashboard
 */
import React, { useState } from 'react';
import ServiceCard from './components/ServiceCard';
import MetricsDashboard from './components/MetricsDashboard';
import TaskHistory from './components/TaskHistory';
import TaskExecutor from './components/TaskExecutor';
import TaskAssignmentManager from './components/TaskAssignmentManager';
import { useServices } from './hooks/useServices';
import { useMetrics } from './hooks/useMetrics';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { services, loading: servicesLoading, error: servicesError } = useServices(5000);
  const { metrics, loading: metricsLoading } = useMetrics(2000);
  const { connected: wsConnected, messages: wsMessages } = useWebSocket();
  const [taskHistoryKey, setTaskHistoryKey] = useState(0);

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <div className="container">
          <h1>🔬 Oxide LLM Orchestrator</h1>
          <p>
            Intelligent routing and orchestration for distributed AI resources
            {wsConnected && (
              <span style={{ marginLeft: '15px', color: '#3fb950' }}>
                ● Live
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="container">
        {/* Metrics Dashboard */}
        <section style={{ marginBottom: '30px' }}>
          <h2 style={{ marginBottom: '20px', fontSize: '1.5rem' }}>System Metrics</h2>
          {metricsLoading ? (
            <div className="loading">Loading metrics...</div>
          ) : (
            <MetricsDashboard metrics={metrics} />
          )}
        </section>

        {/* Task Executor */}
        <section style={{ marginBottom: '30px' }}>
          <TaskExecutor onTaskCompleted={() => setTaskHistoryKey((prev) => prev + 1)} />
        </section>

        {/* Services Section */}
        <section style={{ marginBottom: '30px' }}>
          <h2 style={{ marginBottom: '20px', fontSize: '1.5rem' }}>
            LLM Services
            {services && (
              <span style={{ marginLeft: '15px', fontSize: '1rem', color: '#8b949e' }}>
                ({services.enabled}/{services.total} enabled)
              </span>
            )}
          </h2>

          {servicesLoading ? (
            <div className="loading">Loading services...</div>
          ) : servicesError ? (
            <div className="error">Error loading services: {servicesError}</div>
          ) : services && services.services ? (
            <div className="grid grid-3">
              {Object.entries(services.services).map(([name, status]) => (
                <ServiceCard key={name} name={name} status={status} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">⚙️</div>
              <div>No services configured</div>
            </div>
          )}
        </section>

        {/* Task Assignment Manager */}
        <section style={{ marginBottom: '30px' }}>
          <TaskAssignmentManager />
        </section>

        {/* Task History */}
        <section style={{ marginBottom: '30px' }}>
          <h2 style={{ marginBottom: '20px', fontSize: '1.5rem' }}>Task History</h2>
          <TaskHistory key={taskHistoryKey} />
        </section>

        {/* WebSocket Messages (Debug) */}
        {wsMessages.length > 0 && (
          <section style={{ marginBottom: '30px' }}>
            <h2 style={{ marginBottom: '20px', fontSize: '1.5rem' }}>Live Updates</h2>
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">🔔 Real-time Events</h3>
                <span className="badge badge-info">
                  {wsMessages.length} message(s)
                </span>
              </div>
              <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                {wsMessages.slice(-10).reverse().map((msg, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px',
                      margin: '5px 0',
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    <div style={{ color: '#58a6ff', marginBottom: '5px' }}>
                      {msg.type}
                    </div>
                    <div style={{ color: '#8b949e' }}>
                      {JSON.stringify(msg, null, 2).substring(0, 200)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Footer */}
        <footer style={{ textAlign: 'center', padding: '40px 0', color: '#8b949e', fontSize: '0.85rem' }}>
          <p>Oxide v0.1.0 - Intelligent LLM Orchestration</p>
          <p style={{ marginTop: '5px' }}>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#58a6ff', textDecoration: 'none' }}
            >
              API Documentation
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
