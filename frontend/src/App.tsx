import { useState, useEffect, useCallback } from 'react';
import { Chat } from './components/Chat';
import { IndexStatus } from './components/IndexStatus';

function App() {
  const [isIndexed, setIsIndexed] = useState(false);
  const [stats, setStats] = useState<{ total_chunks: number } | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats');
      const data = await response.json();
      setStats(data);
      setIsIndexed(data.total_chunks > 0);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadStats = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/stats');
        const data = await response.json();
        if (mounted) {
          setStats(data);
          setIsIndexed(data.total_chunks > 0);
        }
      } catch (error) {
        if (mounted) {
          console.error('Failed to fetch stats:', error);
        }
      }
    };

    loadStats();

    return () => {
      mounted = false;
    };
  }, []);

  const handleIndexComplete = useCallback(() => {
    fetchStats();
  }, [fetchStats]);

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