import { useState, useRef, useCallback, useEffect } from 'react';
import type { IndexProgress, IndexStats } from '../types';

const isIndexStats = (value: unknown): value is IndexStats => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const stats = value as Record<string, unknown>;

  return (
    typeof stats.files === 'number' &&
    typeof stats.chunks === 'number' &&
    typeof stats.new === 'number' &&
    typeof stats.modified === 'number' &&
    typeof stats.unchanged === 'number' &&
    typeof stats.deleted === 'number'
  );
};

export const useIndexWebSocket = (url: string) => {
  const [isIndexing, setIsIndexing] = useState(false);
  const [progress, setProgress] = useState<IndexProgress>({
    phase: '',
    currentFile: '',
    totalChunks: 0,
    message: ''
  });
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const startIndexing = useCallback((directory: string) => {
    if (isIndexing) return;

    setIsIndexing(true);
    setError(null);
    setProgress({ phase: 'connecting', currentFile: '', totalChunks: 0, message: 'Connecting...' });
    setStats(null);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send directory to index
      ws.send(JSON.stringify({ directory }));
      setProgress({ phase: 'starting', currentFile: '', totalChunks: 0, message: 'Starting indexing...' });
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { type?: unknown; data?: unknown };

        if (!message || typeof message !== 'object' || typeof message.type !== 'string') {
          setError('Invalid message format from indexing service');
          setIsIndexing(false);
          ws.close();
          return;
        }

        const messageData =
          message.data && typeof message.data === 'object' ? message.data as Record<string, unknown> : {};

        const dataMessage = typeof messageData.message === 'string' ? messageData.message : 'Unknown error';
        const dataFile = typeof messageData.file === 'string' ? messageData.file : 'unknown';
        const dataStatus = typeof messageData.status === 'string' ? messageData.status : 'unknown';
        const dataDirectory = typeof messageData.directory === 'string' ? messageData.directory : 'unknown';
        const dataChunks = typeof messageData.chunks === 'number' ? messageData.chunks : 0;
        const dataTotalChunks = typeof messageData.total_chunks === 'number' ? messageData.total_chunks : 0;

        switch (message.type) {
          case 'scan_start':
            setProgress({
              phase: 'scanning',
              currentFile: '',
              totalChunks: 0,
              message: `Scanning directory: ${dataDirectory}`
            });
            break;

          case 'file_processing':
            setProgress(prev => ({
              ...prev,
              phase: 'processing',
              currentFile: dataFile,
              message: `Processing: ${dataFile} (${dataStatus})`
            }));
            break;

          case 'file_processed':
            setProgress(prev => ({
              ...prev,
              message: `Processed: ${dataFile} (${dataChunks} chunks)`
            }));
            break;

          case 'file_skipped':
            // Silently track skipped files
            break;

          case 'file_deleted':
            setProgress(prev => ({
              ...prev,
              message: `Removed: ${dataFile}`
            }));
            break;

          case 'embedding_start':
            setProgress({
              phase: 'embeddings',
              currentFile: '',
              totalChunks: dataTotalChunks,
              message: `Generating embeddings for ${dataTotalChunks} chunks...`
            });
            break;

          case 'embedding_complete':
            setProgress(prev => ({
              ...prev,
              message: 'Embeddings generated'
            }));
            break;

          case 'saving':
            setProgress({
              phase: 'saving',
              currentFile: '',
              totalChunks: 0,
              message: 'Saving index...'
            });
            break;

          case 'save_complete':
            setProgress(prev => ({
              ...prev,
              message: 'Index saved'
            }));
            break;

          case 'stats':
            setStats(isIndexStats(messageData) ? messageData : null);
            setProgress(prev => ({
              ...prev,
              phase: 'complete',
              message: `Completed: ${typeof messageData.files === 'number' ? messageData.files : 0} files processed`
            }));
            break;

          case 'done':
            setIsIndexing(false);
            ws.close();
            break;

          case 'error':
            setError(dataMessage);
            setProgress(prev => ({
              ...prev,
              message: `Error: ${dataMessage}`
            }));
            break;

          case 'fatal_error':
            setError(dataMessage);
            setIsIndexing(false);
            ws.close();
            break;

          default:
            setProgress(prev => ({
              ...prev,
              message: `Unknown message type: ${message.type}`
            }));
            break;
        }
      } catch (err) {
        console.error('Failed to parse message:', err);
        setError('Received malformed indexing message');
        setIsIndexing(false);
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error');
      setIsIndexing(false);
    };

    ws.onclose = () => {
      setIsIndexing(false);
      wsRef.current = null;
    };
  }, [url, isIndexing]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isIndexing,
    progress,
    stats,
    error,
    startIndexing
  };
};
