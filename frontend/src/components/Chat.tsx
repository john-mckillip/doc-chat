import React, { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { SourcePanel } from './SourcePanel';
import { useWebSocket } from '../hooks/useWebSocket';
import { useIndexWebSocket } from '../hooks/useIndexWebSocket';

export const Chat: React.FC = () => {
  const [input, setInput] = useState('');
  const [showReindexModal, setShowReindexModal] = useState(false);
  const [reindexPath, setReindexPath] = useState('');
  const { messages, sendMessage, isConnected, isStreaming } = useWebSocket('ws://localhost:8000/ws/chat');
  const { isIndexing, progress, stats: indexStats, startIndexing } = useIndexWebSocket('ws://localhost:8000/ws/index');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isStreaming) {
      sendMessage(input);
      setInput('');
    }
  };

  // Close modal when indexing completes
  useEffect(() => {
    if (indexStats && !isIndexing && showReindexModal) {
      setTimeout(() => {
        setShowReindexModal(false);
        setReindexPath('');
      }, 2000); // Show success for 2 seconds before closing
    }
  }, [indexStats, isIndexing, showReindexModal]);

  const handleReindex = () => {
    if (!reindexPath.trim()) return;
    startIndexing(reindexPath);
  };

  const lastAssistantMessage = messages
    .filter(m => m.role === 'assistant')
    .pop();

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Documentation Chat</h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowReindexModal(true)}
              className="px-4 py-2 text-sm bg-gray-100 text-white rounded-lg hover:bg-gray-200 transition-colors"
            >
              Re-index
            </button>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-600">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <MessageList messages={messages} isStreaming={isStreaming} />
        </div>

        {/* Input */}
        <div className="bg-white border-t px-6 py-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your documentation..."
              disabled={!isConnected || isStreaming}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={!isConnected || isStreaming || !input.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isStreaming ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>

      {/* Source panel */}
      {lastAssistantMessage?.sources && (
        <SourcePanel sources={lastAssistantMessage.sources} />
      )}

      {/* Re-index Modal */}
      {showReindexModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-semibold mb-4">Re-index Documentation</h2>
            <p className="text-sm text-gray-600 mb-4">
              Enter the path to your documentation directory. Only new and modified files will be re-indexed.
            </p>
            <input
              type="text"
              value={reindexPath}
              onChange={(e) => setReindexPath(e.target.value)}
              placeholder="/path/to/your/docs"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              disabled={isIndexing}
            />

            {isIndexing && progress.message && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">{progress.message}</p>
                {progress.currentFile && (
                  <p className="text-xs text-blue-600 mt-1">📄 {progress.currentFile}</p>
                )}
              </div>
            )}

            {indexStats && !isIndexing && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800 font-medium">✓ Re-indexing Complete!</p>
                <p className="text-xs text-green-700 mt-1">
                  {indexStats.files} files • {indexStats.chunks} chunks
                  {indexStats.new > 0 && ` • ${indexStats.new} new`}
                  {indexStats.modified > 0 && ` • ${indexStats.modified} modified`}
                </p>
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowReindexModal(false);
                  setReindexPath('');
                }}
                disabled={isIndexing}
                className="px-4 py-2 text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReindex}
                disabled={isIndexing || !reindexPath.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isIndexing ? 'Indexing...' : 'Re-index'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};