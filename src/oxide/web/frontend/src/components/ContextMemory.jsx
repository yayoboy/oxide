/**
 * Context Memory Component
 * Displays conversation history and context memory statistics
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { formatTimestamp, formatDuration } from '../lib/utils';

const API_BASE = 'http://localhost:8000/api';

const ContextMemory = () => {
  const [stats, setStats] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedConv, setExpandedConv] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/memory/stats`);
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch memory stats:', err);
    }
  }, []);

  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/memory/conversations?limit=50`);
      const data = await response.json();
      setConversations(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchConversationDetails = useCallback(async (conversationId) => {
    try {
      const response = await fetch(`${API_BASE}/memory/conversations/${conversationId}`);
      const data = await response.json();
      setSelectedConversation(data);
      setExpandedConv(conversationId);
    } catch (err) {
      console.error('Failed to fetch conversation:', err);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchStats();
    fetchConversations();
  }, [fetchStats, fetchConversations]);

  const toggleConversation = (conversationId) => {
    if (expandedConv === conversationId) {
      setExpandedConv(null);
      setSelectedConversation(null);
    } else {
      fetchConversationDetails(conversationId);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="text-2xl">🧠</span>
              Context Memory
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center py-12">
              <div className="text-gh-fg-muted animate-pulse">Loading memory...</div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="text-2xl">🧠</span>
              Context Memory
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="p-4 bg-gh-danger/10 border border-gh-danger rounded-md text-gh-danger">
              Error loading memory: {error}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Memory Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card variant="interactive">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gh-accent-primary mb-1">
                {stats?.total_conversations || 0}
              </div>
              <div className="text-sm text-gh-fg-muted">Conversations</div>
            </div>
          </CardContent>
        </Card>

        <Card variant="interactive">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gh-success mb-1">
                {stats?.total_messages || 0}
              </div>
              <div className="text-sm text-gh-fg-muted">Total Messages</div>
            </div>
          </CardContent>
        </Card>

        <Card variant="interactive">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gh-attention mb-1">
                {stats?.average_messages_per_conversation?.toFixed(1) || 0}
              </div>
              <div className="text-sm text-gh-fg-muted">Avg Messages/Conv</div>
            </div>
          </CardContent>
        </Card>

        <Card variant="interactive">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-sm font-mono text-gh-fg-subtle mb-1">
                {stats?.storage_path?.split('/').pop() || 'memory.json'}
              </div>
              <div className="text-xs text-gh-fg-muted">Storage File</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Conversations List */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="text-2xl">💬</span>
            Recent Conversations
          </CardTitle>
          <Button variant="secondary" size="sm" onClick={fetchConversations}>
            🔄 Refresh
          </Button>
        </CardHeader>

        <CardContent>
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-6xl mb-4 opacity-20">💭</div>
              <div className="text-gh-fg-muted">No conversations yet</div>
              <div className="text-sm text-gh-fg-subtle mt-2">
                Conversations will appear here as they are created
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className="p-4 bg-gh-canvas rounded-lg border border-gh-border hover:border-gh-accent-primary/50 transition-all duration-200"
                >
                  {/* Conversation Header */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3 flex-wrap">
                      <Badge variant="default">
                        💬 {conv.message_count} messages
                      </Badge>
                      <span className="text-xs text-gh-fg-muted">
                        Created: {formatTimestamp(conv.created_at)}
                      </span>
                      <span className="text-xs text-gh-fg-subtle">
                        Updated: {formatTimestamp(conv.updated_at)}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleConversation(conv.id)}
                    >
                      {expandedConv === conv.id ? '▼ Hide' : '▶ Show'}
                    </Button>
                  </div>

                  {/* Conversation ID */}
                  <div className="text-xs font-mono text-gh-fg-subtle mb-3">
                    ID: {conv.id}
                  </div>

                  {/* Expanded Messages */}
                  {expandedConv === conv.id && selectedConversation && (
                    <div className="mt-4 space-y-2 border-t border-gh-border pt-4">
                      <div className="text-sm font-medium text-gh-fg-muted mb-3">
                        Messages:
                      </div>
                      {selectedConversation.messages.map((msg, idx) => (
                        <div
                          key={msg.id || idx}
                          className={`p-3 rounded-md border ${
                            msg.role === 'user'
                              ? 'bg-gh-accent-emphasis/5 border-gh-accent-primary/20'
                              : 'bg-gh-canvas-subtle border-gh-border'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Badge
                              variant={msg.role === 'user' ? 'default' : 'outline'}
                            >
                              {msg.role === 'user' ? '👤' : '🤖'} {msg.role}
                            </Badge>
                            <span className="text-xs text-gh-fg-subtle">
                              {formatTimestamp(msg.timestamp)}
                            </span>
                          </div>
                          <div className="text-sm text-gh-fg whitespace-pre-wrap">
                            {msg.content.substring(0, 300)}
                            {msg.content.length > 300 && (
                              <span className="text-gh-fg-subtle">...</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ContextMemory;
