import React, { useState, useEffect } from 'react';
import {
  IndexStateBanner,
  IndexingCompleteFeedback,
  IndexingProgressFeedback
} from './IndexingFeedback';
import { SupportedFileTypes } from './SupportedFileTypes';
import { useIndexWebSocket } from '../hooks/useIndexWebSocket';
import { WS_ENDPOINTS } from '../utils/api';
import type { AppStats } from '../types';

interface IndexStatusProps {
  stats: AppStats | null;
  onIndexComplete: () => void;
}

export const IndexStatus: React.FC<IndexStatusProps> = ({ stats, onIndexComplete }) => {
  const [directory, setDirectory] = useState('');
  const { isIndexing, progress, stats: indexStats, error: wsError, startIndexing } = useIndexWebSocket(WS_ENDPOINTS.index);
  const [error, setError] = useState<string | null>(null);

  // Update error from WebSocket
  const displayError = wsError || error;

  // Notify parent when indexing completes
  useEffect(() => {
    if (indexStats && !isIndexing) {
      onIndexComplete();
    }
  }, [indexStats, isIndexing, onIndexComplete]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!directory.trim()) {
      setError('Please enter a directory path');
      return;
    }

    setError(null);
    startIndexing(directory);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">DocChat</h1>
          <p className="text-gray-600">AI-powered documentation assistant</p>
        </div>

        <IndexStateBanner stats={stats} className="mb-6" />

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

          {displayError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{displayError}</p>
            </div>
          )}

          {isIndexing && progress.message && (
            <IndexingProgressFeedback progress={progress} />
          )}

          {indexStats && !isIndexing && (
            <IndexingCompleteFeedback stats={indexStats} />
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

        <SupportedFileTypes />
      </div>
    </div>
  );
};