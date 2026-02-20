import React from 'react';
import type { AppStats, IndexProgress, IndexStats } from '../types';

interface StateBannerProps {
    stats: AppStats | null;
    className?: string;
}

export const IndexStateBanner: React.FC<StateBannerProps> = ({
    stats,
    className = ''
}) => {
    if (stats && stats.total_chunks > 0) {
        return (
            <div className={`bg-green-50 border border-green-200 rounded-lg p-4 ${className}`.trim()}>
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
        );
    }

    return (
        <div className={`bg-blue-50 border border-blue-200 rounded-lg p-4 ${className}`.trim()}>
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
    );
};

interface ProgressFeedbackProps {
    progress: IndexProgress;
    className?: string;
}

export const IndexingProgressFeedback: React.FC<ProgressFeedbackProps> = ({
    progress,
    className = ''
}) => {
    if (!progress.message) {
        return null;
    }

    return (
        <div className={`bg-blue-50 border border-blue-200 rounded-lg p-3 ${className}`.trim()}>
            <div className="flex items-center gap-2 mb-2">
                <svg className="animate-spin h-4 w-4 text-blue-600" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="text-sm font-medium text-blue-800">
                    {progress.phase.charAt(0).toUpperCase() + progress.phase.slice(1)}
                </span>
            </div>
            <p className="text-sm text-blue-700">{progress.message}</p>
            {progress.currentFile && (
                <p className="text-xs text-blue-600 mt-1">📄 {progress.currentFile}</p>
            )}
        </div>
    );
};

interface CompleteFeedbackProps {
    stats: IndexStats;
    title?: string;
    className?: string;
}

export const IndexingCompleteFeedback: React.FC<CompleteFeedbackProps> = ({
    stats,
    title = '✓ Indexing Complete!',
    className = ''
}) => {
    return (
        <div className={`bg-green-50 border border-green-200 rounded-lg p-3 ${className}`.trim()}>
            <p className="text-sm text-green-800 font-medium">{title}</p>
            <p className="text-xs text-green-700 mt-1">
                {stats.files} files • {stats.chunks} chunks
                {stats.new > 0 && ` • ${stats.new} new`}
                {stats.modified > 0 && ` • ${stats.modified} modified`}
            </p>
        </div>
    );
};
