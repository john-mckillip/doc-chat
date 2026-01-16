import { useState, useEffect } from 'react';
import { Chat } from './components/Chat';
import { IndexStatus } from './components/IndexStatus';

function App() {
  const [isIndexed, setIsIndexed] = useState(false);
  const [stats, setStats] = useState<{ total_chunks: number } | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats');
      const data = await response.json();
      setStats(data);
      setIsIndexed(data.total_chunks > 0);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleIndex = async (directory: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/index', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory })
      });
      
      if (response.ok) {
        await fetchStats();
      }
    } catch (error) {
      console.error('Failed to index:', error);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {!isIndexed ? (
        <IndexStatus onIndex={handleIndex} stats={stats} />
      ) : (
        <Chat />
      )}
    </div>
  );
}

export default App;