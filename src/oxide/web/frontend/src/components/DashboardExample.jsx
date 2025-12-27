/**
 * Dashboard Example - Integration Guide
 * Shows how to use the new enhanced UI components
 */
import React, { useState } from 'react';
import { UltraCompactDashboard } from './UltraCompactDashboard';
import { EnhancedLLMMetrics } from './ui/EnhancedLLMMetrics';
import { ServiceHealthMatrix } from './ui/ServiceHealthMatrix';
import { CompactSystemBar } from './ui/CompactSystemBar';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/Tabs';

/**
 * Mock data generator for demonstration
 */
const generateMockData = () => {
  return {
    services: {
      total: 6,
      healthy: 5,
      services: {
        // CLI providers
        'qwen': {
          enabled: true,
          healthy: true,
          info: {
            type: 'cli',
            command: 'qwen',
            default_model: 'qwen-turbo'
          }
        },
        'gemini': {
          enabled: true,
          healthy: true,
          info: {
            type: 'cli',
            command: 'gemini',
            default_model: 'gemini-1.5-pro'
          }
        },
        // Local HTTP providers
        'ollama_local': {
          enabled: true,
          healthy: true,
          info: {
            type: 'http',
            base_url: 'http://localhost:11434',
            model: 'llama3.2'
          }
        },
        'lm_studio': {
          enabled: true,
          healthy: false,
          info: {
            type: 'http',
            base_url: 'http://127.0.0.1:1234',
            model: 'auto-detect'
          }
        },
        // Remote providers
        'openai': {
          enabled: true,
          healthy: true,
          info: {
            type: 'http',
            base_url: 'https://api.openai.com/v1',
            default_model: 'gpt-4-turbo'
          }
        },
        'anthropic': {
          enabled: true,
          healthy: true,
          info: {
            type: 'http',
            base_url: 'https://api.anthropic.com/v1',
            default_model: 'claude-3-opus'
          }
        }
      }
    },
    metrics: {
      active_tasks: 3,
      total_executions: 1247,
      success_rate: 98.4,
      avg_response_time_ms: 134,
      system: {
        cpu_percent: 42.5,
        memory_percent: 68.3,
        disk_percent: 71.2
      },
      llm: {
        avg_latency_ms: 125,
        tokens_per_sec: 48.5,
        total_cost_usd: 3.47,
        success_rate: 99.1,
        latency_trend: -7.2,
        throughput_trend: 14.5
      }
    }
  };
};

/**
 * Example 1: Full Ultra Compact Dashboard
 */
export const Example1_FullDashboard = () => {
  const mockData = generateMockData();

  return (
    <div className="min-h-screen bg-gh-canvas p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">
            Example 1: Full Ultra Compact Dashboard
          </h1>
          <p className="text-sm text-gh-fg-muted">
            Complete dashboard with all features enabled
          </p>
        </div>

        <UltraCompactDashboard
          services={mockData.services}
          metrics={mockData.metrics}
        />
      </div>
    </div>
  );
};

/**
 * Example 2: Individual Components
 */
export const Example2_IndividualComponents = () => {
  const mockData = generateMockData();

  return (
    <div className="min-h-screen bg-gh-canvas p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Example 2: Individual Components
          </h1>
          <p className="text-sm text-gh-fg-muted">
            Using enhanced components separately
          </p>
        </div>

        {/* System Bar */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">System Resources</h2>
          <CompactSystemBar system={mockData.metrics.system} />
        </div>

        {/* LLM Metrics - Grid Layout */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">
            LLM Metrics - Grid Layout
          </h2>
          <EnhancedLLMMetrics
            llmMetrics={mockData.metrics.llm}
            layout="grid"
          />
        </div>

        {/* LLM Metrics - Compact Layout */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">
            LLM Metrics - Compact Layout
          </h2>
          <EnhancedLLMMetrics
            llmMetrics={mockData.metrics.llm}
            layout="compact"
          />
        </div>

        {/* Service Health Matrix */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">
            Service Health Matrix
          </h2>
          <ServiceHealthMatrix services={mockData.services} />
        </div>
      </div>
    </div>
  );
};

/**
 * Example 3: Custom Integration
 */
export const Example3_CustomIntegration = () => {
  const [view, setView] = useState('overview');
  const mockData = generateMockData();

  return (
    <div className="min-h-screen bg-gh-canvas p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">
            Example 3: Custom Integration
          </h1>
          <p className="text-sm text-gh-fg-muted">
            Custom layout with tabs combining different views
          </p>
        </div>

        <Tabs value={view} onValueChange={setView}>
          <TabsList>
            <TabsTrigger value="overview" icon="📊">
              Overview
            </TabsTrigger>
            <TabsTrigger value="performance" icon="⚡">
              Performance
            </TabsTrigger>
            <TabsTrigger value="health" icon="🔧">
              Health
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <UltraCompactDashboard
              services={mockData.services}
              metrics={mockData.metrics}
            />
          </TabsContent>

          <TabsContent value="performance">
            <div className="space-y-6">
              <CompactSystemBar system={mockData.metrics.system} />
              <EnhancedLLMMetrics
                llmMetrics={mockData.metrics.llm}
                layout="grid"
              />
            </div>
          </TabsContent>

          <TabsContent value="health">
            <ServiceHealthMatrix services={mockData.services} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

/**
 * Example 4: Minimal Dashboard
 */
export const Example4_MinimalDashboard = () => {
  const minimalData = {
    services: {
      total: 2,
      healthy: 2,
      services: {
        'qwen': {
          enabled: true,
          healthy: true,
          info: { type: 'cli', command: 'qwen' }
        },
        'ollama': {
          enabled: true,
          healthy: true,
          info: {
            type: 'http',
            base_url: 'http://localhost:11434',
            model: 'llama3.2'
          }
        }
      }
    },
    metrics: {
      active_tasks: 0,
      total_executions: 42,
      system: {
        cpu_percent: 15.2,
        memory_percent: 45.8
      }
    }
  };

  return (
    <div className="min-h-screen bg-gh-canvas p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">
            Example 4: Minimal Dashboard
          </h1>
          <p className="text-sm text-gh-fg-muted">
            Basic setup with minimal data
          </p>
        </div>

        <UltraCompactDashboard
          services={minimalData.services}
          metrics={minimalData.metrics}
        />
      </div>
    </div>
  );
};

/**
 * Main Demo Component - Switch between examples
 */
export const DashboardDemo = () => {
  const [example, setExample] = useState('1');

  const examples = {
    '1': <Example1_FullDashboard />,
    '2': <Example2_IndividualComponents />,
    '3': <Example3_CustomIntegration />,
    '4': <Example4_MinimalDashboard />
  };

  return (
    <div className="relative">
      {/* Example selector */}
      <div className="fixed top-4 right-4 z-50 glass rounded-lg p-3">
        <div className="text-xs text-gh-fg-muted mb-2">Select Example:</div>
        <div className="flex flex-col gap-1">
          {Object.keys(examples).map(num => (
            <button
              key={num}
              onClick={() => setExample(num)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                example === num
                  ? 'bg-cyan-500/30 text-cyan-400'
                  : 'text-gh-fg-muted hover:text-white hover:bg-white/5'
              }`}
            >
              Example {num}
            </button>
          ))}
        </div>
      </div>

      {/* Render selected example */}
      {examples[example]}
    </div>
  );
};

export default DashboardDemo;
