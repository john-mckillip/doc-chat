import { useCallback, useEffect, useState } from 'react';
import { fetchIndexStats } from '../utils/api';
import type { AppStats } from '../types';

export const useStats = () => {
    const [stats, setStats] = useState<AppStats | null>(null);
    const [isIndexed, setIsIndexed] = useState(false);

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

    return {
        stats,
        isIndexed,
        refreshStats: loadStats
    };
};
