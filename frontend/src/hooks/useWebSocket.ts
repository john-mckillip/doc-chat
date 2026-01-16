import { useEffect, useRef, useState, useCallback } from 'react';
import type { Message, Source, WebSocketMessage, UseWebSocketReturn } from '../types';

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const currentMessageRef = useRef<Message | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'sources':
          currentMessageRef.current = {
            role: 'assistant',
            content: '',
            sources: data.data as Source[]
          };
          setIsStreaming(true);
          break;

        case 'content':
          if (currentMessageRef.current) {
            currentMessageRef.current.content += data.data;
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              
              if (lastMessage?.role === 'assistant' && currentMessageRef.current) {
                newMessages[newMessages.length - 1] = { ...currentMessageRef.current };
              } else if (currentMessageRef.current) {
                newMessages.push({ ...currentMessageRef.current });
              }
              
              return newMessages;
            });
          }
          break;

        case 'done':
          setIsStreaming(false);
          currentMessageRef.current = null;
          break;
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = useCallback((query: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && !isStreaming) {
      const userMessage: Message = { role: 'user', content: query };
      setMessages(prev => [...prev, userMessage]);

      wsRef.current.send(JSON.stringify({ query }));
    }
  }, [isStreaming]);

  return { messages, sendMessage, isConnected, isStreaming };
};