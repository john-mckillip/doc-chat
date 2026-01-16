import React from 'react';
import type { Source } from '../types';

interface SourcePanelProps {
  sources: Source[];
}

export const SourcePanel: React.FC<SourcePanelProps> = ({ sources }) => {
    return (
    <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
      <div className="p-4 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Sources</h2>
        <p className="text-sm text-gray-600 mt-1">
          {sources.length} document{sources.length !== 1 ? 's' : ''} referenced
        </p>
      </div>

      <div className="p-4 space-y-3">
        {sources.map((source, index) => (
          <div
            key={index}
            className="p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-start gap-2">
              <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded flex items-center justify-center text-xs font-semibold">
                {index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm text-gray-900 truncate">
                  {source.file}
                </p>
                <p className="text-xs text-gray-500 mt-1 truncate" title={source.path}>
                  {source.path}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Chunk {source.chunk}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};