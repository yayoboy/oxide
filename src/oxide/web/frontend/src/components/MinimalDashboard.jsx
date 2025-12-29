/**
 * Minimal Dashboard - Fast, Clean, Essential
 * Single source of truth for Oxide dashboard
 */
import React from 'react';

const MinimalDashboard = ({ services, metrics }) => {
  if (!services || !services.services) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  const servicesList = Object.entries(services.services || {});
  const healthyCount = services.healthy || 0;
  const totalCount = services.total || 0;
  const healthPercent = totalCount > 0 ? Math.round((healthyCount / totalCount) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Quick Stats - Simple Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Services"
          value={`${healthyCount}/${totalCount}`}
          status={healthPercent >= 80 ? 'good' : healthPercent >= 50 ? 'warning' : 'error'}
        />
        <StatCard
          label="Active Tasks"
          value={metrics?.active_tasks || 0}
          status="neutral"
        />
        <StatCard
          label="Total Runs"
          value={metrics?.total_executions || 0}
          status="neutral"
        />
        <StatCard
          label="CPU"
          value={`${metrics?.system?.cpu_percent || 0}%`}
          status={
            (metrics?.system?.cpu_percent || 0) > 80 ? 'error' :
            (metrics?.system?.cpu_percent || 0) > 50 ? 'warning' : 'good'
          }
        />
      </div>

      {/* Services List - Simple Table */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div className="bg-gray-50 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Services ({servicesList.length})
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {servicesList.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
              No services configured
            </div>
          ) : (
            servicesList.map(([name, service]) => (
              <ServiceRow key={name} name={name} service={service} />
            ))
          )}
        </div>
      </div>

      {/* System Info - Compact */}
      {metrics?.system && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <SystemMetric label="Memory" value={`${metrics.system.memory_percent || 0}%`} />
          <SystemMetric label="Disk" value={`${metrics.system.disk_percent || 0}%`} />
          <SystemMetric label="Uptime" value={formatUptime(metrics.uptime_seconds)} />
          <SystemMetric label="Version" value="0.1.0" />
        </div>
      )}
    </div>
  );
};

// Stat Card - Minimal Design
const StatCard = ({ label, value, status }) => {
  const statusColors = {
    good: 'text-green-600 dark:text-green-400 border-green-200 dark:border-green-800',
    warning: 'text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800',
    error: 'text-red-600 dark:text-red-400 border-red-200 dark:border-red-800',
    neutral: 'text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700'
  };

  return (
    <div className={`border rounded-lg p-4 ${statusColors[status] || statusColors.neutral}`}>
      <div className="text-xs font-medium uppercase tracking-wide opacity-70 mb-1">
        {label}
      </div>
      <div className="text-2xl font-bold">
        {value}
      </div>
    </div>
  );
};

// Service Row - Clean List Item
const ServiceRow = ({ name, service }) => {
  const isHealthy = service.healthy;
  const serviceType = service.info?.type || 'unknown';
  const baseUrl = service.info?.base_url || service.info?.executable || '-';

  return (
    <div className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Status Dot */}
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
            isHealthy ? 'bg-green-500' : 'bg-red-500'
          }`} />

          {/* Service Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {name}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                {serviceType}
              </span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
              {baseUrl}
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div className={`text-xs font-medium px-2 py-1 rounded ${
          isHealthy
            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
        }`}>
          {isHealthy ? 'Healthy' : 'Down'}
        </div>
      </div>
    </div>
  );
};

// System Metric - Simple Display
const SystemMetric = ({ label, value }) => (
  <div className="text-gray-600 dark:text-gray-400">
    <span className="opacity-70">{label}:</span>{' '}
    <span className="font-medium text-gray-900 dark:text-gray-100">{value}</span>
  </div>
);

// Utility: Format uptime
const formatUptime = (seconds) => {
  if (!seconds) return '0s';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${Math.floor(seconds)}s`;
};

export default MinimalDashboard;
