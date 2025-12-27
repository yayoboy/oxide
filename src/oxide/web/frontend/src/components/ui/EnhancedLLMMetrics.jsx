/**
 * Enhanced LLM Metrics Component
 * Advanced metrics visualization with mini sparkline charts and rich indicators
 */
import React from 'react';
import { cn } from '../../lib/utils';

/**
 * Mini Sparkline Chart Component
 * Renders a simple line chart for metric trends
 */
const MiniSparkline = ({ data = [], color = 'cyan', height = 24 }) => {
  if (!data || data.length === 0) {
    return <div className={`h-${height} w-full bg-white/5 rounded`} />;
  }

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * 100;
    const y = 100 - ((value - min) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  const colorMap = {
    cyan: 'stroke-cyan-400',
    purple: 'stroke-purple-400',
    yellow: 'stroke-yellow-400',
    green: 'stroke-green-400',
    red: 'stroke-red-400'
  };

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className={`w-full opacity-60`}
      style={{ height: `${height}px` }}
    >
      {/* Area fill */}
      <polygon
        points={`0,100 ${points} 100,100`}
        className={`fill-${color}-500/10`}
      />
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        className={cn(colorMap[color], "stroke-2")}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
};

/**
 * Rich Metric Card with Sparkline
 */
const RichMetricCard = ({
  icon,
  label,
  value,
  unit,
  prefix = '',
  trend,
  sparklineData,
  color = 'cyan',
  subtext
}) => {
  const colorClasses = {
    cyan: {
      text: 'text-cyan-400',
      border: 'border-cyan-500/30',
      bg: 'bg-cyan-500/10',
      glow: 'shadow-cyan-500/20'
    },
    purple: {
      text: 'text-purple-400',
      border: 'border-purple-500/30',
      bg: 'bg-purple-500/10',
      glow: 'shadow-purple-500/20'
    },
    yellow: {
      text: 'text-yellow-400',
      border: 'border-yellow-500/30',
      bg: 'bg-yellow-500/10',
      glow: 'shadow-yellow-500/20'
    },
    green: {
      text: 'text-green-400',
      border: 'border-green-500/30',
      bg: 'bg-green-500/10',
      glow: 'shadow-green-500/20'
    }
  };

  const theme = colorClasses[color];

  const formatValue = (val) => {
    if (val == null) return '0';
    if (val < 10) return val.toFixed(1);
    if (val < 100) return val.toFixed(0);
    if (val < 1000) return val.toFixed(0);
    return (val / 1000).toFixed(1) + 'k';
  };

  return (
    <div
      className={cn(
        "relative rounded-xl border overflow-hidden transition-all hover:scale-[1.02]",
        "bg-gradient-to-br from-white/5 to-transparent backdrop-blur-sm",
        theme.border,
        theme.glow,
        "shadow-lg hover:shadow-xl"
      )}
      data-testid="metric-card"
    >
      {/* Top gradient accent */}
      <div className={cn("absolute top-0 left-0 right-0 h-1", theme.bg)} />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{icon}</span>
            <div>
              <div className="text-xs text-gh-fg-subtle uppercase tracking-wide">
                {label}
              </div>
              {subtext && (
                <div className="text-xs text-gh-fg-muted mt-0.5">
                  {subtext}
                </div>
              )}
            </div>
          </div>

          {/* Trend indicator */}
          {trend != null && trend !== 0 && (
            <div className={cn(
              "px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1",
              trend > 0
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
            )}>
              {trend > 0 ? '↑' : '↓'}
              {Math.abs(trend).toFixed(0)}%
            </div>
          )}
        </div>

        {/* Main value */}
        <div className={cn("text-3xl font-bold mb-3", theme.text)}>
          {prefix}{formatValue(value)}<span className="text-xl">{unit}</span>
        </div>

        {/* Sparkline */}
        {sparklineData && sparklineData.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/10">
            <MiniSparkline data={sparklineData} color={color} height={32} />
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Compact metric row for horizontal layout
 */
const CompactMetricRow = ({ icon, label, value, unit, prefix = '', color = 'cyan' }) => {
  const colorMap = {
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
    green: 'text-green-400'
  };

  return (
    <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="text-sm text-gh-fg-muted">{label}</span>
      </div>
      <div className={cn("text-lg font-bold", colorMap[color])}>
        {prefix}{value}{unit}
      </div>
    </div>
  );
};

/**
 * Main Enhanced LLM Metrics Panel
 */
export const EnhancedLLMMetrics = ({ llmMetrics, layout = 'grid' }) => {
  if (!llmMetrics || Object.keys(llmMetrics).length === 0) {
    return null;
  }

  // Generate mock sparkline data (replace with real historical data)
  const generateSparkline = (baseValue, variance = 20) => {
    return Array.from({ length: 20 }, (_, i) => {
      return Math.max(0, baseValue + (Math.random() - 0.5) * variance);
    });
  };

  const latencyData = generateSparkline(llmMetrics?.avg_latency_ms || 100, 50);
  const throughputData = generateSparkline(llmMetrics?.tokens_per_sec || 50, 20);
  const costData = generateSparkline(llmMetrics?.total_cost_usd || 0.05, 0.02);

  if (layout === 'compact') {
    return (
      <div className="glass rounded-xl p-4 border border-cyan-500/20">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">🤖</span>
          <h3 className="text-sm font-semibold text-white">LLM Performance</h3>
        </div>

        <div className="space-y-1">
          <CompactMetricRow
            icon="⚡"
            label="Latency"
            value={llmMetrics?.avg_latency_ms?.toFixed(0) || 0}
            unit="ms"
            color="cyan"
          />
          <CompactMetricRow
            icon="🔤"
            label="Throughput"
            value={llmMetrics?.tokens_per_sec?.toFixed(0) || 0}
            unit=" tok/s"
            color="purple"
          />
          <CompactMetricRow
            icon="💰"
            label="Cost"
            value={llmMetrics?.total_cost_usd?.toFixed(4) || 0}
            unit=""
            prefix="$"
            color="yellow"
          />
          <CompactMetricRow
            icon="✅"
            label="Success"
            value={llmMetrics?.success_rate?.toFixed(0) || 100}
            unit="%"
            color="green"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🤖</span>
        <div>
          <h3 className="text-lg font-semibold text-white">LLM Performance Metrics</h3>
          <p className="text-xs text-gh-fg-subtle">Real-time model performance tracking</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <RichMetricCard
          icon="⚡"
          label="Average Latency"
          value={llmMetrics?.avg_latency_ms || 0}
          unit="ms"
          trend={llmMetrics?.latency_trend}
          sparklineData={latencyData}
          color="cyan"
          subtext="Response time"
        />
        <RichMetricCard
          icon="🔤"
          label="Tokens/Second"
          value={llmMetrics?.tokens_per_sec || 0}
          unit=" tok/s"
          trend={llmMetrics?.throughput_trend}
          sparklineData={throughputData}
          color="purple"
          subtext="Generation speed"
        />
        <RichMetricCard
          icon="💰"
          label="Total Cost"
          value={llmMetrics?.total_cost_usd || 0}
          unit=""
          prefix="$"
          sparklineData={costData}
          color="yellow"
          subtext="API usage"
        />
        <RichMetricCard
          icon="✅"
          label="Success Rate"
          value={llmMetrics?.success_rate || 100}
          unit="%"
          color="green"
          subtext="Reliability"
        />
      </div>
    </div>
  );
};

export default EnhancedLLMMetrics;
