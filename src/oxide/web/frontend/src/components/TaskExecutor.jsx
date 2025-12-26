/**
 * Task Executor Component
 * Allows users to create and execute tasks with manual service selection
 */
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { tasksAPI } from '../api/client';
import { useServices } from '../hooks/useServices';
import { useWebSocket } from '../hooks/useWebSocket';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { FormField, Select, Textarea } from './ui/Input';

const TaskExecutor = ({ onTaskCompleted }) => {
  const [prompt, setPrompt] = useState('');
  const [selectedService, setSelectedService] = useState('auto');
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [result, setResult] = useState('');
  const [error, setError] = useState(null);

  const { services, loading: servicesLoading } = useServices();
  const { lastMessage } = useWebSocket();

  // Listen for WebSocket updates
  useEffect(() => {
    if (!lastMessage || !currentTaskId) return;

    if (lastMessage.type === 'task_progress' && lastMessage.task_id === currentTaskId) {
      setResult((prev) => prev + lastMessage.chunk);
    } else if (lastMessage.type === 'task_complete' && lastMessage.task_id === currentTaskId) {
      setIsExecuting(false);
      if (lastMessage.success) {
        if (onTaskCompleted) onTaskCompleted();
      } else {
        setError(lastMessage.error || 'Task failed');
      }
    }
  }, [lastMessage, currentTaskId, onTaskCompleted]);

  const handleExecute = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsExecuting(true);
    setResult('');
    setError(null);
    setCurrentTaskId(null);

    try {
      const preferences = {};
      if (selectedService !== 'auto') {
        preferences.preferred_service = selectedService;
      }

      const response = await tasksAPI.execute(prompt, null, preferences);
      setCurrentTaskId(response.data.task_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setIsExecuting(false);
    }
  };

  const handleClear = () => {
    setPrompt('');
    setResult('');
    setError(null);
    setCurrentTaskId(null);
    setIsExecuting(false);
  };

  const healthyServices = services?.services
    ? Object.entries(services.services)
        .filter(([_, service]) => service.healthy)
        .map(([name]) => name)
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="text-2xl">🚀</span>
          Execute Task
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Service Selection */}
        <FormField
          label="LLM Service"
          description={
            selectedService === 'auto'
              ? 'Oxide will automatically select the best service based on your query'
              : `Task will be routed to ${selectedService}`
          }
        >
          <Select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            disabled={isExecuting || servicesLoading}
          >
            <option value="auto">🤖 Auto (Intelligent Routing)</option>
            <optgroup label="Available Services">
              {healthyServices.map((serviceName) => (
                <option key={serviceName} value={serviceName}>
                  {serviceName}
                </option>
              ))}
            </optgroup>
            {healthyServices.length === 0 && (
              <option disabled>No healthy services available</option>
            )}
          </Select>
        </FormField>

        {/* Prompt Input */}
        <FormField label="Prompt" required>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isExecuting}
            placeholder="Enter your query or task description..."
            rows={4}
          />
        </FormField>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button
            onClick={handleExecute}
            disabled={isExecuting || !prompt.trim()}
            variant="primary"
            className="flex-1"
          >
            {isExecuting ? (
              <>
                <span className="animate-spin">⏳</span>
                Executing...
              </>
            ) : (
              <>
                <span>▶️</span>
                Execute Task
              </>
            )}
          </Button>
          <Button
            onClick={handleClear}
            disabled={isExecuting}
            variant="secondary"
          >
            🗑️ Clear
          </Button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-gh-danger/10 border border-gh-danger rounded-md animate-slide-up">
            <div className="flex items-start gap-2">
              <span className="text-gh-danger font-semibold">Error:</span>
              <span className="text-gh-danger text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Result Display */}
        {(result || isExecuting) && (
          <div className="space-y-2 animate-slide-up">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gh-fg-DEFAULT">Result</span>
              {isExecuting && (
                <span className="text-xs text-gh-accent-primary flex items-center gap-1">
                  <span className="w-2 h-2 bg-gh-accent-primary rounded-full animate-pulse" />
                  streaming...
                </span>
              )}
            </div>
            <div className="p-4 bg-gh-canvas border border-gh-border rounded-md max-h-80 overflow-y-auto">
              {result ? (
                <ReactMarkdown
                  className="prose prose-invert max-w-none text-sm"
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-lg my-2"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className="bg-white/10 px-1.5 py-0.5 rounded text-cyan-400 font-mono" {...props}>
                          {children}
                        </code>
                      );
                    },
                    p: ({ children }) => <p className="text-gh-fg-DEFAULT mb-2">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc list-inside text-gh-fg-DEFAULT mb-2">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside text-gh-fg-DEFAULT mb-2">{children}</ol>,
                    h1: ({ children }) => <h1 className="text-xl font-bold text-white mb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-bold text-white mb-2">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-bold text-white mb-2">{children}</h3>,
                    a: ({ children, href }) => <a href={href} className="text-cyan-400 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                  }}
                >
                  {result}
                </ReactMarkdown>
              ) : (
                <div className="text-sm text-gh-fg-muted font-mono">
                  Waiting for response...
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TaskExecutor;
