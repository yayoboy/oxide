/**
 * React hook for WebSocket connection with event subscriptions
 * Integrated with Zustand global state
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import useStore from '../store/useStore';

const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000; // 3 seconds
const PING_INTERVAL = 30000; // 30 seconds

export const useWebSocket = () => {
  const [lastMessage, setLastMessage] = useState(null);

  // Use Zustand store for connection status
  const connected = useStore((state) => state.wsConnected);
  const setWsConnected = useStore((state) => state.setWsConnected);
  const setWsError = useStore((state) => state.setWsError);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const listenersRef = useRef(new Map());
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    try {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        if (mountedRef.current) {
          setWsConnected(true);
          setWsError(null);
        }

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (mountedRef.current) {
            setLastMessage(message);
          }

          // Notify type-specific listeners
          const type = message.type;
          if (listenersRef.current.has(type)) {
            listenersRef.current.get(type).forEach(callback => {
              try {
                callback(message);
              } catch (err) {
                console.error(`[WebSocket] Error in ${type} listener:`, err);
              }
            });
          }

          // Notify all listeners
          if (listenersRef.current.has('*')) {
            listenersRef.current.get('*').forEach(callback => {
              try {
                callback(message);
              } catch (err) {
                console.error('[WebSocket] Error in wildcard listener:', err);
              }
            });
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        if (mountedRef.current) {
          setWsError('WebSocket connection error');
        }
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        if (mountedRef.current) {
          setWsConnected(false);
        }

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt reconnection if still mounted
        if (mountedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[WebSocket] Reconnecting...');
            connect();
          }, RECONNECT_DELAY);
        }
      };

      wsRef.current = ws;

    } catch (err) {
      console.error('[WebSocket] Connection error:', err);
      if (mountedRef.current) {
        setWsError(err.message);
      }
    }
  }, [setWsConnected, setWsError]);

  // Subscribe to specific message types
  const subscribe = useCallback((type, callback) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set());
    }
    listenersRef.current.get(type).add(callback);

    // Return unsubscribe function
    return () => {
      const listeners = listenersRef.current.get(type);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          listenersRef.current.delete(type);
        }
      }
    };
  }, []);

  // Send message
  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      wsRef.current.send(message);
    } else {
      console.warn('[WebSocket] Cannot send message - not connected');
    }
  }, []);

  // Initialize connection
  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const error = useStore((state) => state.wsError);

  return {
    connected,
    lastMessage,
    error,
    subscribe,
    send
  };
};

/**
 * Hook for subscribing to specific WebSocket message types
 *
 * @param {string} messageType - Type of message to listen for (e.g., 'metrics', 'service_status')
 * @param {function} callback - Callback function to handle messages
 * @param {array} deps - Dependency array for callback
 */
export const useWebSocketSubscription = (messageType, callback, deps = []) => {
  const { connected, subscribe } = useWebSocket();

  useEffect(() => {
    if (connected && callback) {
      return subscribe(messageType, callback);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connected, messageType, subscribe, ...deps]);

  return { connected };
};
