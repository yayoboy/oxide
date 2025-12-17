/**
 * Metrics Dashboard Component
 * Displays real-time system metrics
 */
import React from 'react';

const MetricsDashboard = ({ metrics }) => {
  if (!metrics) {
    return <div className="loading">Loading metrics...</div>;
  }

  const { services, tasks, system, websocket } = metrics;

  return (
    <div className="grid grid-2">
      {/* Services Overview */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🔧 Services</h3>
        </div>
        <div className="grid grid-2">
          <div className="metric">
            <div className="metric-label">Enabled</div>
            <div className="metric-value" style={{ color: '#3fb950' }}>
              {services?.enabled || 0}
            </div>
          </div>
          <div className="metric">
            <div className="metric-label">Healthy</div>
            <div className="metric-value" style={{ color: '#58a6ff' }}>
              {services?.healthy || 0}
            </div>
          </div>
        </div>
        {services?.unhealthy > 0 && (
          <div style={{ marginTop: '10px', color: '#f85149', fontSize: '0.9rem' }}>
            ⚠️ {services.unhealthy} service(s) unavailable
          </div>
        )}
      </div>

      {/* Tasks Overview */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">📊 Tasks</h3>
        </div>
        <div className="grid grid-2">
          <div className="metric">
            <div className="metric-label">Completed</div>
            <div className="metric-value" style={{ color: '#3fb950' }}>
              {tasks?.completed || 0}
            </div>
          </div>
          <div className="metric">
            <div className="metric-label">Running</div>
            <div className="metric-value" style={{ color: '#f7b955' }}>
              {tasks?.running || 0}
            </div>
          </div>
        </div>
        <div className="grid grid-2" style={{ marginTop: '10px' }}>
          <div className="metric">
            <div className="metric-label">Total</div>
            <div style={{ fontSize: '1.1rem', color: '#8b949e' }}>
              {tasks?.total || 0}
            </div>
          </div>
          <div className="metric">
            <div className="metric-label">Failed</div>
            <div style={{ fontSize: '1.1rem', color: '#f85149' }}>
              {tasks?.failed || 0}
            </div>
          </div>
        </div>
      </div>

      {/* System Resources */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">💻 System</h3>
        </div>
        <div className="metric">
          <div className="metric-label">CPU Usage</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="metric-value" style={{ color: getCPUColor(system?.cpu_percent) }}>
              {system?.cpu_percent?.toFixed(1) || 0}%
            </div>
            <div style={{ flex: 1, height: '8px', background: '#21262d', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${system?.cpu_percent || 0}%`,
                  height: '100%',
                  background: getCPUColor(system?.cpu_percent),
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">Memory Usage</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="metric-value" style={{ color: getMemoryColor(system?.memory_percent) }}>
              {system?.memory_percent?.toFixed(1) || 0}%
            </div>
            <div style={{ flex: 1, height: '8px', background: '#21262d', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${system?.memory_percent || 0}%`,
                  height: '100%',
                  background: getMemoryColor(system?.memory_percent),
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        </div>
        <div style={{ fontSize: '0.8rem', color: '#8b949e', marginTop: '10px' }}>
          {system?.memory_used_mb?.toFixed(0) || 0} MB / {system?.memory_total_mb?.toFixed(0) || 0} MB
        </div>
      </div>

      {/* WebSocket Status */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🔌 WebSocket</h3>
        </div>
        <div className="metric">
          <div className="metric-label">Active Connections</div>
          <div className="metric-value" style={{ color: '#58a6ff' }}>
            {websocket?.connections || 0}
          </div>
        </div>
        <div style={{ marginTop: '15px', fontSize: '0.9rem', color: '#8b949e' }}>
          Real-time updates {websocket?.connections > 0 ? 'enabled' : 'disabled'}
        </div>
      </div>
    </div>
  );
};

const getCPUColor = (percent) => {
  if (!percent) return '#3fb950';
  if (percent < 50) return '#3fb950';
  if (percent < 75) return '#f7b955';
  return '#f85149';
};

const getMemoryColor = (percent) => {
  if (!percent) return '#58a6ff';
  if (percent < 60) return '#58a6ff';
  if (percent < 80) return '#f7b955';
  return '#f85149';
};

export default MetricsDashboard;
