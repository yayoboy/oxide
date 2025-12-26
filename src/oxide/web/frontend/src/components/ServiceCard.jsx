/**
 * Service Card Component
 * Displays information about an LLM service with glassmorphism UI
 */
import React from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { cn } from '../lib/utils';

const ServiceCard = ({ name, status }) => {
  const { healthy, info } = status || {};
  const isHealthy = healthy === true;

  return (
    <Card variant="interactive" className={cn(!isHealthy && 'opacity-75')}>
      {/* Neon accent line */}
      <div className={cn(
        'absolute top-0 left-0 right-0 h-1 rounded-t-2xl',
        isHealthy ? 'bg-gradient-to-r from-cyan-500 to-blue-500' : 'bg-gradient-to-r from-red-500 to-pink-500'
      )} />

      <div className="mt-2 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-3 h-3 rounded-full',
              isHealthy ? 'bg-cyan-400 pulse-neon' : 'bg-red-400'
            )} />
            <h3 className="text-lg font-bold text-white">{name}</h3>
          </div>
          <Badge variant={isHealthy ? 'success' : 'error'}>
            {isHealthy ? 'Online' : 'Offline'}
          </Badge>
        </div>

        {/* Service Info */}
        {info && (
          <div className="space-y-3">
            <div className="space-y-1">
              <div className="text-xs text-gh-fg-muted uppercase tracking-wide">Type</div>
              <div className="text-sm text-white font-medium">
                {info.type?.value || info.type || 'Unknown'}
              </div>
            </div>

            {info.base_url && (
              <div className="space-y-1">
                <div className="text-xs text-gh-fg-muted uppercase tracking-wide">Endpoint</div>
                <div className="text-xs text-cyan-400 font-mono truncate">
                  {info.base_url}
                </div>
              </div>
            )}

            {info.default_model && (
              <div className="space-y-1">
                <div className="text-xs text-gh-fg-muted uppercase tracking-wide">Default Model</div>
                <div className="text-sm text-white font-medium">
                  {info.default_model}
                </div>
              </div>
            )}

            {info.description && (
              <div className="space-y-1">
                <div className="text-xs text-gh-fg-muted uppercase tracking-wide">Description</div>
                <div className="text-sm text-gh-fg-subtle">
                  {info.description}
                </div>
              </div>
            )}

            {info.optimal_for && info.optimal_for.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs text-gh-fg-muted uppercase tracking-wide">Optimal For</div>
                <div className="flex flex-wrap gap-1.5">
                  {info.optimal_for.slice(0, 3).map((item, idx) => (
                    <Badge key={idx} variant="info" className="text-xs">
                      {item}
                    </Badge>
                  ))}
                  {info.optimal_for.length > 3 && (
                    <Badge variant="default" className="text-xs">
                      +{info.optimal_for.length - 3}
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Offline Warning */}
        {!isHealthy && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-xs text-red-400">
              ⚠️ Service is offline or unreachable
            </p>
            {info?.base_url && (
              <p className="text-xs text-gh-fg-subtle mt-1">
                Check if the service is running at {info.base_url}
              </p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};

export default ServiceCard;
