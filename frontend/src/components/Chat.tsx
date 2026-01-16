import React, { useState } from 'react';
import { MessageList } from './MessageList';
import { SourcePanel } from './SourcePanel';
import { useWebSocket } from '../hooks/useWebSocket';

export const Chat: React.FC = () => {
  const [input, setInput] = useState('');
  const { messages, sendMessage, isConnected, isStreaming } = useWebSocket('ws://localhost:8000/ws/chat');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isStreaming) {
      sendMessage(input);
      setInput('');
    }
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
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
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
    </div>
  );
};