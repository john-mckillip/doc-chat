import { useState, useRef, useCallback, useEffect } from 'react';

interface IndexProgress {
  phase: string;
  currentFile: string;
  totalChunks: number;
  message: string;
}

interface IndexStats {
  files: number;
  chunks: number;
  new: number;
  modified: number;
  unchanged: number;
  deleted: number;
}

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
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'scan_start':
            setProgress({
              phase: 'scanning',
              currentFile: '',
              totalChunks: 0,
              message: `Scanning directory: ${message.data.directory}`
            });
            break;

          case 'file_processing':
            setProgress(prev => ({
              ...prev,
              phase: 'processing',
              currentFile: message.data.file,
              message: `Processing: ${message.data.file} (${message.data.status})`
            }));
            break;

          case 'file_processed':
            setProgress(prev => ({
              ...prev,
              message: `Processed: ${message.data.file} (${message.data.chunks} chunks)`
            }));
            break;

          case 'file_skipped':
            // Silently track skipped files
            break;

          case 'file_deleted':
            setProgress(prev => ({
              ...prev,
              message: `Removed: ${message.data.file}`
            }));
            break;

          case 'embedding_start':
            setProgress({
              phase: 'embeddings',
              currentFile: '',
              totalChunks: message.data.total_chunks,
              message: `Generating embeddings for ${message.data.total_chunks} chunks...`
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
            setStats(message.data);
            setProgress(prev => ({
              ...prev,
              phase: 'complete',
              message: `Completed: ${message.data.files} files processed`
            }));
            break;

          case 'done':
            setIsIndexing(false);
            ws.close();
            break;

          case 'error':
            console.error('Indexing error:', message.data);
            setProgress(prev => ({
              ...prev,
              message: `Error: ${message.data.message}`
            }));
            break;

          case 'fatal_error':
            setError(message.data.message);
            setIsIndexing(false);
            ws.close();
            break;
        }
      } catch (err) {
        console.error('Failed to parse message:', err);
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
