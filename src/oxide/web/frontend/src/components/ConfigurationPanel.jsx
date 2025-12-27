import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { Alert, AlertDescription } from './ui/Alert';

const ConfigurationPanel = () => {
  const [config, setConfig] = useState(null);
  const [reloadStats, setReloadStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloading, setReloading] = useState(false);
  const [lastReload, setLastReload] = useState(null);
  const [apiKeyStatus, setApiKeyStatus] = useState({});
  const [testingKey, setTestingKey] = useState(null);

  // Fetch configuration
  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/config');
      if (!response.ok) throw new Error('Failed to fetch configuration');
      const data = await response.json();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch reload stats
  const fetchReloadStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/config/reload/stats');
      if (!response.ok) throw new Error('Failed to fetch reload stats');
      const data = await response.json();
      setReloadStats(data);
    } catch (err) {
      console.error('Error fetching reload stats:', err);
    }
  };

  // Reload configuration
  const handleReload = async () => {
    try {
      setReloading(true);
      setError(null);

      const response = await fetch('http://localhost:8000/api/config/reload', {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reload configuration');
      }

      const result = await response.json();
      setLastReload(result);

      // Refresh configuration and stats
      await fetchConfig();
      await fetchReloadStats();

      // Show success message
      setTimeout(() => setLastReload(null), 5000);
    } catch (err) {
      setError(err.message);
    } finally {
      setReloading(false);
    }
  };

  // Toggle service enabled/disabled
  const toggleService = async (serviceName, currentlyEnabled) => {
    try {
      const response = await fetch(`http://localhost:8000/api/config/services/${serviceName}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled: !currentlyEnabled,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update service');
      }

      // Refresh configuration
      await fetchConfig();
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch API key status for a service
  const fetchApiKeyStatus = async (serviceName) => {
    try {
      const response = await fetch(`http://localhost:8000/api/api-keys/status/${serviceName}`);
      if (!response.ok) return null;
      const data = await response.json();
      return data;
    } catch (err) {
      console.error(`Error fetching API key status for ${serviceName}:`, err);
      return null;
    }
  };

  // Test API key for a service
  const testApiKey = async (serviceName) => {
    try {
      setTestingKey(serviceName);
      const response = await fetch('http://localhost:8000/api/api-keys/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service: serviceName,
        }),
      });

      const result = await response.json();

      // Update the API key status with test result
      setApiKeyStatus(prev => ({
        ...prev,
        [serviceName]: {
          ...prev[serviceName],
          testResult: result
        }
      }));

      // Clear test result after 5 seconds
      setTimeout(() => {
        setApiKeyStatus(prev => ({
          ...prev,
          [serviceName]: {
            ...prev[serviceName],
            testResult: null
          }
        }));
      }, 5000);
    } catch (err) {
      console.error('Error testing API key:', err);
    } finally {
      setTestingKey(null);
    }
  };

  // Load API key status for services that require keys
  useEffect(() => {
    const loadApiKeyStatuses = async () => {
      if (!config || !config.services) return;

      const servicesRequiringKeys = ['openrouter'];
      const statuses = {};

      for (const serviceName of servicesRequiringKeys) {
        if (config.services[serviceName]) {
          const status = await fetchApiKeyStatus(serviceName);
          if (status) {
            statuses[serviceName] = status;
          }
        }
      }

      setApiKeyStatus(statuses);
    };

    loadApiKeyStatuses();
  }, [config]);

  useEffect(() => {
    fetchConfig();
    fetchReloadStats();

    // Refresh stats periodically
    const interval = setInterval(fetchReloadStats, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-gh-fg-muted">Loading configuration...</p>
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertDescription>
          <strong>Error:</strong> {error}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Configuration</h1>
          <p className="text-gh-fg-muted">
            View and manage Oxide configuration settings
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Reload Stats */}
          {reloadStats && reloadStats.enabled && (
            <div className="glass rounded-lg px-4 py-2">
              <div className="text-xs text-gh-fg-muted mb-1">Hot Reload</div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${reloadStats.watching ? 'bg-green-400' : 'bg-gray-400'}`}></div>
                <span className="text-sm font-mono text-white">
                  {reloadStats.reload_count} reloads
                </span>
              </div>
            </div>
          )}

          {/* Reload Button */}
          <Button
            onClick={handleReload}
            disabled={reloading}
            className="bg-cyan-600 hover:bg-cyan-700 text-white"
          >
            {reloading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Reloading...
              </>
            ) : (
              <>
                🔄 Reload Configuration
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Success/Error Messages */}
      {lastReload && (
        <Alert className="bg-green-900/20 border-green-700">
          <AlertDescription className="text-green-400">
            ✅ Configuration reloaded successfully!
            {Object.keys(lastReload.changes).length > 0 && (
              <div className="mt-2 text-sm">
                Changes: {Object.keys(lastReload.changes).join(', ')}
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            <strong>Error:</strong> {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Configuration Tabs */}
      <Tabs defaultValue="services" className="space-y-4">
        <TabsList className="glass">
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="routing">Routing Rules</TabsTrigger>
          <TabsTrigger value="execution">Execution</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="cluster">Cluster</TabsTrigger>
        </TabsList>

        {/* Services Tab */}
        <TabsContent value="services" className="space-y-4">
          <Card className="glass">
            <CardHeader>
              <CardTitle>LLM Services</CardTitle>
              <CardDescription>
                Configure and manage LLM service providers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {config && config.services && Object.entries(config.services).map(([name, service]) => (
                  <div
                    key={name}
                    className="glass rounded-lg p-4 flex items-start justify-between hover:bg-gh-canvas-subtle transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-white">{name}</h3>
                        <Badge variant={service.enabled ? "default" : "secondary"}>
                          {service.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        <Badge variant="outline" className="font-mono text-xs">
                          {service.type}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        {service.executable && (
                          <div>
                            <span className="text-gh-fg-muted">Executable:</span>
                            <span className="ml-2 font-mono text-white">{service.executable}</span>
                          </div>
                        )}
                        {service.base_url && (
                          <div>
                            <span className="text-gh-fg-muted">URL:</span>
                            <span className="ml-2 font-mono text-white">{service.base_url}</span>
                          </div>
                        )}
                        {service.default_model && (
                          <div>
                            <span className="text-gh-fg-muted">Model:</span>
                            <span className="ml-2 font-mono text-white">{service.default_model}</span>
                          </div>
                        )}
                        {service.max_context_tokens && (
                          <div>
                            <span className="text-gh-fg-muted">Context:</span>
                            <span className="ml-2 font-mono text-white">
                              {(service.max_context_tokens / 1000).toFixed(0)}K tokens
                            </span>
                          </div>
                        )}
                      </div>

                      {service.capabilities && service.capabilities.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {service.capabilities.map((cap) => (
                            <Badge key={cap} variant="outline" className="text-xs">
                              {cap}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* API Key Status (for services that require keys) */}
                      {apiKeyStatus[name] && (
                        <div className="mt-4 p-3 glass rounded-lg border border-gh-border-default">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-gh-fg-muted">API Key:</span>
                              {apiKeyStatus[name].configured ? (
                                <>
                                  <Badge variant="default" className="text-xs bg-green-600">Configured</Badge>
                                  <code className="text-xs font-mono text-gh-fg-muted">
                                    {apiKeyStatus[name].key_preview}
                                  </code>
                                </>
                              ) : (
                                <Badge variant="destructive" className="text-xs">Not Configured</Badge>
                              )}
                            </div>

                            {apiKeyStatus[name].configured && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => testApiKey(name)}
                                disabled={testingKey === name}
                                className="text-xs h-7"
                              >
                                {testingKey === name ? (
                                  <>
                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                                    Testing...
                                  </>
                                ) : (
                                  '🔍 Test Key'
                                )}
                              </Button>
                            )}
                          </div>

                          {/* Test Result */}
                          {apiKeyStatus[name].testResult && (
                            <div className={`mt-2 p-2 rounded text-xs ${
                              apiKeyStatus[name].testResult.success
                                ? 'bg-green-900/20 text-green-400 border border-green-700'
                                : 'bg-red-900/20 text-red-400 border border-red-700'
                            }`}>
                              {apiKeyStatus[name].testResult.message}
                            </div>
                          )}

                          {/* Instructions if not configured */}
                          {!apiKeyStatus[name].configured && (
                            <div className="mt-2 text-xs text-gh-fg-muted">
                              <div className="font-semibold mb-1">To configure:</div>
                              <code className="bg-gh-canvas-default px-2 py-1 rounded block">
                                export {name.toUpperCase()}_API_KEY='your_key_here'
                              </code>
                              <div className="mt-1 text-[10px] text-gh-fg-muted/70">
                                Then restart the Oxide server
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <Button
                      size="sm"
                      variant={service.enabled ? "destructive" : "default"}
                      onClick={() => toggleService(name, service.enabled)}
                      className="ml-4"
                    >
                      {service.enabled ? 'Disable' : 'Enable'}
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Routing Rules Tab */}
        <TabsContent value="routing" className="space-y-4">
          <Card className="glass">
            <CardHeader>
              <CardTitle>Routing Rules</CardTitle>
              <CardDescription>
                Task type routing configuration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {config && config.routing_rules && Object.entries(config.routing_rules).map(([taskType, rule]) => (
                  <div
                    key={taskType}
                    className="glass rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-white">{taskType}</h3>
                      {rule.timeout_seconds && (
                        <Badge variant="outline" className="font-mono">
                          {rule.timeout_seconds}s timeout
                        </Badge>
                      )}
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gh-fg-muted w-20">Primary:</span>
                        <Badge variant="default" className="font-mono">
                          {rule.primary}
                        </Badge>
                      </div>

                      {rule.fallback && rule.fallback.length > 0 && (
                        <div className="flex items-start gap-2">
                          <span className="text-gh-fg-muted w-20 pt-1">Fallback:</span>
                          <div className="flex flex-wrap gap-2">
                            {rule.fallback.map((service, idx) => (
                              <Badge key={service} variant="secondary" className="font-mono">
                                {idx + 1}. {service}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {rule.parallel_threshold_files && (
                        <div className="flex items-center gap-2">
                          <span className="text-gh-fg-muted w-20">Parallel:</span>
                          <span className="text-white">
                            {rule.parallel_threshold_files} files
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Execution Tab */}
        <TabsContent value="execution">
          <Card className="glass">
            <CardHeader>
              <CardTitle>Execution Settings</CardTitle>
              <CardDescription>
                Global execution and retry configuration
              </CardDescription>
            </CardHeader>
            <CardContent>
              {config && config.execution && (
                <div className="grid grid-cols-2 gap-4">
                  <ConfigItem
                    label="Max Parallel Workers"
                    value={config.execution.max_parallel_workers}
                  />
                  <ConfigItem
                    label="Default Timeout"
                    value={`${config.execution.timeout_seconds}s`}
                  />
                  <ConfigItem
                    label="Streaming"
                    value={config.execution.streaming ? 'Enabled' : 'Disabled'}
                  />
                  <ConfigItem
                    label="Retry on Failure"
                    value={config.execution.retry_on_failure ? 'Enabled' : 'Disabled'}
                  />
                  <ConfigItem
                    label="Max Retries"
                    value={config.execution.max_retries}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Memory Tab */}
        <TabsContent value="memory">
          <Card className="glass">
            <CardHeader>
              <CardTitle>Context Memory Settings</CardTitle>
              <CardDescription>
                Conversation memory and context retrieval configuration
              </CardDescription>
            </CardHeader>
            <CardContent>
              {config && config.memory ? (
                <div className="grid grid-cols-2 gap-4">
                  <ConfigItem
                    label="Enabled"
                    value={config.memory.enabled ? 'Yes' : 'No'}
                  />
                  <ConfigItem
                    label="Storage Path"
                    value={config.memory.storage_path}
                  />
                  <ConfigItem
                    label="Max Conversations"
                    value={config.memory.max_conversations}
                  />
                  <ConfigItem
                    label="Max Age (days)"
                    value={config.memory.max_age_days}
                  />
                  <ConfigItem
                    label="Messages Per Conversation"
                    value={config.memory.max_messages_per_conversation}
                  />
                  <ConfigItem
                    label="Auto-Prune"
                    value={config.memory.auto_prune_enabled ? 'Enabled' : 'Disabled'}
                  />
                  <ConfigItem
                    label="Similarity Threshold"
                    value={config.memory.similarity_threshold}
                  />
                </div>
              ) : (
                <p className="text-gh-fg-muted">Memory not configured</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cluster Tab */}
        <TabsContent value="cluster">
          <Card className="glass">
            <CardHeader>
              <CardTitle>Cluster Configuration</CardTitle>
              <CardDescription>
                Multi-machine coordination settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              {config && config.cluster ? (
                <div className="grid grid-cols-2 gap-4">
                  <ConfigItem
                    label="Enabled"
                    value={config.cluster.enabled ? 'Yes' : 'No'}
                  />
                  <ConfigItem
                    label="Broadcast Port"
                    value={config.cluster.broadcast_port}
                  />
                  <ConfigItem
                    label="API Port"
                    value={config.cluster.api_port}
                  />
                  <ConfigItem
                    label="Discovery Interval"
                    value={`${config.cluster.discovery_interval}s`}
                  />
                  <ConfigItem
                    label="Load Balancing"
                    value={config.cluster.load_balancing ? 'Enabled' : 'Disabled'}
                  />
                </div>
              ) : (
                <p className="text-gh-fg-muted">Cluster not configured</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Raw Configuration View */}
      <Card className="glass">
        <CardHeader>
          <CardTitle>Raw Configuration (JSON)</CardTitle>
          <CardDescription>
            Complete configuration in JSON format
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="bg-gh-canvas-default border border-gh-border-default rounded-lg p-4 overflow-auto max-h-96 text-xs">
            <code className="text-gh-fg-default">
              {JSON.stringify(config, null, 2)}
            </code>
          </pre>
        </CardContent>
      </Card>
    </div>
  );
};

// Helper component for displaying config items
const ConfigItem = ({ label, value }) => (
  <div className="glass rounded-lg p-3">
    <div className="text-xs text-gh-fg-muted mb-1">{label}</div>
    <div className="text-white font-mono text-sm">{value}</div>
  </div>
);

export default ConfigurationPanel;
