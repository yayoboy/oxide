/**
 * Multi-Response Viewer Component
 * Displays responses from multiple LLM services side-by-side for comparison
 */
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Badge } from './ui/Badge';

const ServiceResponsePanel = ({ serviceName, response, isStreaming, error, chunkCount }) => {
  const contentRef = useRef(null);

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (contentRef.current && isStreaming) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [response, isStreaming]);

  const getServiceColor = (name) => {
    const colors = {
      gemini: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
      qwen: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
      openrouter: 'bg-green-500/10 border-green-500/30 text-green-400',
      ollama: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
      default: 'bg-gray-500/10 border-gray-500/30 text-gray-400'
    };

    const key = Object.keys(colors).find(k => name.toLowerCase().includes(k));
    return colors[key] || colors.default;
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <span className={`px-2 py-1 rounded ${getServiceColor(serviceName)}`}>
              {serviceName}
            </span>
          </CardTitle>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <Badge variant="primary" className="text-xs">
                <span className="w-2 h-2 bg-current rounded-full animate-pulse mr-1 inline-block" />
                streaming
              </Badge>
            )}
            {!isStreaming && response && (
              <Badge variant="success" className="text-xs">
                ✓ completed
              </Badge>
            )}
            {error && (
              <Badge variant="danger" className="text-xs">
                ✗ failed
              </Badge>
            )}
          </div>
        </div>
        {chunkCount > 0 && (
          <div className="text-xs text-gh-fg-muted mt-1">
            {chunkCount} chunks received
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden">
        <div
          ref={contentRef}
          className="h-full overflow-y-auto p-4 bg-gh-canvas border border-gh-border rounded-md"
        >
          {error ? (
            <div className="text-sm text-gh-danger">
              <div className="font-semibold mb-1">Error:</div>
              <div className="font-mono text-xs">{error}</div>
            </div>
          ) : response ? (
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
                a: ({ children, href }) => (
                  <a href={href} className="text-cyan-400 hover:underline" target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {response}
            </ReactMarkdown>
          ) : isStreaming ? (
            <div className="text-sm text-gh-fg-muted font-mono animate-pulse">
              Waiting for {serviceName} response...
            </div>
          ) : (
            <div className="text-sm text-gh-fg-muted font-mono">
              No response yet
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const MultiResponseViewer = React.forwardRef(({ taskId, onAllCompleted }, ref) => {
  // State: { [serviceName]: { response: string, isStreaming: boolean, error: string|null, chunkCount: number } }
  const [serviceStates, setServiceStates] = useState({});
  const [completedServices, setCompletedServices] = useState(new Set());
  const [totalServices, setTotalServices] = useState(0);

  const updateServiceState = (serviceName, updates) => {
    setServiceStates((prev) => ({
      ...prev,
      [serviceName]: {
        response: '',
        isStreaming: false,
        error: null,
        chunkCount: 0,
        ...prev[serviceName],
        ...updates,
      },
    }));
  };

  const handleBroadcastChunk = (message) => {
    if (message.task_id !== taskId) return;

    const { service, chunk, done, error, total_chunks } = message;

    if (done) {
      // Service completed
      updateServiceState(service, {
        isStreaming: false,
        error: error || null,
        chunkCount: total_chunks || serviceStates[service]?.chunkCount || 0,
      });

      setCompletedServices((prev) => {
        const newSet = new Set(prev);
        newSet.add(service);
        return newSet;
      });
    } else {
      // Streaming chunk
      updateServiceState(service, {
        response: (serviceStates[service]?.response || '') + chunk,
        isStreaming: true,
        chunkCount: (serviceStates[service]?.chunkCount || 0) + 1,
      });

      // Track total services
      setTotalServices((prev) => {
        const current = Object.keys(serviceStates).length;
        return Math.max(prev, current + 1);
      });
    }
  };

  // Expose handleBroadcastChunk to parent via ref
  React.useImperativeHandle(ref, () => ({
    handleBroadcastChunk,
  }));

  // Check if all services completed
  useEffect(() => {
    if (totalServices > 0 && completedServices.size === totalServices) {
      if (onAllCompleted) {
        onAllCompleted();
      }
    }
  }, [completedServices, totalServices, onAllCompleted]);

  // Reset when taskId changes
  useEffect(() => {
    setServiceStates({});
    setCompletedServices(new Set());
    setTotalServices(0);
  }, [taskId]);

  const services = Object.keys(serviceStates).sort();
  const gridCols = services.length === 2 ? 'grid-cols-2' : services.length === 3 ? 'grid-cols-3' : 'grid-cols-2 lg:grid-cols-4';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-gh-fg-DEFAULT">
            🎯 Multi-LLM Broadcast Comparison
          </span>
          <Badge variant="info" className="text-xs">
            {completedServices.size}/{totalServices || '?'} completed
          </Badge>
        </div>
        {totalServices > 0 && completedServices.size < totalServices && (
          <div className="text-xs text-gh-fg-muted flex items-center gap-2">
            <span className="w-2 h-2 bg-gh-accent-primary rounded-full animate-pulse" />
            Broadcasting to {totalServices} services...
          </div>
        )}
      </div>

      {/* Grid of Service Panels */}
      {services.length > 0 ? (
        <div className={`grid ${gridCols} gap-4 min-h-[400px] max-h-[600px]`}>
          {services.map((serviceName) => (
            <ServiceResponsePanel
              key={serviceName}
              serviceName={serviceName}
              response={serviceStates[serviceName].response}
              isStreaming={serviceStates[serviceName].isStreaming}
              error={serviceStates[serviceName].error}
              chunkCount={serviceStates[serviceName].chunkCount}
            />
          ))}
        </div>
      ) : (
        <Card className="min-h-[400px] flex items-center justify-center">
          <div className="text-center space-y-2">
            <div className="text-6xl mb-4">📡</div>
            <div className="text-gh-fg-DEFAULT font-medium">
              Waiting for broadcast to start...
            </div>
            <div className="text-sm text-gh-fg-muted">
              Responses from all LLM services will appear here
            </div>
          </div>
        </Card>
      )}
    </div>
  );
});

MultiResponseViewer.displayName = 'MultiResponseViewer';

export default MultiResponseViewer;
