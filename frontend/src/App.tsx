import { useCallback } from 'react';
import { Chat } from './components/Chat';
import { IndexStatus } from './components/IndexStatus';
import { useStats } from './hooks/useStats';

function App() {
  const { stats, isIndexed, refreshStats } = useStats();

  const handleIndexComplete = useCallback(() => {
    refreshStats();
  }, [refreshStats]);

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