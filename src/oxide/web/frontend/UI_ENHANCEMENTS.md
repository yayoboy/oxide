# Oxide UI Enhancements

## Overview

Enhanced UI components for the Oxide LLM Orchestrator dashboard, focusing on:
1. **Compact Layout** - Maximum information density
2. **Visual Separation** - Clear distinction between CLI, Local, and Remote providers
3. **Enhanced Metrics** - Rich visualizations with sparklines and trends

## New Components

### 1. EnhancedLLMMetrics

Advanced LLM metrics visualization with mini sparkline charts.

**File:** `src/components/ui/EnhancedLLMMetrics.jsx`

**Features:**
- Mini sparkline charts showing historical trends
- Rich metric cards with color-coded themes
- Compact and grid layout modes
- Trend indicators (↑/↓ with percentage)
- Hover effects and smooth transitions

**Usage:**

```jsx
import { EnhancedLLMMetrics } from './components/ui/EnhancedLLMMetrics';

// Grid layout (default)
<EnhancedLLMMetrics llmMetrics={metrics.llm} />

// Compact layout
<EnhancedLLMMetrics llmMetrics={metrics.llm} layout="compact" />
```

**Props:**
- `llmMetrics` (object) - LLM performance metrics
  - `avg_latency_ms` - Average response latency
  - `tokens_per_sec` - Token generation throughput
  - `total_cost_usd` - Estimated API costs
  - `success_rate` - Success percentage
  - `latency_trend` - Trend percentage (±)
  - `throughput_trend` - Trend percentage (±)
- `layout` (string) - 'grid' or 'compact'

**Visual Features:**
- **Cyan** theme for latency metrics
- **Purple** theme for throughput metrics
- **Yellow** theme for cost metrics
- **Green** theme for success rate
- Animated sparklines showing last 20 data points
- Gradient accents and glassmorphism effects

---

### 2. ServiceHealthMatrix

Ultra-compact grid visualization of all services with visual health indicators.

**File:** `src/components/ui/ServiceHealthMatrix.jsx`

**Features:**
- Grid layout with service cells
- Color-coded by provider type (CLI/Local/Remote)
- Animated pulse for healthy services
- Hover tooltips with service details
- Section headers with health summaries
- Overall health percentage indicator

**Usage:**

```jsx
import { ServiceHealthMatrix } from './components/ui/ServiceHealthMatrix';

<ServiceHealthMatrix services={services} />
```

**Props:**
- `services` (object) - Services data from API
  - `services` (object) - Map of service_name → status
  - `healthy` (number) - Count of healthy services
  - `total` (number) - Total service count

**Provider Themes:**
- **CLI** (⚡ Blue/Cyan) - Command-line tools
- **Local** (🏠 Green/Emerald) - Localhost HTTP services
- **Remote** (🌐 Purple/Magenta) - External APIs

**Visual Features:**
- 3x4x6 responsive grid (mobile → tablet → desktop)
- Service initials as identifiers
- Status dot indicators
- Gradient backgrounds
- Pulse animations for online services
- Detailed hover tooltips

---

### 3. UltraCompactDashboard

Maximum information density dashboard combining all enhanced components.

**File:** `src/components/UltraCompactDashboard.jsx`

**Features:**
- Quick stats bar with inline metrics
- System resource bars (CPU/RAM/Disk)
- Provider type breakdown (CLI/Local/Remote counts)
- Layout switching (Matrix/List/Hybrid)
- Collapsible LLM metrics section
- Footer with uptime and timing stats

**Usage:**

```jsx
import { UltraCompactDashboard } from './components/UltraCompactDashboard';

<UltraCompactDashboard services={services} metrics={metrics} />
```

**Props:**
- `services` (object) - Services status data
- `metrics` (object) - System and LLM metrics
  - `system` - CPU, RAM, disk metrics
  - `llm` - LLM performance metrics
  - `active_tasks` - Current running tasks
  - `total_executions` - Historical count
  - `success_rate` - Overall success percentage
  - `avg_response_time_ms` - Average timing

**Layout Modes:**
1. **Matrix** (⊞) - Service health matrix view
2. **List** (☰) - Traditional list view
3. **Hybrid** (⊟) - Split view with matrix + activity

**Visual Hierarchy:**
- Top: Quick stats pills
- Middle: System resource bars
- Expandable: LLM metrics with sparklines
- Main: Services visualization (layout-dependent)
- Footer: Update time and summary stats

---

## Integration Guide

### Replacing CompactDashboard

To use the new ultra-compact dashboard in your app:

**In `App.jsx`:**

```jsx
// Replace this:
import CompactDashboard from './components/CompactDashboard';

// With this:
import { UltraCompactDashboard } from './components/UltraCompactDashboard';

// Then in your JSX:
<TabsContent value="dashboard">
  <UltraCompactDashboard services={services} metrics={metrics} />
</TabsContent>
```

### Using Individual Components

You can also use the enhanced components individually:

