/**
 * React hook for WebSocket connection
 */
import { useState, useEffect, useRef } from 'react';
import { createWebSocket } from '../api/client';

export const useWebSocket = () => {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = createWebSocket(
      (message) => {
        setMessages((prev) => [...prev, message]);

        // Update connection status
        if (message.type === 'connected') {
          setConnected(true);
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      }
    );

    wsRef.current = ws;

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const send = (data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { messages, connected, send };
};
