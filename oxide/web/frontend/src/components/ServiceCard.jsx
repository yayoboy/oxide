/**
 * Service Card Component
 * Displays information about an LLM service
 */
import React from 'react';

const ServiceCard = ({ name, status }) => {
  const { healthy, info } = status || {};
  const isHealthy = healthy === true;

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <span className={`status-indicator ${isHealthy ? 'status-healthy' : 'status-unhealthy'}`}></span>
          {name}
        </h3>
        <span className={`badge ${isHealthy ? 'badge-success' : 'badge-error'}`}>
          {isHealthy ? 'Healthy' : 'Unavailable'}
        </span>
      </div>

      {info && (
        <div className="service-info">
          <div className="metric">
            <div className="metric-label">Type</div>
            <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>
              {info.type?.value || info.type || 'Unknown'}
            </div>
          </div>

          {info.description && (
            <div className="metric">
              <div className="metric-label">Description</div>
              <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>
                {info.description}
              </div>
            </div>
          )}

          {info.base_url && (
            <div className="metric">
              <div className="metric-label">Base URL</div>
              <div style={{ color: '#58a6ff', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                {info.base_url}
              </div>
            </div>
          )}

          {info.default_model && (
            <div className="metric">
              <div className="metric-label">Default Model</div>
              <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>
                {info.default_model}
              </div>
            </div>
          )}

          {info.optimal_for && info.optimal_for.length > 0 && (
            <div className="metric">
              <div className="metric-label">Optimal For</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '5px' }}>
                {info.optimal_for.slice(0, 3).map((item, idx) => (
                  <span key={idx} className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ServiceCard;
