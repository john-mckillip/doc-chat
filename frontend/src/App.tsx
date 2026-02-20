import { useState, useEffect, useCallback } from 'react';
import { Chat } from './components/Chat';
import { IndexStatus } from './components/IndexStatus';
import { fetchIndexStats } from './utils/api';

function App() {
  const [isIndexed, setIsIndexed] = useState(false);
  const [stats, setStats] = useState<{ total_chunks: number } | null>(null);

  const loadStats = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await fetchIndexStats(signal);
      setStats(data);
      setIsIndexed(data.total_chunks > 0);
    } catch (error) {
      if (signal?.aborted) {
        return;
      }
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  useEffect(() => {
    const abortController = new AbortController();
    loadStats(abortController.signal);

    return () => {
      abortController.abort();
    };
  }, [loadStats]);

  const handleIndexComplete = useCallback(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="h-screen flex flex-col">
      {!isIndexed ? (
        <IndexStatus stats={stats} onIndexComplete={handleIndexComplete} />
      ) : (
        <Chat />
      )}
    </div>
  );
}

export default App;