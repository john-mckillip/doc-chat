import React, { useState}  from 'react';

interface IndexStatusProps {
    onIndex: (directory: string) => Promise<void>;
    stats: { total_chunks: number } | null;
}

export const IndexStatus: React.FC<IndexStatusProps> = ({ onIndex, stats }) => {
  const [directory, setDirectory] = useState('');
  const [isIndexing, setIsIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!directory.trim()) {
      setError('Please enter a directory path');
      return;
    }

    setIsIndexing(true);
    setError(null);

    try {
      await onIndex(directory);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to index directory');
    } finally {
      setIsIndexing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">DocChat</h1>
          <p className="text-gray-600">AI-powered documentation assistant</p>
        </div>

        {stats && stats.total_chunks > 0 ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-green-800 mb-1">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold">Index Ready</span>
            </div>
            <p className="text-sm text-green-700">
              {stats.total_chunks} document chunks indexed
            </p>
          </div>
        ) : (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-blue-800 mb-1">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold">No Index Found</span>
            </div>
            <p className="text-sm text-blue-700">
              Please index your documentation to get started
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="directory" className="block text-sm font-medium text-gray-700 mb-2">
              Documentation Directory
            </label>
            <input
              id="directory"
              type="text"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="/path/to/your/docs"
              disabled={isIndexing}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <p className="mt-2 text-xs text-gray-500">
              Examples: <code className="bg-gray-100 px-1 py-0.5 rounded">./docs</code>,{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded">../my-project</code>,{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded">/home/user/project/docs</code>
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isIndexing}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isIndexing ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Indexing...
              </span>
            ) : (
              'Index Documentation'
            )}
          </button>
        </form>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Supported File Types</h3>
          <div className="flex flex-wrap gap-2">
            {['.md', '.txt', '.py', '.js', '.ts', '.tsx', '.cs', '.json'].map((ext) => (
              <span key={ext} className="text-xs bg-white px-2 py-1 rounded border border-gray-200">
                {ext}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};