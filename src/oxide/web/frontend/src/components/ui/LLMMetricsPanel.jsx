/**
 * LLM Metrics Panel Component
 * Displays LLM-specific performance metrics
 */
import React from 'react';
import { cn } from '../../lib/utils';

const MetricMiniCard = ({ icon, label, value, unit, prefix = '', trend, color }) => {
  const colorClasses = {
    cyan: 'text-cyan-400 border-cyan-500/30',
    purple: 'text-purple-400 border-purple-500/30',
    yellow: 'text-yellow-400 border-yellow-500/30',
    green: 'text-green-400 border-green-500/30'
  };

  const formatValue = (val) => {
    if (val == null) return '0';
    if (val < 10) return val.toFixed(1);
    return val.toFixed(0);
  };

  return (
    <div className={cn(
      "rounded-lg p-3 border bg-white/5 transition-all hover:bg-white/10",
      colorClasses[color]
    )}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-lg">{icon}</span>
        {trend != null && trend !== 0 && (
          <span className={cn(
            "text-xs font-medium",
            trend > 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(0)}%
          </span>
        )}
      </div>
      <div className={cn("text-xl font-bold", colorClasses[color])}>
        {prefix}{formatValue(value)}{unit}
      </div>
      <div className="text-xs text-gh-fg-subtle truncate mt-1">{label}</div>
    </div>
  );
};

export const LLMMetricsPanel = ({ llmMetrics }) => {
  if (!llmMetrics || Object.keys(llmMetrics).length === 0) {
    return null;
  }

  return (
    <div className="glass rounded-xl p-4 border border-cyan-500/30">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xl">🤖</span>
        <h3 className="text-sm font-semibold text-white">LLM Performance Metrics</h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricMiniCard
          icon="⚡"
          label="Avg Latency"
          value={llmMetrics?.avg_latency_ms || 0}
          unit="ms"
          trend={llmMetrics?.latency_trend}
          color="cyan"
        />
        <MetricMiniCard
          icon="🔤"
          label="Tokens/sec"
          value={llmMetrics?.tokens_per_sec || 0}
          unit=" tok/s"
          trend={llmMetrics?.throughput_trend}
          color="purple"
        />
        <MetricMiniCard
          icon="💰"
          label="Est. Cost"
          value={llmMetrics?.total_cost_usd || 0}
          unit=""
          prefix="$"
          color="yellow"
        />
        <MetricMiniCard
          icon="✅"
          label="Success Rate"
          value={llmMetrics?.success_rate || 100}
          unit="%"
          color="green"
        />
      </div>
    </div>
  );
};

export default LLMMetricsPanel;