```jsx
import { EnhancedLLMMetrics } from './components/ui/EnhancedLLMMetrics';
import { ServiceHealthMatrix } from './components/ui/ServiceHealthMatrix';
import { CompactSystemBar } from './components/ui/CompactSystemBar';

function CustomDashboard({ services, metrics }) {
  return (
    <div className="space-y-4">
      {/* System resources */}
      <CompactSystemBar system={metrics.system} />

      {/* LLM performance */}
      <EnhancedLLMMetrics llmMetrics={metrics.llm} layout="grid" />

      {/* Service health */}
      <ServiceHealthMatrix services={services} />
    </div>
  );
}
```

---

## Design System

### Color Palette

**Provider Types:**
- CLI: `blue-500/cyan-500` (Electric blue)
- Local: `green-500/emerald-500` (Forest green)
- Remote: `purple-500/magenta-500` (Cosmic purple)

**Status Indicators:**
- Success: `cyan-400` (Bright cyan)
- Warning: `yellow-400` (Amber)
- Error: `red-400` (Coral red)
- Info: `purple-400` (Violet)
- Neutral: `white` (Ghost white)

**Metrics:**
- Latency: Cyan
- Throughput: Purple
- Cost: Yellow
- Success: Green

### Visual Effects

**Glassmorphism:**
```css
.glass {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

**Neon Glow:**
```css
.neon-glow {
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.pulse-neon {
  animation: pulse 2s infinite;
}
```

**Shimmer:**
```css
.shimmer {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  animation: shimmer 2s infinite;
}
```

### Spacing Scale

- **Compact:** 2px gaps, 3px padding
- **Standard:** 4px gaps, 4px padding
- **Comfortable:** 6px gaps, 6px padding

### Typography

- **Headers:** text-sm to text-lg, font-semibold
- **Metrics:** text-xl to text-3xl, font-bold
- **Labels:** text-xs, text-gh-fg-muted
- **Body:** text-sm, text-white/text-gh-fg-subtle

---

## Best Practices

### 1. Data Updates

Components automatically re-render when props change. Use WebSocket hooks for real-time updates:

```jsx
const { metrics } = useMetrics(); // Auto-updates via WebSocket
const { services } = useServices(); // Auto-updates via WebSocket

<EnhancedLLMMetrics llmMetrics={metrics?.llm} />
```

### 2. Performance

Sparkline data is mocked for now. To use real historical data:

```jsx
// Fetch historical metrics
const llmMetrics = {
  avg_latency_ms: 120,
  latency_history: [100, 110, 105, 115, 120, ...] // Last 20 samples
};

// Pass to component (modify EnhancedLLMMetrics to accept history)
```

### 3. Responsive Design

All components are mobile-first and responsive:

- **Mobile:** Single column, stacked layout
- **Tablet:** 2-column grid, horizontal bars
- **Desktop:** 3-4 column grid, full features

### 4. Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements
- Keyboard navigation support
- Color contrast ratios meet WCAG AA
- Tooltips for additional context

---

## Future Enhancements

1. **Historical Charts** - Full-featured time-series charts
2. **Real-time Sparklines** - Live data integration
3. **Alert Indicators** - Visual warnings for issues
4. **Customizable Layouts** - User-saveable preferences
5. **Export Metrics** - CSV/JSON download
6. **Dark Mode Variants** - Optimized color schemes
7. **Animation Controls** - Reduce motion preferences

---

## Examples

### Minimal Dashboard

```jsx
<UltraCompactDashboard
  services={{ total: 3, healthy: 3, services: {...} }}
  metrics={{
    active_tasks: 2,
    total_executions: 150,
    system: { cpu_percent: 45, memory_percent: 62 }
  }}
/>
```

### Full-Featured Dashboard

```jsx
<UltraCompactDashboard
  services={services}
  metrics={{
    active_tasks: 5,
    total_executions: 1250,
    success_rate: 98.5,
    avg_response_time_ms: 125,
    system: {
      cpu_percent: 45,
      memory_percent: 62,
      disk_percent: 75
    },
    llm: {
      avg_latency_ms: 120,
      tokens_per_sec: 45,
      total_cost_usd: 2.35,
      success_rate: 99.2,
      latency_trend: -5,
      throughput_trend: 12
    }
  }}
/>
```

---

## Troubleshooting

**Issue:** Sparklines not showing
**Solution:** Ensure `llmMetrics` prop is provided with numeric values

**Issue:** Services not categorized correctly
**Solution:** Verify `info.type` is 'cli' or 'http' and `info.base_url` contains localhost

**Issue:** Layout toggle not working
**Solution:** Check console for errors, ensure Tailwind classes are compiled

**Issue:** Colors not matching design
**Solution:** Verify Tailwind config includes custom colors (cyan, purple, etc.)

---

## License

MIT License - Oxide Project

## Contributors

- Enhanced by Claude Sonnet 4.5 with ui-styling skill
- Based on original Oxide dashboard by development team
